from langgraph.infrastructure.lang_controller import LangGraphController
from websocket.application.response import WsChatAplicationResponse
from websocket.domain.dataModel.model import WsChatMessageRequest

class WSChatController:
    def __init__(self, payload: WsChatMessageRequest):
        self.payload = payload
        self.wsresponse = WsChatAplicationResponse(payload)
        self.langgraph = LangGraphController(payload)

    def wsController(self):
        wsresponse = self.wsresponse.process_request()

        if wsresponse.success:
            # ✅ enviar payload completo a LangGraph
            conversation_state  = self.langgraph.langController()

        return conversation_state
