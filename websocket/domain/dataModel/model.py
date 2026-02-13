import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from pyparsing import Any


class WsChatMessage(BaseModel):
    message: str


class WsChatMessageRequest(BaseModel):
    message: str
    code_user: str
    fullname: str
    area: str
    canal: str = "ws"
    params_required: Optional[Dict[str, Any]] = None

class WSSuccessResponse(BaseModel):
    success: bool = True
    ws_code: int = 1000
    message: str
    code_user: str
    fullname: Optional[str] = None
    canal: str = "ws"
    area: str = "general"
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    extra: Optional[Dict[str, Any]] = None

class WSErrorResponse(BaseModel):
    success: bool = False
    ws_code: int = 1008
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    extra: Optional[Dict[str, Any]] = None