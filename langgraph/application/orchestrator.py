from langgraph.domain.graph import build_graph
from langgraph.domain.states import ConversationState
from websocket.domain.dataModel.model import WsChatMessageRequest


class LangGraphOrchestrator:
    def __init__(self):
        # Construye y compila el pipeline de LangGraph para reutilizarlo.
        self.graph = build_graph()

    def run(self, payload: WsChatMessageRequest) -> ConversationState:
        # Inicializa el estado de conversacion con el request entrante.
        state = ConversationState(
            payload=payload,
            user_message=payload.message
        )

        # Ejecuta el grafo; los nodos enriquecen/modifican el estado.
        result = self.graph.invoke(state)
        return ConversationState.model_validate(result)
        # return self.graph.invoke(state)
