"""
Nodos del grafo de orquestación usando LangGraph.
Define el estado (State) y las funciones de cada nodo del flujo.

Estructura:
1. Definición de Tipos (State)
2. Constantes y Configuración
3. Funciones Auxiliares (Privadas)
4. Lógica de Routing
5. Nodos del Grafo (Funciones Core)
"""

import re
import json
from typing import TypedDict, Dict, Any, List, Set, Tuple

# Dependencias internas
from sistemas.application.jira_service import JiraService
from ia_agent.application.orchestrator.redis_action_store import RedisActionStore
from ia_agent.application.orchestrator.intent_engine import IntentEngine
from ia_agent.application.orchestrator.action_loader import ActionFactory


# =============================================================================
# 1. DEFINICIÓN DE TIPOS (STATE)
# =============================================================================

class OrchestratorState(TypedDict):
    """
    Estado compartido entre los nodos del grafo de orquestación.
    
    Attributes:
        user_message: Mensaje original del usuario.
        area: Área de negocio del usuario (e.g., 'sistemas').
        username: Nombre del usuario.
        company: Identificador de la compañía/tenant (default: 'default').
        tags: Lista de tags del request para contexto adicional.
        actions: Diccionario de acciones disponibles y filtradas.
        interpretation: Resultado de la interpretación (Intención/LLM).
        preselect: Metadatos de la fase de preselección (scores, candidatos).
        result: Resultado final de la ejecución para devolver al cliente.
    """
    user_message: str
    area: str
    username: str
    company: str
    tags: List[str]
    actions: Dict[str, Any]
    interpretation: Dict[str, Any]
    preselect: Dict[str, Any]
    result: Dict[str, Any]


# =============================================================================
# 2. CONSTANTES Y CONFIGURACIÓN
# =============================================================================

# Umbrales para la lógica de preselección (Keyword matching)
MIN_LLM_TRIGGER = 0.30  # Score mínimo para considerar llamar al LLM si no es match perfecto
MIN_LLM_MARGIN = 0.05   # Margen mínimo para considerar una opción "segura" sin LLM (DEPRECATED en uso estricto, pero útil como referencia)
STRONG_MATCH_THRESHOLD = 0.55 # Score mínimo para considerar un match como "fuerte" y ejecutar directo
STRONG_MATCH_MARGIN = 0.20    # Diferencia requerida con el segundo lugar para ejecutar directo


# =============================================================================
# 3. FUNCIONES AUXILIARES (PRIVADAS)
# =============================================================================

def _normalize_text(text: str) -> str:
    """Normaliza texto: minúsculas y solo caracteres alfanuméricos simples."""
    text = (text or "").lower()
    return re.sub(r"[^a-z0-9áéíóúñü\s]", " ", text)


def _tokenize(text: str) -> Set[str]:
    """Convierte texto en un conjunto de tokens únicos normalizados."""
    return {t for t in _normalize_text(text).split() if t}


def _missing_required_for(action_name: str, params: Dict[str, Any], state: OrchestratorState) -> List[str]:
    """Identifica parámetros obligatorios faltantes para una acción."""
    cfg = state["actions"].get(action_name) or {}
    schema = cfg.get("parameters", {}) or {}
    required = schema.get("required", []) or []
    return [k for k in required if not params.get(k)]


def _score_against_action(name: str, cfg: Dict[str, Any], query_tokens: Set[str]) -> float:
    """
    Calcula un score de similitud entre los tokens del query y una acción.
    Basado en coincidencia de palabras clave, nombre y descripción.
    """
    # Construir corpus de texto de la acción
    parts = [name, cfg.get("description", "")]
    tags = cfg.get("tags", []) or cfg.get("keywords", []) or []
    
    if isinstance(tags, list):
        parts.extend(tags)
    elif isinstance(tags, str):
        parts.append(tags)
        
    text = " ".join(map(str, parts))
    action_tokens = _tokenize(text)
    
    if not action_tokens or not query_tokens:
        return 0.0

    # Calcular overlap (Jaccard-ish)
    overlap = len(action_tokens & query_tokens)
    score = overlap / (len(query_tokens) or 1) # Penaliza queries largos con poco match
    
    # Bonificaciones heurísticas
    if name in _tokenize(" ".join(query_tokens)): # Si el nombre exacto está en el query
        score += 0.2
    if cfg.get("type") == "composite": # Preferencia ligera por flujos compuestos
        score += 0.1
        
    return score


# =============================================================================
# 4. LÓGICA DE ROUTING (EDGES CONDICIONALES)
# =============================================================================

def should_interpret_intent(state: OrchestratorState) -> str:
    """
    Decide si proceder a la fase de interpretación/preselección o terminar.
    Se ejecuta después de 'get_actions'.
    
    Returns:
        'interpret': Si hay acciones disponibles.
        'end': Si no hay acciones (ahorro de tokens).
    """
    actions = state.get("actions", {})
    
    if not actions:
        state["result"] = {
            "status": False,
            "msg": "No se encontrado una accion concreta para tu consulta, puedes replantearla por favor.",
            "data": {
                "area": state.get("area"),
                "company": state.get("company"),
                "sugerencia": "Verifica que el área sea correcta o que haya acciones configuradas."
            }
        }
        print(f"🚫 Sin acciones disponibles → Saltando LLM")
        return "end"
    
    print(f"✅ {len(actions)} acciones candidatas disponibles")
    return "interpret"


def should_proceed_after_preselect(state: OrchestratorState) -> str:
    """
    Decide el siguiente paso basado en el resultado de la preselección.
    
    Returns:
        'execute': Si hubo un match fuerte y claro (Fast Track).
        'interpret': Si hay ambigüedad o match parcial aceptable (LLM).
        'end': Si no hay coincidencias relevantes.
    """
    # 1. Si preselect ya determinó una acción (Fast Track)
    action_name = (state.get("interpretation") or {}).get("action")
    if action_name and action_name != "none":
        print(f"🚀 Fast Track: Ejecutando '{action_name}' por preselección exitosa")
        return "execute"

    # 2. Analizar scores para decidir si llamar al LLM
    ps = state.get("preselect", {}) or {}
    top = float(ps.get("top_score", 0.0))
    second = float(ps.get("second_score", 0.0))
    margin = top - second
    
    print(f"🧮 Routing Gate: top={top:.2f}, margin={margin:.2f} (trigger={MIN_LLM_TRIGGER})")

    # Si el mejor score es muy bajo, no vale la pena molestar al LLM
    if top < MIN_LLM_TRIGGER:
        print("🛑 Routing Gate: Saltando LLM por baja confianza")
        return "failure"

    # Si pasamos el filtro mínimo, vamos al LLM (incluso si hay ambigüedad/empate)
    return "interpret"


def should_execute_action(state: OrchestratorState) -> str:
    """
    Decide si ejecutar una acción después de la interpretación del LLM.
    
    Returns:
        'execute': Si el LLM identificó una acción válida.
        'end': Si el LLM retornó 'none' o falló.
    """
    interpretation = state.get("interpretation", {})
    action_name = interpretation.get("action")
    
    print(f"🔀 Execution Gate: action='{action_name}'")
    
    if not action_name or action_name == "none":
        error_msg = interpretation.get("_error")
        msg = "No se pudo determinar una acción clara."
        if error_msg:
            msg = f"Error en interpretación: {error_msg}"
        
        state["result"] = {
            "status": False,
            "msg": msg,
            "data": {"opciones": list(state["actions"].keys())}
        }
        print(f"❌ Execution Gate → END (Sin acción válida)")
        return "end"
    
    print(f"✅ Execution Gate → EXECUTE")
    return "execute"


# =============================================================================
# 5. NODOS DEL GRAFO (FUNCIONES CORE)
# =============================================================================

def get_actions(state: OrchestratorState) -> OrchestratorState:
    """
    Nodo: Recupera y filtra las acciones disponibles desde Redis.
    Aplica filtros por: Compañía, Área, y Tags/Keywords.
    """
    company = state.get("company", "default")
    area = state.get("area", "")
    
    # 1. Cargar acciones base y específicas de la compañía
    default_actions = RedisActionStore.get_all(key="actions:default")
    if company != "default":
        company_actions = RedisActionStore.get_all(key=f"actions:{company}")
        all_actions = {**default_actions, **company_actions}
    else:
        all_actions = default_actions

    # 2. Definir filtros locales
    def _area_matches(cfg: Dict[str, Any]) -> bool:
        action_area = cfg.get("area")
        # Match si no tiene área, es global, o coincide con el área del usuario
        return (not action_area) or (action_area == "global") or (str(action_area).lower() == str(area).lower())
    
    def _has_relevant_tags(cfg: Dict[str, Any]) -> bool:
        # Filtro relajado: si la acción no tiene tags, pasa.
        # Si tiene tags, debe coincidir alguno con el mensaje o los tags del usuario.
        action_tags = cfg.get("tags", []) or cfg.get("keywords", []) or []
        if not action_tags:
            return True
        
        user_tags = [t.lower() for t in (state.get("tags") or [])]
        msg_lower = state.get("user_message", "").lower()
        
        # Normalizar a lista de strings lower
        if isinstance(action_tags, str):
            action_tags = [action_tags]
        action_tags_lower = [str(t).lower() for t in action_tags]
        
        # Check de coincidencia
        for tag in action_tags_lower:
            if tag in msg_lower or tag in user_tags:
                return True
        return False
    
    # 3. Aplicar filtrado
    filtered_actions = {
        k: v for k, v in all_actions.items() 
        if _area_matches(v) and _has_relevant_tags(v)
    }
    
    state["actions"] = filtered_actions
    
    print(f"\n🏢 Contexto: {company} | 📍 Área: {area}")
    print(f"📂 Acciones cargadas: {list(state['actions'].keys())}\n")
        
    return state


def preselect_intent(state: OrchestratorState) -> OrchestratorState:
    """
    Nodo: Preselección heurística basada en keyword matching.
    Intenta "adivinar" la acción sin usar LLM para optimizar costos y latencia.
    """
    message = state.get("user_message", "")
    actions = state.get("actions", {})
    
    # Preparar tokens del usuario + tags contextules
    user_tokens = _tokenize(message)
    user_tokens |= {str(t).lower() for t in (state.get("tags") or [])}

    # Calcular scores para todas las acciones
    scored: List[Tuple[float, str]] = []
    for name, cfg in actions.items():
        score = _score_against_action(name, cfg, user_tokens)
        scored.append((score, name))

    if not scored:
        state["interpretation"] = {"action": "none"}
        state["preselect"] = {"top_score": 0.0}
        print("🤷‍♂️ Preselect: Sin candidatos")
        return state

    # Ordenar candidatos
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score, top_name = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    print(f"🔎 Preselect Scores: {top_name}={top_score:.2f}, 2nd={second_score:.2f}")

    # Decisión: Fast Track (Match fuerte y único)
    if top_score >= STRONG_MATCH_THRESHOLD and (top_score - second_score) >= STRONG_MATCH_MARGIN:
        state["interpretation"] = {"action": top_name, "params": {}}
        print(f"✅ Preselect HIT: '{top_name}' (Fast Track)")
    else:
        # No hay decisión definitiva aquí, se delega al routing (que decidirá si llamar al LLM)
        state["interpretation"] = {"action": "none"}
        print("🤔 Preselect: Ambiguo o bajo score → Delegando")

    # Guardar metadatos para el Router
    state["preselect"] = {
        "top_action": top_name,
        "top_score": top_score,
        "second_score": second_score
    }

    return state


def interpret_intent(state: OrchestratorState) -> OrchestratorState:
    """
    Nodo: Interpretación profunda usando LLM (Gemini).
    Se usa cuando la preselección no fue concluyente.
    """
    try:
        print("🧠 Invocando Motor de Intenciones (LLM)...")
        state["interpretation"] = IntentEngine.interpret(
            state["user_message"],
            state["area"],
            state["actions"]
        )
    except Exception as e:
        print(f"❌ Error crítico en interpret_intent: {e}")
        state["interpretation"] = {
            "action": "none", 
            "params": {},
            "_error": str(e)
        }
        
    return state


def execute_action(state: OrchestratorState) -> OrchestratorState:
    """
    Nodo: Ejecución de la acción seleccionada.
    Instancia el handler correspondiente y ejecuta la lógica de negocio.
    Soporta acciones simples y compuestas (multi-step).
    """
    interpretation = state["interpretation"]
    action_name = interpretation.get("action")
    params = interpretation.get("params", {})
    
    # Recuperar config
    action_config = state["actions"].get(action_name)
    if not action_config:
        state["result"] = {
            "status": False,
            "msg": f"Acción '{action_name}' no encontrada en configuración."
        }
        return state

    print(f"⚙️ Iniciando ejecución: {action_name}")

    # -------------------------------------------------------------------------
    # CASO A: Acción Compuesta (Composite)
    # -------------------------------------------------------------------------
    if action_config.get("type") == "composite":
        steps = action_config.get("steps", []) or []
        results: Dict[str, Any] = {}
        
        for idx, step in enumerate(steps):
            step_id = step.get("id") or f"step_{idx+1}"
            step_action = step.get("action")
            
            # Parametrización en cascada: (Step Default < User Input < Parent Params)
            step_defaults = step.get("params", {}) or {}
            user_step_params = (state.get("interpretation", {}).get("params", {}).get(step_id, {}))
            merged_params = {**step_defaults, **user_step_params, **params}
            merged_params["_action"] = step_action # Contexto para el handler

            # Validación de parámetros
            missing = _missing_required_for(step_action, merged_params, state)
            if missing:
                state["result"] = {
                    "status": False,
                    "msg": f"Faltan parámetros en subtarea '{step_id}'",
                    "data": {"missing": missing, "step": step_id}
                }
                return state

            # Instanciación y Ejecución
            step_cfg = state["actions"].get(step_action) or {}
            handler_name = step_cfg.get("handler") or step_cfg.get("class") or step_action
            
            # Dependencias
            deps = {"actions": state["actions"], "username": state["username"]}
            if handler_name == "jira" or step_action in ["epicas", "sprints"]:
                deps["jira_service"] = JiraService(None)
                if "jira_method" in step_cfg:
                    merged_params["_jira_method"] = step_cfg["jira_method"]

            handler = ActionFactory.create(handler_name, **deps)
            if not handler:
                state["result"] = {
                    "status": False, 
                    "msg": f"Handler no encontrado: {handler_name}"
                }
                return state

            step_result = handler.execute(merged_params)
            results[step_id] = step_result

            # Fail-fast: Si un paso falla, se aborta todo
            if not step_result.get("status", True):
                state["result"] = {
                    "status": False,
                    "msg": f"Error en paso '{step_id}': {step_result.get('msg')}",
                    "data": {"steps": results}
                }
                return state

        # Éxito total composite
        state["result"] = {
            "status": True,
            "msg": f"Acción compuesta '{action_name}' completada.",
            "data": {"steps": results}
        }
        return state

    # -------------------------------------------------------------------------
    # CASO B: Acción Simple
    # -------------------------------------------------------------------------
    handler_name = action_config.get("handler") or action_config.get("class") or action_name
    
    # Dependencias
    deps = {"actions": state["actions"], "username": state["username"]}
    if handler_name == "jira" or action_name in ["epicas", "sprints"]:
        deps["jira_service"] = JiraService(None)
        if "jira_method" in action_config:
            params["_jira_method"] = action_config["jira_method"]
    
    handler = ActionFactory.create(handler_name, **deps)
    if not handler:
        state["result"] = {
            "status": False,
            "msg": f"Handler no configurado para: {handler_name}"
        }
        return state
    
    params["_action"] = action_name
    state["result"] = handler.execute(params)
    
    return state


def handle_preselect_failure(state: OrchestratorState) -> OrchestratorState:
    """
    Nodo: Maneja el caso de fallo en preselección (baja confianza).
    Establece el mensaje de error explícito solicitado.
    """
    ps = state.get("preselect", {})
    username = state.get("username", "Usuario")
    state["result"] = {
        "status": False,
        "msg": f"👋 Hola {username}, no logré entender muy bien tu consulta 🤔. ¿Podrías darme un poco más de contexto? 🙏",
        "data": {
            "opciones": list(state.get("actions", {}).keys()),
            "sugerencia": "Intenta mencionar explícitamente una de las acciones disponibles.",
            "top_sugerido": ps.get("top_action")
        }
    }
    print("🛑 Preselect Failure Node: Estableciendo resultado de error.")
    return state
