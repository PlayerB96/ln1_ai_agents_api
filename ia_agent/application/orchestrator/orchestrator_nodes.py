"""
Nodos del grafo de orquestación usando LangGraph.
Define el estado y las funciones de cada nodo del flujo.
"""
from typing import TypedDict, Dict, Any
from sistemas.application.jira_service import JiraService
from ia_agent.application.orchestrator.redis_action_store import RedisActionStore
from ia_agent.application.orchestrator.intent_engine import IntentEngine
from ia_agent.application.orchestrator.action_loader import ActionFactory


class OrchestratorState(TypedDict):
    """Estado compartido entre nodos del grafo"""
    user_message: str
    area: str
    username: str
    actions: Dict[str, Any]
    interpretation: Dict[str, Any]
    result: Dict[str, Any]


def get_actions(state: OrchestratorState) -> OrchestratorState:
    """
    Obtiene las acciones disponibles desde Redis.
    
    Args:
        state: Estado actual del orquestador
        
    Returns:
        Estado actualizado con las acciones
    """
    state["actions"] = RedisActionStore.get_all()
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
    error_msg = interpretation.get("_error")
    
    # Manejo explícito de acción 'none' o errores de interpretación
    if action_name == "none":
        msg = "No se pudo determinar una acción clara."
        if error_msg:
            msg = f"No se pudo generar la respuesta: {error_msg}"
            
        state["result"] = {
            "status": False, # Indica que no se ejecutó acción exitosa
            "msg": msg,
            "data": {
                "opciones": list(state["actions"].keys())
            }
        }
        return state
    
    # Obtener configuración de la acción desde Redis
    action_config = RedisActionStore.get_action(action_name)
    
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
    handler_name = action_config.get("handler")
    
    if not handler_name:
        # Fallback: usar action_name directamente (funciona con estructura actual)
        handler_name = action_name
    
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
