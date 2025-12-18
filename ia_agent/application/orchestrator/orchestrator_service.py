from langgraph.graph import StateGraph, END

from ia_agent.application.orchestrator.orchestrator_nodes import (
    OrchestratorState,
    get_actions,
    interpret_intent,
    execute_action,
    should_execute_action,
    should_interpret_intent,
    preselect_intent,
    should_proceed_after_preselect
)


class OrchestratorGraphService:
    """
    Orchestrator usando LangGraph (StateGraph)
    """

    def __init__(self):
        self.graph = StateGraph(OrchestratorState)

        # Registrar nodos
        self.graph.add_node("get_actions", get_actions)
        self.graph.add_node("preselect_intent", preselect_intent)
        self.graph.add_node("interpret_intent", interpret_intent)
        self.graph.add_node("execute_action", execute_action)

        # Flujo del grafo con routing condicional
        self.graph.set_entry_point("get_actions")
        
        # Edge condicional: después de obtener acciones, decidir si ir a preselección o terminar
        self.graph.add_conditional_edges(
            "get_actions",
            should_interpret_intent,
            {
                "interpret": "preselect_intent",  # Si hay acciones, primero intentar match sin LLM
                "end": END
            }
        )
        
        # Edge condicional: resultado de preselección
        self.graph.add_conditional_edges(
            "preselect_intent",
            should_proceed_after_preselect,
            {
                "execute": "execute_action",    # Match fuerte → ejecutar directo
                "interpret": "interpret_intent", # Ambiguo → consultar LLM
                "end": END                      # Nada parecido → terminar
            }
        )

        # Edge condicional: solo ejecuta acción si la interpretación (LLM) fue exitosa
        self.graph.add_conditional_edges(
            "interpret_intent",
            should_execute_action,
            {
                "execute": "execute_action",  # Si interpretación OK → ejecutar
                "end": END  # Si interpretación falló → terminar directamente
            }
        )
        
        self.graph.add_edge("execute_action", END)

        # # Flujo del grafo
        # self.graph.set_entry_point("get_actions")
        # self.graph.add_edge("get_actions", END)  # 🔴 TESTING: Detiene después de get_actions
        # self.graph.add_edge("get_actions", "interpret_intent")
        # self.graph.add_edge("interpret_intent", "execute_action")
        # self.graph.add_edge("execute_action", END)

        # Compilar grafo
        self.app = self.graph.compile()

    def process(self, **kwargs):
        """Procesa una solicitud con parámetros dinámicos"""
        initial_state: OrchestratorState = {
            "user_message": kwargs.get("message", ""),
            "area": kwargs.get("area", ""),
            "username": kwargs.get("username", ""),
            "company": kwargs.get("company", "default"),
            "tags": kwargs.get("tags", []) or [],
            "actions": {},
            "interpretation": {},
            "preselect": {},
            "result": {}
        }

        final_state = self.app.invoke(initial_state)
        return final_state["result"]
