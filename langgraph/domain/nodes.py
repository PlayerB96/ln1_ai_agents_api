from langgraph.domain.states import ConversationState
from langgraph.application.lang_response import LangGraphResponse
from langgraph.application.node_context import NodeContext
import json


def entry_router_node(context: NodeContext):

    def node(state: ConversationState) -> ConversationState:
        print("ENTRY ROUTER STEP:", state.step)
        print("USER MESSAGE:", state.user_message)
        print("PAYLOAD PARAMS:", state.payload.params_required)

        # Detectar si el usuario está enviando params_required
        if not state.payload.params_required and state.user_message:
            try:
                parsed_message = json.loads(state.user_message)
                if isinstance(parsed_message, dict) and "params_required" in parsed_message:
                    state.payload.params_required = parsed_message.get("params_required")
            except json.JSONDecodeError:
                pass

        if state.payload.params_required:
            state.step = "params_received"
        else:
            matched_actions = state.metadata.get("matched_actions", [])
            valid_action_ids = {a.get("id") for a in matched_actions if a.get("id")}
            if state.user_message and state.user_message in valid_action_ids:
                state.step = "action_id_received"
            else:
                state.step = "normal_flow"
        return state

    return node


def entry_router(state: ConversationState) -> str:
    if state.step == "params_received":
        return "params"
    if state.step == "action_id_received":
        return "action_select"
    return "classify"


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
            ).replace(
                "{fullname}", state.payload.fullname
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
            print(f"🧮 Tokens usados: {response.get('tokens', {})}")

            raw_text = response.get("text", "")
            lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
            intent = (lines[0] if lines else "desconocida").lower()
            suggestion = lines[1] if len(lines) > 1 else ""

            state.intent = intent
            state.llm_response = suggestion or intent
            state.metadata["classified_intent"] = intent
            state.metadata["llm_suggestion"] = suggestion
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


def action_selector_node(context: NodeContext):

    def node(state: ConversationState) -> ConversationState:
        user_input = (state.user_message or "").strip()
        matched_actions = state.metadata.get("matched_actions", [])

        # IDs válidos que se enviaron al usuario
        valid_action_ids = {a.get("id") for a in matched_actions if a.get("id")}

        if not user_input or user_input not in valid_action_ids:
            state.step = "action_invalid"
            state.metadata["selected_action"] = None
            return state

        # Acción válida
        selected_action = next(
            a for a in matched_actions if a["id"] == user_input
        )

        state.metadata["selected_action"] = selected_action
        state.step = "action_selected"
        return state

    return node


def execute_action_node(context: NodeContext):

    def node(state: ConversationState) -> ConversationState:
        action = state.metadata.get("selected_action")

        # Construir objeto de parámetros requeridos (solo nombres de parámetros)
        required_params = action.get("required", [])
        params_required = {param: "" for param in required_params}
        
        state.metadata["params_required"] = params_required
        state.llm_response = "Por favor rellena los siguientes parametros requeridos:"
        state.step = "action_executed"
        
        return state

    return node

def action_selector_router(state: ConversationState) -> str:
    if state.step == "action_selected":
        return "valid"
    return "wait"


def params_processor_node(context: NodeContext):

    def node(state: ConversationState) -> ConversationState:
        # Procesar los parámetros recibidos del usuario
        params_from_user = state.payload.params_required
        
        if params_from_user:
            # Actualizar params_required con los datos del usuario
            state.metadata["params_required"] = params_from_user
            state.llm_response = "Por favor confirma la accion para iniciar con la accion"
            state.step = "params_completed"
        else:
            state.step = "params_missing"
        
        return state

    return node


def params_router(state: ConversationState) -> str:
    if state.step == "params_completed":
        return "complete"
    return "wait"


def wait_for_user_input_node(context: NodeContext):

    def node(state: ConversationState) -> ConversationState:
        # No hace nada.
        # El socket debe reinvocar el grafo con un nuevo user_message.
        state.step = "waiting_user_input"
        return state

    return node
