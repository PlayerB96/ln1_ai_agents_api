from pydantic import BaseModel, ValidationError, Field
from validations.validators import parsedRespond
from datetime import datetime
from typing import Any, Dict, List
from typing import Optional

class JiraRequest(BaseModel):
    accion: str = Field(..., example="documentar")
    ticket_id:  Optional[str] = None
    proyecto_id: str = Field(..., example="SCRUMSIST")
    descripcion: Optional[str] = None
    
