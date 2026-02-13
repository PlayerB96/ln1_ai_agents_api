from langgraph.domain.states import ConversationState
from langgraph.infrastructure.llm_adapter import GeminiLLMAdapter
from langgraph.infrastructure.tools import LangGraphTools
from infrastructure.config.redis_config import RedisConfig
from langgraph.application.lang_response import LangGraphResponse
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
    Nodo que busca y filtra acciones en Redis según la intención clasificada.
    Lee agente:actions:* y filtra por tags que coincidan con state.intent.
    Retorna acciones ordenadas por prioridad.
    """
    intent = state.intent
    
    if not intent:
        print("❌ No hay intención disponible")
        state.metadata["matched_actions"] = []
        state.metadata["matched_count"] = 0
        state.step = "actions_retriever_error"
        return state
    
    try:
        redis_client = RedisConfig.get_client()
        matched_actions = LangGraphResponse.fetch_and_filter_actions(redis_client, intent)
        
        # Guardar acciones coincidentes en el estado
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


