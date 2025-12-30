"""
Modelos de datos para el agente IA.
Define las estructuras de entrada/salida de la API.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class IaRequest(BaseModel):
    """Modelo de solicitud para el agente IA"""
    message: str = Field(
        ..., 
        example="Muéstrame todas las épicas del proyecto LN1SCRUM",
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
    company: str = Field(
        default="ln1",
        example="ln1",
        description="Identificador de la compañía/tenant"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        example=["jira", "proyecto"],
        description="Tags opcionales para filtrar acciones específicas"
    )