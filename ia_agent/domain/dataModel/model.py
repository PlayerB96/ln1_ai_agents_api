from pydantic import BaseModel, ValidationError, Field
from validations.validators import parsedRespond
from datetime import datetime
from typing import Any, Dict, List
from typing import Optional

class IaRequest(BaseModel):
    message: str = Field(..., example="muestramos todos las epicas de la SCRUMSIST")

