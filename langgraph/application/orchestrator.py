from langgraph.domain.graph import build_graph
from langgraph.domain.states import ConversationState
from websocket.domain.dataModel.model import WsChatMessageRequest


class LangGraphOrchestrator:
    def __init__(self):
        # Construye y compila el pipeline de LangGraph para reutilizarlo.
        self.graph = build_graph()
        if not hasattr(self.__class__, "_last_state_by_user"):
            self.__class__._last_state_by_user = {}

    def run(self, payload: WsChatMessageRequest) -> ConversationState:
        last_state_by_user = self.__class__._last_state_by_user
        previous_state = last_state_by_user.get(payload.code_user)

        if previous_state:
            # 🔥 Reusar estado anterior SIEMPRE
            state = previous_state.model_copy(deep=True)
            state.user_message = payload.message
            state.payload = payload  # actualizar payload completo
        else:
            # Primera interacción
            state = ConversationState(
                payload=payload,
                user_message=payload.message
            )

        result = self.graph.invoke(state)
        validated = ConversationState.model_validate(result)

        # 🔥 Guardar estado actualizado
        last_state_by_user[payload.code_user] = validated

        return validated
