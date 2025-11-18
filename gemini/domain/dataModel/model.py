from pydantic import BaseModel
from typing import Optional

class GeminiRequest(BaseModel):
    question: Optional[str] = "Que es Gemini"  # contexto por defecto
    context: Optional[str] = "Responde de forma clara, breve y en español."  # contexto por defecto
    model: Optional[str] = "gemini-2.5-flash"
    temperature: Optional[float] = 0.7
    
