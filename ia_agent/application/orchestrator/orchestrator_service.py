from langgraph.graph import StateGraph, END

from ia_agent.application.orchestrator.orchestrator_nodes import (
    OrchestratorState,
    get_actions,
    interpret_intent,
    execute_action,
    should_execute_action,
    should_interpret_intent,
    preselect_intent,
    should_proceed_after_preselect,
    handle_preselect_failure
)


class OrchestratorGraphService:
    """
    Servicio de orquestación principal basado en LangGraph.
    Define y ejecuta el flujo de trabajo del agente inteligente.
    
    Flujo:
    1. get_actions (Recuperar acciones contexto)
    2. should_interpret_intent (¿Hay acciones?)
    3. preselect_intent (¿Hay match obvio?)
    4. should_proceed_after_preselect (FastTrack vs LLM vs Failure)
    5. handle_preselect_failure (Si falla preselección/confianza)
    6. interpret_intent (LLM)
    7. should_execute_action (¿Interpretación válida?)
    8. execute_action (Ejecución lógica de negocio)
    """

    def __init__(self):
        self.graph = StateGraph(OrchestratorState)

        # ---------------------------------------------------------------------
        # 1. Definición de Nodos
        # ---------------------------------------------------------------------
        self.graph.add_node("get_actions", get_actions)
        self.graph.add_node("preselect_intent", preselect_intent)
        self.graph.add_node("handle_preselect_failure", handle_preselect_failure)
        self.graph.add_node("interpret_intent", interpret_intent)
        self.graph.add_node("execute_action", execute_action)

        # ---------------------------------------------------------------------
        # 2. Definición de Edges (Flujo)
        # ---------------------------------------------------------------------
        self.graph.set_entry_point("get_actions")
        
        # A. Decisión post-recuperación: ¿Hay acciones disponibles?
        self.graph.add_conditional_edges(
            "get_actions",
            should_interpret_intent,
            {
                "interpret": "preselect_intent",  # Sí: Intentar match por palabras clave
                "end": END                        # No: Terminar flujo (ahorro tokens)
            }
        )
        
        # B. Decisión post-preselección: ¿Match claro o ambigüedad?
        self.graph.add_conditional_edges(
            "preselect_intent",
            should_proceed_after_preselect,
            {
                "execute": "execute_action",    # Match Fuerte: Ejecutar directo (Fast Track)
                "interpret": "interpret_intent", # Ambiguo: Consultar al LLM
                "failure": "handle_preselect_failure" # Baja confianza: Error
            }
        )
        
        self.graph.add_edge("handle_preselect_failure", END)

        # C. Decisión post-interpretación: ¿Entendió el LLM?
        self.graph.add_conditional_edges(
            "interpret_intent",
            should_execute_action,
            {
                "execute": "execute_action",    # Sí: Ejecutar acción
                "end": END                      # No: Terminar (o acción 'none')
            }
        )
        
        # D. Finalización
        self.graph.add_edge("execute_action", END)

        # ---------------------------------------------------------------------
        # 3. Compilación
        # ---------------------------------------------------------------------
        self.app = self.graph.compile()

    def process(self, **kwargs):
        """
        Procesa una solicitud de usuario a través del grafo de orquestación.
        
        Args:
            **kwargs: Parámetros del contexto (message, area, username, company, tags).
            
        Returns:
            Dict: Resultado final de la ejecución.
        """
        initial_state: OrchestratorState = {
            "user_message": kwargs.get("message", ""),
            "area": kwargs.get("area", ""),
            "username": kwargs.get("username", ""),
            "company": kwargs.get("company", "default"),
            "tags": kwargs.get("tags", []) or [],
            "actions": {},
            "interpretation": {},
            "preselect": {},  # Inicialización requerida para evitar KeyError
            "result": {}
        }

        final_state = self.app.invoke(initial_state)
        return final_state["result"]
