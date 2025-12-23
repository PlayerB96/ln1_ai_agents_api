"""
Servicio de gestión de conexiones WebSocket para el Runner.
Implementa el patrón "Lazo de Vida" con reconexión automática.
"""
import asyncio
import json
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

from runner.domain.dataModel.model import (
    RunnerCommand,
    RunnerResponse,
    RunnerRegistration,
    RunnerHeartbeat,
    WebSocketMessage
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gestor centralizado de conexiones WebSocket para múltiples Runners.
    Mantiene un registro de todos los Runners conectados y facilita
    la comunicación bidireccional.
    """
    
    def __init__(self):
        # Conexiones activas: {runner_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Información de Runners registrados: {runner_id: RunnerRegistration}
        self.registered_runners: Dict[str, RunnerRegistration] = {}
        
        # Últimos heartbeats: {runner_id: datetime}
        self.last_heartbeat: Dict[str, datetime] = {}
        
        # Respuestas pendientes: {command_id: asyncio.Future}
        self.pending_responses: Dict[str, asyncio.Future] = {}
        
        # Callbacks para comandos personalizados
        self.command_handlers: Dict[str, Callable] = {}
        
        # Lock para operaciones thread-safe
        self._lock = asyncio.Lock()
        
    async def connect(self, websocket: WebSocket, runner_id: str) -> bool:
        """
        Acepta una nueva conexión WebSocket y la registra.
        
        Args:
            websocket: Conexión WebSocket
            runner_id: ID único del Runner
            
        Returns:
            True si la conexión fue exitosa
        """
        try:
            await websocket.accept()
            
            async with self._lock:
                self.active_connections[runner_id] = websocket
                self.last_heartbeat[runner_id] = datetime.now()
                
            logger.info(f"Runner {runner_id} conectado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al conectar Runner {runner_id}: {str(e)}")
            return False
    
    async def disconnect(self, runner_id: str):
        """
        Desconecta un Runner y limpia sus recursos.
        """
        async with self._lock:
            if runner_id in self.active_connections:
                del self.active_connections[runner_id]
            if runner_id in self.registered_runners:
                del self.registered_runners[runner_id]
            if runner_id in self.last_heartbeat:
                del self.last_heartbeat[runner_id]
                
        logger.info(f"Runner {runner_id} desconectado")
    
    async def register_runner(self, runner_id: str, registration: RunnerRegistration):
        """
        Registra un Runner con su información.
        """
        async with self._lock:
            self.registered_runners[runner_id] = registration
            
        logger.info(f"Runner {runner_id} registrado: {registration.client_name}")
    
    async def send_command(
        self, 
        runner_id: str, 
        command: RunnerCommand,
        wait_response: bool = True,
        timeout: int = 30
    ) -> Optional[RunnerResponse]:
        """
        Envía un comando a un Runner específico y opcionalmente espera la respuesta.
        
        Args:
            runner_id: ID del Runner destino
            command: Comando a enviar
            wait_response: Si True, espera la respuesta
            timeout: Timeout en segundos para esperar respuesta
            
        Returns:
            RunnerResponse si wait_response=True, None en caso contrario
        """
        if runner_id not in self.active_connections:
            raise ValueError(f"Runner {runner_id} no está conectado")
        
        websocket = self.active_connections[runner_id]
        
        # Crear mensaje WebSocket con estructura simple: { id, type, payload }
        message = {
            "id": command.command_id,
            "type": "COMMAND",
            "payload": {
                "command_id": command.command_id,
                "command_type": command.command_type,
                "timeout": command.timeout,
                **command.payload  # Desplegar el payload (adapter_type, query, database, etc.)
            }
        }
        
        try:
            # Enviar comando
            await websocket.send_text(json.dumps(message))
            logger.info(f"Comando {command.command_id} enviado a Runner {runner_id}")
            
            # Si se debe esperar respuesta
            if wait_response:
                # Crear Future para esperar respuesta
                future = asyncio.Future()
                self.pending_responses[command.command_id] = future
                
                try:
                    # Esperar respuesta con timeout
                    response_data = await asyncio.wait_for(future, timeout=timeout)
                    return RunnerResponse(**response_data)
                except asyncio.TimeoutError:
                    logger.error(f"Timeout esperando respuesta del comando {command.command_id}")
                    del self.pending_responses[command.command_id]
                    raise TimeoutError(f"Comando {command.command_id} excedió el timeout de {timeout}s")
                    
            return None
            
        except Exception as e:
            logger.error(f"Error enviando comando a Runner {runner_id}: {str(e)}")
            raise
    
    async def broadcast_command(self, command: RunnerCommand):
        """
        Envía un comando a todos los Runners conectados.
        """
        disconnected = []
        
        for runner_id, websocket in self.active_connections.items():
            try:
                # Crear mensaje con estructura simple: { id, type, payload }
                message = {
                    "id": command.command_id,
                    "type": "COMMAND",
                    "payload": {
                        "command_id": command.command_id,
                        "command_type": command.command_type,
                        "timeout": command.timeout,
                        **command.payload  # Desplegar el payload
                    }
                }
                await websocket.send_text(json.dumps(message))
                logger.info(f"Comando broadcast enviado a Runner {runner_id}")
            except Exception as e:
                logger.error(f"Error enviando broadcast a Runner {runner_id}: {str(e)}")
                disconnected.append(runner_id)
        
        # Limpiar conexiones fallidas
        for runner_id in disconnected:
            await self.disconnect(runner_id)
    
    async def handle_message(self, runner_id: str, message_data: str):
        """
        Procesa un mensaje recibido del Runner.
        Estándar: { id, type, message_type, payload }
        """
        try:
            message_dict = json.loads(message_data)
            # Obtener tipo de mensaje (puede venir como 'type' o 'message_type')
            message_type = message_dict.get("type") or message_dict.get("message_type")
            payload = message_dict.get("payload", {})
            message_id = message_dict.get("id")
            
            if message_type in ["REGISTRATION", "AUTH", "WELCOME"]:
                # Procesar registro (compatible con diferentes formatos)
                # Normalizar estructura de datos
                if isinstance(payload, dict):
                    normalized_data = {
                        "runner_id": payload.get("runner_id") or payload.get("runnerId") or runner_id,
                        "client_name": payload.get("client_name") or payload.get("clientName") or "Unknown",
                        "hostname": payload.get("hostname") or "Unknown",
                        "version": payload.get("version") or "1.0.0",
                        "capabilities": payload.get("capabilities") or [],
                        "ip_address": payload.get("ip_address") or payload.get("ipAddress")
                    }
                    registration = RunnerRegistration(**normalized_data)
                    await self.register_runner(runner_id, registration)
                
            elif message_type == "RESPONSE":
                # Procesar respuesta a un comando
                command_id = payload.get("command_id")
                if command_id in self.pending_responses:
                    future = self.pending_responses[command_id]
                    if not future.done():
                        future.set_result(payload)
                    del self.pending_responses[command_id]
                    
            elif message_type == "HEARTBEAT":
                # Actualizar heartbeat
                async with self._lock:
                    self.last_heartbeat[runner_id] = datetime.now()
                logger.debug(f"Heartbeat recibido de Runner {runner_id}")
                
            elif message_type == "ERROR":
                # Procesar error
                logger.error(f"Error reportado por Runner {runner_id}: {payload}")
                
            else:
                logger.warning(f"Tipo de mensaje desconocido: {message_type}")
                
        except Exception as e:
            logger.error(f"Error procesando mensaje de Runner {runner_id}: {str(e)}")
    
    async def send_heartbeat_request(self, runner_id: str):
        """
        Solicita un heartbeat a un Runner específico.
        """
        if runner_id not in self.active_connections:
            return
        
        websocket = self.active_connections[runner_id]
        message = WebSocketMessage(
            message_type="HEARTBEAT_REQUEST",
            data={"runner_id": runner_id}
        )
        
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Error enviando heartbeat request a Runner {runner_id}: {str(e)}")
            await self.disconnect(runner_id)
    
    def get_connected_runners(self) -> list:
        """
        Obtiene la lista de Runners conectados.
        """
        return [
            {
                "runner_id": runner_id,
                "client_name": self.registered_runners.get(runner_id).client_name if runner_id in self.registered_runners else "Unknown",
                "last_heartbeat": self.last_heartbeat.get(runner_id).isoformat() if runner_id in self.last_heartbeat else None,
                "connected": True
            }
            for runner_id in self.active_connections.keys()
        ]
    
    async def check_stale_connections(self, max_idle_seconds: int = 300):
        """
        Verifica y desconecta Runners inactivos.
        
        Args:
            max_idle_seconds: Segundos máximos sin heartbeat antes de desconectar
        """
        now = datetime.now()
        stale_runners = []
        
        async with self._lock:
            for runner_id, last_beat in self.last_heartbeat.items():
                if (now - last_beat).total_seconds() > max_idle_seconds:
                    stale_runners.append(runner_id)
        
        for runner_id in stale_runners:
            logger.warning(f"Runner {runner_id} inactivo, desconectando...")
            await self.disconnect(runner_id)


# Instancia global del gestor de conexiones
connection_manager = ConnectionManager()
