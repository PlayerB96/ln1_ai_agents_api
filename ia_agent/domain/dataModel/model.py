"""
Modelos de datos para el agente IA.
Define las estructuras de entrada/salida de la API.
"""
from pydantic import BaseModel, Field
from typing import Optional


class IaRequest(BaseModel):
    """Modelo de solicitud para el agente IA"""
    message: str = Field(
        ..., 
        example="Muéstrame todas las épicas del proyecto SCRUMSIST",
        description="Mensaje del usuario en lenguaje natural"
    )
    area: str = Field(
        ..., 
        example="sistemas",
        description="Área del agente (sistemas, rrhh, etc.)"
    )
    username: Optional[str] = Field(
        None, 
        example="Bryan Rafael",
        description="Nombre del usuario que realiza la solicitud"
    )