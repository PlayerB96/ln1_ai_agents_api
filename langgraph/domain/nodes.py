from langgraph.domain.states import ConversationState
from langgraph.infrastructure.llm_adapter import GeminiLLMAdapter
from langgraph.infrastructure.tools import LangGraphTools
from infrastructure.config.redis_config import RedisConfig
import json


def build_prompt_classifier_node(state: ConversationState) -> ConversationState:
    """
    Nodo clasificador que lee el prompt de reglas desde Redis y lo enriquece con el mensaje del usuario.
    Lee la regla: agente:rule:intent:classifier
    """
    redis_client = RedisConfig.get_client()
    
    try:
        # Leer el prompt de clasificación desde Redis
        rule_key = "agente:rule:intent:classifier"
        rule_type = redis_client.type(rule_key)
        
        classifier_prompt = None
        
        if rule_type == "ReJSON-RL":
            rule_json = redis_client.execute_command('JSON.GET', rule_key)
            if rule_json:
                rule_data = json.loads(rule_json) if isinstance(rule_json, str) else rule_json
                classifier_prompt = rule_data.get("prompt") if isinstance(rule_data, dict) else str(rule_data)
        elif rule_type == "string":
            classifier_prompt = redis_client.get(rule_key)
        elif rule_type == "none":
            print(f"⚠️ Key '{rule_key}' no existe en Redis")
            classifier_prompt = None
        
        if classifier_prompt:
            # Reemplazar {user_message} con el mensaje real del usuario
            enriched_prompt = classifier_prompt.replace("{user_message}", state.user_message)
                        
            # Guardar el prompt enriquecido en el estado para uso posterior
            state.metadata["classifier_prompt"] = enriched_prompt
            state.metadata["classifier_template"] = classifier_prompt
        else:
            print("⚠️ No se encontró prompt de clasificación en Redis")
            state.metadata["classifier_prompt"] = None
        
        state.step = "rule_classified"
        # Nota: state.intent aún es None, se asignará en el siguiente nodo (llm_classifier_node)
        return state
        
    except Exception as e:
        print(f"❌ Error en clasificación: {e}")
        state.metadata["classifier_prompt"] = None
        state.step = "rule_classified_error"
        return state


def llm_classifier_node(state: ConversationState) -> ConversationState:
    """
    Nodo que envía el prompt enriquecido a Gemini para clasificar la intención.
    Usa el prompt guardado en state.metadata["classifier_prompt"]
    Imprime confianza y tokens utilizados.
    """
    try:
        classifier_prompt = state.metadata.get("classifier_prompt")
        
        if not classifier_prompt:
            print("❌ No hay prompt de clasificación disponible")
            state.llm_response = "desconocida"
            state.step = "llm_classifier_done_error"
            return state
        
        # Enviar a Gemini
        llm = GeminiLLMAdapter()
        response_data = llm.generate_text(classifier_prompt)
        
        # Extraer datos
        response_text = response_data.get("text", "")
        tokens_info = response_data.get("tokens", {})
        finish_reason = response_data.get("finish_reason", "UNKNOWN")
        
        
        # Limpieza: extraer solo la palabra clave (primera línea, sin espacios)
        classified_intent = response_text.strip().split('\n')[0].strip().lower()
        
        print(f"🤖 Respuesta del LLM (raw): {response_text}")
        print(f"✅ Intención clasificada: {classified_intent}")
        print(f"📊 Tokens utilizados: {json.dumps(tokens_info, indent=2)}")
        
        # Guardar la clasificación
        state.llm_response = classified_intent
        state.intent = classified_intent
        state.metadata["classified_intent"] = classified_intent
        state.metadata["tokens_used"] = tokens_info
        state.metadata["finish_reason"] = str(finish_reason)
        state.step = "llm_classifier_done"
        
        return state
        
    except Exception as e:
        print(f"❌ Error en clasificación del LLM: {e}")
        state.llm_response = "desconocida"
        state.step = "llm_classifier_done_error"
        return state


def actions_retriever_node(state: ConversationState) -> ConversationState:
    """
    Nodo optimizado que busca y filtra acciones en Redis según la intención clasificada.
    Lee agente:actions:* y filtra por tags que coincidan con state.intent.
    Retorna acciones ordenadas por prioridad.
    """
    redis_client = RedisConfig.get_client()
    intent = state.intent  # Viene del nodo anterior
    
    if not intent:
        print("❌ No hay intención disponible")
        state.metadata["matched_actions"] = []
        state.metadata["matched_count"] = 0
        state.step = "actions_retriever_error"
        return state
    
    try:
        # Buscar todas las keys de acciones
        action_keys = redis_client.keys("agente:actions:*")
        matched_actions = []
        intent_lower = intent.lower()
        # print(action_keys)
        print(f"\n🔍 Buscando acciones para intención: '{intent}'")
        
        for key in action_keys:
            try:
                key_type = redis_client.type(key)
                actions_data = None
                
                # Leer según el tipo de dato
                if key_type == "ReJSON-RL":
                    json_data = redis_client.execute_command('JSON.GET', key)
                    actions_data = json.loads(json_data) if isinstance(json_data, str) else json_data
                    print(actions_data)
                elif key_type == "string":
                    json_str = redis_client.get(key)
                    actions_data = json.loads(json_str) if json_str else None
                
                if not actions_data:
                    continue
                
                # Detectar si es acción individual o estructura múltiple
                actions_list = []
                if isinstance(actions_data, list):
                    actions_list = actions_data
                elif isinstance(actions_data, dict) and "id" in actions_data and "tags" in actions_data:
                    # Es una acción individual con estructura: {"id": ..., "tags": ...}
                    actions_list = [actions_data]
                elif isinstance(actions_data, dict):
                    # Es un diccionario con múltiples acciones como valores
                    actions_list = list(actions_data.values())
                else:
                    continue
                
                print(f"  📖 {key} contiene {len(actions_list)} acciones")
                
                # Iterar sobre cada acción
                for action_detail in actions_list:
                    if not isinstance(action_detail, dict):
                        continue
                    
                    action_id = action_detail.get("id", "unknown")
                    tags = action_detail.get("tags", [])
                    if not isinstance(tags, list):
                        tags = [tags]
                    tags_lower = [tag.lower() for tag in tags]
                    
                    print(f"    - {action_id}: tags={tags_lower}")
                    
                    # Si hay coincidencia
                    if intent_lower in tags_lower:
                        matched_actions.append({
                            "id": action_detail.get("id", action_id),
                            "description": action_detail.get("description", ""),
                            "tags": tags,
                            "priority": action_detail.get("priority", 0),
                            "params": action_detail.get("params", {}),
                            "required": action_detail.get("required", []),
                            "examples": action_detail.get("examples", []),
                            "source_key": key
                        })
                        print(f"  ✅ {action_detail.get('id', action_id)} | Priority: {action_detail.get('priority', 0)} | Tags: {tags}")
            
            except Exception as e:
                print(f"  ⚠️ Error procesando {key}: {e}")
                continue
        
        # Ordenar por prioridad (descendente)
        matched_actions.sort(key=lambda x: x["priority"], reverse=True)
        
        # Guardar acciones coincidentes
        state.metadata["matched_actions"] = matched_actions
        state.metadata["matched_count"] = len(matched_actions)
        state.step = "actions_retrieved"
        
        if matched_actions:
            print(f"\n✅ {len(matched_actions)} acciones encontradas (ordenadas por prioridad):")
            for i, action in enumerate(matched_actions, 1):
                print(f"   {i}. {action['id']} (prioridad: {action['priority']})")
        else:
            print(f"\n⚠️ No se encontraron acciones para la intención '{intent}'")
        
        return state
        
    except Exception as e:
        print(f"❌ Error en actions_retriever: {e}")
        state.metadata["matched_actions"] = []
        state.metadata["matched_count"] = 0
        state.step = "actions_retriever_error"
        return state


