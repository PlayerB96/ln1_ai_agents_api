from langgraph.domain.states import ConversationState
from langgraph.application.lang_response import LangGraphResponse
from langgraph.application.node_context import NodeContext
import json


def build_prompt_classifier_node(context: NodeContext):

    def node(state: ConversationState) -> ConversationState:
        redis_client = context.redis
        rule_key = "agente:rule:intent:classifier"

        try:
            rule_type = redis_client.type(rule_key)
            classifier_prompt = None

            if rule_type == "ReJSON-RL":
                rule_json = redis_client.execute_command("JSON.GET", rule_key)
                if rule_json:
                    rule_data = json.loads(rule_json)
                    classifier_prompt = rule_data.get("prompt")

            elif rule_type == "string":
                classifier_prompt = redis_client.get(rule_key)

            if not classifier_prompt:
                state.metadata["classifier_prompt"] = None
                state.step = "rule_classified_error"
                return state

            enriched_prompt = classifier_prompt.replace(
                "{user_message}", state.user_message
            )

            state.metadata["classifier_prompt"] = enriched_prompt
            state.metadata["classifier_template"] = classifier_prompt
            state.step = "rule_classified"

            return state

        except Exception as e:
            print(f"❌ Error build_prompt_classifier_node: {e}")
            state.metadata["classifier_prompt"] = None
            state.step = "rule_classified_error"
            return state

    return node



def llm_classifier_node(context: NodeContext):

    def node(state: ConversationState) -> ConversationState:
        prompt = state.metadata.get("classifier_prompt")

        if not prompt:
            state.intent = "desconocida"
            state.step = "llm_classifier_done_error"
            return state

        try:
            response = context.llm.generate_text(prompt)

            raw_text = response.get("text", "")
            intent = raw_text.strip().split("\n")[0].lower()

            state.intent = intent
            state.llm_response = intent
            state.metadata["classified_intent"] = intent
            state.metadata["tokens_used"] = response.get("tokens", {})
            state.metadata["finish_reason"] = response.get(
                "finish_reason", "UNKNOWN"
            )
            state.step = "llm_classifier_done"

            return state

        except Exception as e:
            print(f"❌ Error llm_classifier_node: {e}")
            state.intent = "desconocida"
            state.step = "llm_classifier_done_error"
            return state

    return node



def actions_retriever_node(context: NodeContext):

    def node(state: ConversationState) -> ConversationState:
        intent = state.intent

        if not intent:
            state.metadata["matched_actions"] = []
            state.metadata["matched_count"] = 0
            state.step = "actions_retriever_error"
            return state

        try:
            matched_actions = LangGraphResponse.fetch_and_filter_actions(
                context.redis,
                intent
            )

            state.metadata["matched_actions"] = matched_actions
            state.metadata["matched_count"] = len(matched_actions)
            state.step = "actions_retrieved"

            return state

        except Exception as e:
            print(f"❌ Error actions_retriever_node: {e}")
            state.metadata["matched_actions"] = []
            state.metadata["matched_count"] = 0
            state.step = "actions_retriever_error"
            return state

    return node

