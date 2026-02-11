from pydantic import BaseModel


class IaChatMessage(BaseModel):
    message: str
