from langgraph.application.lang_response import LangGraphResponse
from websocket.domain.dataModel.model import WsChatMessageRequest
from langgraph.application.orchestrator import LangGraphOrchestrator

class LangGraphController:
    def __init__(self, payload: WsChatMessageRequest):
        self.payload = payload
        self.langResponse = LangGraphResponse()
        self.langOrchestrator = LangGraphOrchestrator()

    def langController(self):
        wsresponse = self.langOrchestrator.run(self.payload)

        return wsresponse
