from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from websocket.domain.dataModel.model import WsChatMessageRequest


class ConversationState(BaseModel):
    payload: WsChatMessageRequest

    user_message: str
    llm_response: Optional[str] = None

    intent: Optional[str] = None
    step: str = "start"

    metadata: Dict[str, Any] = {}
