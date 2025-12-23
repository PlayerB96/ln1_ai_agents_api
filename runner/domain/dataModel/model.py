"""
Modelos de datos para el módulo Runner.
Define las estructuras de mensajes WebSocket y comandos.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime


class RunnerCommand(BaseModel):
    """
    Comando que la API envía al Runner para ejecutar en el cliente.
    """
    command_id: str = Field(..., description="ID único del comando")
    command_type: str = Field(..., description="Tipo de comando: SQL_QUERY, FILE_READ, SYSTEM_INFO, etc.")
    payload: Dict[str, Any] = Field(..., description="Datos específicos del comando")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Timestamp del comando")
    timeout: Optional[int] = Field(default=30, description="Timeout en segundos")


class RunnerResponse(BaseModel):
    """
    Respuesta que el Runner envía de vuelta a la API.
    """
    command_id: str = Field(..., description="ID del comando que se está respondiendo")
    success: bool = Field(..., description="Indica si el comando se ejecutó exitosamente")
    data: Optional[Any] = Field(None, description="Datos de respuesta")
    error: Optional[str] = Field(None, description="Mensaje de error si falló")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Timestamp de la respuesta")


class RunnerRegistration(BaseModel):
    """
    Datos de registro cuando un Runner se conecta.
    """
    runner_id: str = Field(..., description="ID único del Runner")
    client_name: str = Field(..., description="Nombre de la empresa/cliente")
    hostname: Optional[str] = Field(None, description="Nombre del host donde corre el Runner")
    ip_address: Optional[str] = Field(None, description="IP del cliente")
    version: Optional[str] = Field(default="1.0.0", description="Versión del Runner")
    capabilities: Optional[Union[List[str], Dict[str, bool]]] = Field(
        default_factory=list,
        description="Capacidades del Runner (lista o diccionario)"
    )


class RunnerHeartbeat(BaseModel):
    """
    Heartbeat para mantener la conexión viva.
    """
    runner_id: str = Field(..., description="ID del Runner")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp del heartbeat")
    status: str = Field(default="alive", description="Estado del Runner")


class WebSocketMessage(BaseModel):
    """
    Mensaje genérico para WebSocket.
    """
    message_type: str = Field(..., description="Tipo: REGISTRATION, COMMAND, RESPONSE, HEARTBEAT, ERROR")
    data: Dict[str, Any] = Field(..., description="Contenido del mensaje")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Timestamp del mensaje")
