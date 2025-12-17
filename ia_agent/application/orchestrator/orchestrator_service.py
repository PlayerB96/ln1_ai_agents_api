from langgraph.graph import StateGraph, END

from ia_agent.application.orchestrator.orchestrator_nodes import (
    OrchestratorState,
    get_actions,
    interpret_intent,
    execute_action
)


class OrchestratorGraphService:
    """
    Orchestrator usando LangGraph (StateGraph)
    """

    def __init__(self):
        self.graph = StateGraph(OrchestratorState)

        # Registrar nodos
        self.graph.add_node("get_actions", get_actions)
        self.graph.add_node("interpret_intent", interpret_intent)
        self.graph.add_node("execute_action", execute_action)

        # # Flujo del grafo
        # self.graph.set_entry_point("get_actions")
        # self.graph.add_edge("get_actions", "interpret_intent")
        # self.graph.add_edge("interpret_intent", "execute_action")
        # self.graph.add_edge("execute_action", END)

        # Flujo del grafo
        self.graph.set_entry_point("get_actions")
        self.graph.add_edge("get_actions", END)  # 🔴 TESTING: Detiene después de get_actions
        # self.graph.add_edge("get_actions", "interpret_intent")
        # self.graph.add_edge("interpret_intent", "execute_action")
        # self.graph.add_edge("execute_action", END)

        # Compilar grafo
        self.app = self.graph.compile()

    def process(self, user_message: str, area: str, username: str):
        initial_state: OrchestratorState = {
            "user_message": user_message,
            "area": area,
            "username": username,
            "actions": {},
            "interpretation": {},
            "result": {}
        }

        final_state = self.app.invoke(initial_state)
        return final_state["result"]
