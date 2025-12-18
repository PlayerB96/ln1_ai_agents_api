"""
Nodos del grafo de orquestación usando LangGraph.
Define el estado y las funciones de cada nodo del flujo.
"""
import json
from typing import TypedDict, Dict, Any
from sistemas.application.jira_service import JiraService
from ia_agent.application.orchestrator.redis_action_store import RedisActionStore
from ia_agent.application.orchestrator.intent_engine import IntentEngine
from ia_agent.application.orchestrator.action_loader import ActionFactory
import re


class OrchestratorState(TypedDict):
    """Estado compartido entre nodos del grafo"""
    user_message: str
    area: str
    username: str
    company: str  # Identificador de la compañía/tenant
    tags: list  # Tags opcionales para filtrado adicional
    actions: Dict[str, Any]
    interpretation: Dict[str, Any]
    result: Dict[str, Any]
    preselect: Dict[str, Any]  # Metadatos de preselección para routing

def _missing_required_for(action_name: str, params: Dict[str, Any], state: OrchestratorState) -> list:
    """Devuelve la lista de parámetros requeridos que faltan para una acción."""
    cfg = state["actions"].get(action_name) or {}
    schema = cfg.get("parameters", {}) or {}
    required = schema.get("required", []) or []
    missing = [k for k in required if not params.get(k)]
    return missing


def should_execute_action(state: OrchestratorState) -> str:
    """
    Función de routing condicional.
    Decide si ejecutar la acción o terminar el flujo basado en la interpretación.
    
    Returns:
        'execute' si hay una acción válida para ejecutar
        'end' si la interpretación falló o no pudo determinar acción
    """
    interpretation = state.get("interpretation", {})
    action_name = interpretation.get("action")
    
    print(f"🔀 Routing: action='{action_name}'")
    
    # Si no hay acción o es 'none', terminar directamente
    if not action_name or action_name == "none":
        # Preparar resultado de error antes de terminar
        error_msg = interpretation.get("_error")
        msg = "No se pudo determinar una acción clara."
        if error_msg:
            msg = f"No se pudo generar la respuesta: {error_msg}"
        
        state["result"] = {
            "status": False,
            "msg": msg,
            "data": {
                "opciones": list(state["actions"].keys())
            }
        }
        print(f"❌ Routing → END (sin acción válida)")
        return "end"
    
    # Si hay acción, continuar a ejecución
    print(f"✅ Routing → EXECUTE (acción: {action_name})")
    return "execute"


def should_interpret_intent(state: OrchestratorState) -> str:
    """
    Función de routing condicional después de get_actions.
    Decide si vale la pena llamar al LLM o terminar directamente.
    
    Returns:
        'interpret' si hay acciones disponibles para interpretar
        'end' si no hay acciones disponibles (ahorra tokens)
    """
    actions = state.get("actions", {})
    
    # Si no hay acciones disponibles, no tiene sentido usar el LLM
    if not actions or len(actions) == 0:
        state["result"] = {
            "status": False,
            "msg": "No se encontrado una accion concreta para tu consulta, puedes replantearla por favor.",
            "data": {
                "area": state.get("area"),
                "company": state.get("company"),
                "sugerencia": "Verifica que el área sea correcta o que haya acciones configuradas."
            }
        }
        print(f"🚫 Sin acciones disponibles → Saltando LLM (ahorro de tokens)")
        return "end"
    
    # Si hay acciones, continuar con interpretación
    print(f"✅ {len(actions)} acciones disponibles → Llamando al LLM")
    return "interpret"


# ------------------------------------------------------------
# Preselección ligera sin LLM (ahorro de tokens)
# ------------------------------------------------------------
# Umbrales de decisión para preselección y uso de LLM
MIN_LLM_TRIGGER = 0.30  # si el mejor score es menor, no vale la pena llamar al LLM
MIN_LLM_MARGIN = 0.05   # si la diferencia entre top y segundo es menor, es ambiguo


def _normalize_text(text: str) -> str:
    text = (text or "").lower()
    return re.sub(r"[^a-z0-9áéíóúñü\s]", " ", text)


def _tokenize(text: str) -> set:
    return {t for t in _normalize_text(text).split() if t}


def _score_against_action(name: str, cfg: Dict[str, Any], query_tokens: set) -> float:
    parts = [name, cfg.get("description", "")]
    tags = cfg.get("tags", []) or cfg.get("keywords", []) or []
    if isinstance(tags, list):
        parts.extend(tags)
    elif isinstance(tags, str):
        parts.append(tags)
    text = " ".join(map(str, parts))
    tokens = _tokenize(text)
    if not tokens or not query_tokens:
        return 0.0
    overlap = len(tokens & query_tokens)
    score = overlap / (len(query_tokens) or 1)
    if name in tokens:
        score += 0.2
    if cfg.get("type") == "composite":
        score += 0.1
    return score


def preselect_intent(state: OrchestratorState) -> OrchestratorState:
    """
    Intent matching ligero y determinístico sin LLM.
    Si existe un match fuerte y claro, fija la acción en el estado
    para evitar llamar al LLM.
    """
    message = state.get("user_message", "")
    actions = state.get("actions", {})
    user_tokens = _tokenize(message)
    # Incluir tags del request como señales adicionales
    user_tokens |= {str(t).lower() for t in (state.get("tags") or [])}

    scored = []
    for name, cfg in actions.items():
        score = _score_against_action(name, cfg, user_tokens)
        scored.append((score, name))

    if not scored:
        state["interpretation"] = {"action": "none", "params": {}}
        print("🤷‍♂️ Preselect: sin acciones para evaluar")
        return state

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[0]
    second = scored[1] if len(scored) > 1 else (0.0, None)

    top_score, top_name = top
    second_score, _ = second

    print(f"🔎 Preselect scores → top: {top_name}={top_score:.2f}, second={second_score:.2f}")

    # Umbrales: requerimos confianza mínima y separación suficiente
    STRONG_MATCH = 0.55
    MARGIN = 0.20
    if top_score >= STRONG_MATCH and (top_score - second_score) >= MARGIN:
        state["interpretation"] = {"action": top_name, "params": {}}
        print(f"✅ Preselect hit → acción: {top_name}")
    else:
        state["interpretation"] = {"action": "none", "params": {}}
        print("🤔 Preselect inconcluso → requerirá LLM")

    # Guardar metadatos de preselect para routing posterior
    state["preselect"] = {
        "top_action": top_name,
        "top_score": top_score,
        "second_score": second_score
    }

    return state


def should_proceed_after_preselect(state: OrchestratorState) -> str:
    """
    Si la preselección determinó una acción válida, ejecutar directo.
    De lo contrario, proceder a LLM para interpretación.
    """
    action_name = (state.get("interpretation") or {}).get("action")
    if action_name and action_name != "none":
        print(f"🚀 Saltando LLM: Ejecutando '{action_name}' por preselect")
        return "execute"

    # Si no hubo acción por preselect, decidir si vale la pena llamar al LLM
    ps = state.get("preselect", {}) or {}
    top = float(ps.get("top_score", 0.0))
    second = float(ps.get("second_score", 0.0))
    margin = top - second
    print(f"🧮 Gate LLM: top={top:.2f}, margin={margin:.2f} (min_top={MIN_LLM_TRIGGER}, min_margin={MIN_LLM_MARGIN})")

    # Solo saltar el LLM si la confianza del mejor candidato es muy baja.
    # Si hay buenos candidatos pero están empatados (ambigüedad), DEBEMOS llamar al LLM.
    if top < MIN_LLM_TRIGGER:
        state["result"] = {
            "status": False,
            "msg": "No se encontrado una accion concreta para tu consulta, puedes replantearla por favor.",
            "data": {
                "opciones": list(state.get("actions", {}).keys()),
                "sugerencia": "Intenta mencionar explícitamente una de las acciones disponibles.",
                "top_sugerido": ps.get("top_action")
            }
        }
        print("🛑 Gate LLM: saltando interpretación por baja confianza/ambigüedad")
        return "end"

    # En caso contrario, vale la pena intentar con LLM
    return "interpret"



def get_actions(state: OrchestratorState) -> OrchestratorState:
    """
    Obtiene las acciones disponibles desde Redis.
    Filtra por compañía y área para soporte multi-tenant.
    
    Args:
        state: Estado actual del orquestador
        
    Returns:
        Estado actualizado con las acciones
    """
    company = state.get("company", "default")
    area = state.get("area", "")
    
    # Siempre cargar acciones default (base para todos)
    default_actions = RedisActionStore.get_all(key="actions:default")
    
    # Si la empresa es diferente de default, cargar sus acciones específicas
    if company != "default":
        company_actions = RedisActionStore.get_all(key=f"actions:{company}")
        all_actions = {**default_actions, **company_actions}
    else:
        all_actions = default_actions

    # Filtrar por área: mantener acciones sin área definida (globales) y las del área específica
    def area_matches(cfg: Dict[str, Any]) -> bool:
        action_area = cfg.get("area")
        return (action_area is None) or (action_area == "global") or (str(action_area).lower() == str(area).lower())
    
    # Filtrar por tags: si el mensaje o los tags del request contienen keywords de los tags de la acción
    def has_relevant_tags(cfg: Dict[str, Any]) -> bool:
        action_tags = cfg.get("tags", []) or cfg.get("keywords", []) or []
        if not action_tags:
            return True  # Sin tags = pasa el filtro (neutro)
        
        # Obtener tags del usuario (si los envió) y mensaje
        user_tags = [t.lower() for t in (state.get("tags") or [])]
        msg_lower = state.get("user_message", "").lower()
        
        # Normalizar action_tags a lista
        if isinstance(action_tags, str):
            action_tags = [action_tags]
        
        action_tags_lower = [str(t).lower() for t in action_tags]
        
        # Coincide si algún tag de la acción aparece en el mensaje o en los tags del usuario
        for tag in action_tags_lower:
            if tag in msg_lower or tag in user_tags:
                return True
        
        return False
    
    # Aplicar ambos filtros
    state["actions"] = {
        k: v for k, v in all_actions.items() 
        if area_matches(v) and has_relevant_tags(v)
    }
    
    print(f"\n🏢 Compañía: {company}")
    print(f"📍 Área: {area}")
    print(f"✅ Acciones disponibles (filtradas por área y tags): {list(state['actions'].keys())}\n")
        
    return state



def interpret_intent(state: OrchestratorState) -> OrchestratorState:
    """
    Interpreta la intención del usuario usando Gemini.
    
    Args:
        state: Estado actual del orquestador
        
    Returns:
        Estado actualizado con la interpretación
    """
    try:
        # Intentar interpretar la intención
        state["interpretation"] = IntentEngine.interpret(
            state["user_message"],
            state["area"],
            state["actions"]
        )

    except Exception as e:
        # En caso de error (e.g. Gemini 503, 429), retornar acción 'none' 
        # pero guardando el error para debugging si es necesario
        print(f"❌ Error en interpret_intent: {e}")
        state["interpretation"] = {
            "action": "none", 
            "params": {},
            "_error": str(e)  # Guardar error para posible uso
        }
        
        # Opcional: Si queremos fallar fallar rápido y devolver error al usuario
        # descomentar lo siguiente:
        # state["result"] = {
        #     "status": False,
        #     "msg": f"No se pudo interpretar la intención: {str(e)}",
        #     "data": {"opciones": list(state["actions"].keys())}
        # }
        # Esto requeriría cambiar el flujo del grafo para ir directo a END
        
    return state


def execute_action(state: OrchestratorState) -> OrchestratorState:
    """
    Ejecuta la acción interpretada.
    
    Args:
        state: Estado actual del orquestador
        
    Returns:
        Estado actualizado con el resultado
    """
    interpretation = state["interpretation"]
    action_name = interpretation.get("action")
    params = interpretation.get("params", {})
    
    print(f"⚙️ Ejecutando acción: {action_name} con params: {params}")
    
    # Obtener configuración de la acción desde el estado combinado (default + company)
    action_config = state["actions"].get(action_name)

    # Soporte para tareas compuestas (tarea padre con subtareas/steps)
    if action_config and action_config.get("type") == "composite":
        steps = action_config.get("steps", []) or []
        results: Dict[str, Any] = {}
        
        for idx, step in enumerate(steps):
            step_id = step.get("id") or f"step_{idx+1}"
            step_action = step.get("action")
            if not step_action:
                state["result"] = {
                    "status": False,
                    "msg": f"El step '{step_id}' no define 'action'"
                }
                return state

            # Construir parámetros del step: defaults del step, luego params específicos del step,
            # y por último los params del parent (permitiendo override por el usuario)
            step_defaults = step.get("params", {}) or {}
            user_step_params = (state.get("interpretation", {}).get("params", {}).get(step_id, {})) if state.get("interpretation") else {}
            merged_params = {**step_defaults, **user_step_params, **params}

            # Validar requeridos contra el esquema del step_action
            missing = _missing_required_for(step_action, merged_params, state)
            if missing:
                state["result"] = {
                    "status": False,
                    "msg": f"Faltan parámetros para la subtarea '{step_id}' ({step_action})",
                    "data": {
                        "step": step_id,
                        "action": step_action,
                        "missing": missing,
                        "required": state["actions"].get(step_action, {}).get("parameters", {}).get("required", [])
                    },
                    "followups": [
                        {
                            "question": f"¿Puedes proporcionar {', '.join(missing)} para '{step_id}'?",
                            "step": step_id,
                            "action": step_action
                        }
                    ]
                }
                return state

            # Determinar handler del step
            step_config = state["actions"].get(step_action) or {}
            step_handler_name = step_config.get("handler") or step_config.get("class") or step_action

            # Preparar dependencias (reutilizamos la misma lógica)
            dependencies = {
                "actions": state["actions"],
                "username": state["username"]
            }
            if step_handler_name == "jira" or step_action in ["epicas", "sprints"]:
                dependencies["jira_service"] = JiraService(None)
                if "jira_method" in step_config:
                    merged_params["_jira_method"] = step_config["jira_method"]

            handler = ActionFactory.create(step_handler_name, **dependencies)
            if not handler:
                state["result"] = {
                    "status": False,
                    "msg": f"Handler no encontrado para subtarea: {step_handler_name}"
                }
                return state

            # Identificar acción del step y ejecutar
            merged_params["_action"] = step_action
            step_result = handler.execute(merged_params)
            results[step_id] = step_result

            # Si un step falla, detener el flujo compuesto
            if not step_result.get("status", True):
                state["result"] = {
                    "status": False,
                    "msg": f"Falló la subtarea '{step_id}': {step_result.get('msg', 'Error en ejecución')}",
                    "data": {"steps": results}
                }
                return state

        # Todas las subtareas OK
        state["result"] = {
            "status": True,
            "msg": f"Flujo compuesto '{action_name}' ejecutado correctamente",
            "data": {"steps": results}
        }
        return state
    
    if not action_config:
        state["result"] = {
            "status": False,
            "msg": f"Acción no reconocida en el sistema: {action_name}",
            "data": {
                "opciones": list(state["actions"].keys())
            }
        }
        return state
    
    # Determinar el handler a usar
    # Soporta tanto "handler" (estructura optimizada) como "class" (estructura actual)
    # Soportar tanto "handler" (preferido) como "class" (compatibilidad)
    handler_name = action_config.get("handler") or action_config.get("class") or action_name
    
    # Preparar dependencias según el handler
    dependencies = {
        "actions": state["actions"],
        "username": state["username"]
    }
    
    # Si es una acción de Jira (por handler o por action_name)
    if handler_name == "jira" or action_name in ["epicas", "sprints"]:
        dependencies["jira_service"] = JiraService(None)
        
        # Agregar método de Jira si está especificado en Redis
        if "jira_method" in action_config:
            params["_jira_method"] = action_config["jira_method"]
    
    # Crear instancia del handler usando el factory
    handler = ActionFactory.create(handler_name, **dependencies)
    
    if not handler:
        state["result"] = {
            "status": False,
            "msg": f"Handler no encontrado para: {handler_name}"
        }
        return state
    
    # Agregar nombre de acción a los parámetros
    params["_action"] = action_name
    
    # Ejecutar acción
    state["result"] = handler.execute(params)
    return state
