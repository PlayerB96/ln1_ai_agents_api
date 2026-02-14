from infrastructure.config.redis_config import RedisConfig
from langgraph.domain.graph import build_graph
from langgraph.domain.states import ConversationState
from websocket.domain.dataModel.model import WsChatMessageRequest


class LangGraphOrchestrator:

    def __init__(self):
        self.graph = build_graph()
        self.redis = RedisConfig.get_client()

    def run(self, payload: WsChatMessageRequest):

        key = f"conversation:{payload.code_user}"
        previous_state_json = self.redis.get(key)

        if previous_state_json:
            previous_state = ConversationState.model_validate_json(previous_state_json)
            state = previous_state.model_copy(deep=True)
            state.user_message = payload.message
            state.payload = payload
        else:
            state = ConversationState(
                payload=payload,
                user_message=payload.message
            )

        result = self.graph.invoke(state)
        validated = ConversationState.model_validate(result)

        # 🔥 Persistir
        self.redis.set(key, validated.model_dump_json())

        return validated

