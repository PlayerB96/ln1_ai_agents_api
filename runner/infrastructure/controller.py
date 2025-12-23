"""
Controlador para gestionar las conexiones y comandos del Runner.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from runner.application.runner_service import connection_manager
from runner.domain.dataModel.model import RunnerCommand, RunnerResponse

logger = logging.getLogger(__name__)


class RunnerController:
    """
    Controlador que facilita la interacción con los Runners conectados.
    """
    
    def __init__(self):
        self.manager = connection_manager
    
    def get_connected_runners(self) -> Dict[str, Any]:
        """
        Obtiene información de todos los Runners conectados.
        """
        try:
            runners_list = []
            for runner_id in self.manager.active_connections.keys():
                runner_info = {
                    "runner_id": runner_id,
                    "connected": True,
                    "last_heartbeat": self.manager.last_heartbeat.get(runner_id).isoformat() if runner_id in self.manager.last_heartbeat else None
                }
                
                # Agregar información de registro si existe
                if runner_id in self.manager.registered_runners:
                    reg = self.manager.registered_runners[runner_id]
                    runner_info.update({
                        "client_name": reg.client_name,
                        "hostname": reg.hostname,
                        "version": reg.version,
                        "capabilities": reg.capabilities,
                        "ip_address": reg.ip_address
                    })
                
                runners_list.append(runner_info)
            
            return {
                "status": True,
                "data": {
                    "runners": runners_list,
                    "total_connected": len(runners_list)
                },
                "message": f"Se encontraron {len(runners_list)} runner(s) conectado(s)"
            }
        except Exception as e:
            logger.error(f"Error obteniendo runners conectados: {str(e)}")
            return {
                "status": False,
                "data": None,
                "message": f"Error al obtener runners: {str(e)}"
            }
    
    async def execute_sql_query(
        self, 
        runner_id: str,
        adapter_type: str,
        query: str,
        database: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Ejecuta una consulta SQL en el Runner especificado.
        
        Args:
            runner_id: ID del Runner donde ejecutar la consulta
            adapter_type: Tipo de base de datos (mysql|postgres|redis|mongo)
            query: Query SQL a ejecutar
            database: Nombre de la base de datos (opcional)
            timeout: Timeout en segundos
            
        Returns:
            Diccionario con el resultado de la ejecución
        """
        try:
            # Crear comando
            command = RunnerCommand(
                command_id=str(uuid.uuid4()),
                command_type="SQL_QUERY",
                payload={
                    "adapter_type": adapter_type,
                    "query": query,
                    "database": database
                },
                timeout=timeout
            )
            
            # Enviar comando y esperar respuesta
            response = await self.manager.send_command(
                runner_id=runner_id,
                command=command,
                wait_response=True,
                timeout=timeout
            )
            
            if response.success:
                return {
                    "status": True,
                    "data": response.data,
                    "message": "Consulta ejecutada exitosamente"
                }
            else:
                return {
                    "status": False,
                    "data": None,
                    "message": f"Error ejecutando consulta: {response.error}"
                }
                
        except TimeoutError as e:
            return {
                "status": False,
                "data": None,
                "message": f"Timeout ejecutando consulta: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error ejecutando SQL query: {str(e)}")
            return {
                "status": False,
                "data": None,
                "message": f"Error: {str(e)}"
            }
    
    async def get_system_info(
        self, 
        runner_id: str,
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        Obtiene información del sistema donde corre el Runner.
        
        Args:
            runner_id: ID del Runner
            timeout: Timeout en segundos
            
        Returns:
            Diccionario con información del sistema
        """
        try:
            command = RunnerCommand(
                command_id=str(uuid.uuid4()),
                command_type="SYSTEM_INFO",
                payload={},
                timeout=timeout
            )
            
            response = await self.manager.send_command(
                runner_id=runner_id,
                command=command,
                wait_response=True,
                timeout=timeout
            )
            
            if response.success:
                return {
                    "status": True,
                    "data": response.data,
                    "message": "Información del sistema obtenida"
                }
            else:
                return {
                    "status": False,
                    "data": None,
                    "message": f"Error obteniendo información: {response.error}"
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo system info: {str(e)}")
            return {
                "status": False,
                "data": None,
                "message": f"Error: {str(e)}"
            }
    
    async def execute_custom_command(
        self,
        runner_id: str,
        command_type: str,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Ejecuta un comando personalizado en el Runner.
        
        Args:
            runner_id: ID del Runner
            command_type: Tipo de comando personalizado
            payload: Datos del comando
            timeout: Timeout en segundos
            
        Returns:
            Diccionario con el resultado
        """
        try:
            command = RunnerCommand(
                command_id=str(uuid.uuid4()),
                command_type=command_type,
                payload=payload,
                timeout=timeout
            )
            
            response = await self.manager.send_command(
                runner_id=runner_id,
                command=command,
                wait_response=True,
                timeout=timeout
            )
            
            if response.success:
                return {
                    "status": True,
                    "data": response.data,
                    "message": f"Comando {command_type} ejecutado exitosamente"
                }
            else:
                return {
                    "status": False,
                    "data": None,
                    "message": f"Error ejecutando comando: {response.error}"
                }
                
        except Exception as e:
            logger.error(f"Error ejecutando comando personalizado: {str(e)}")
            return {
                "status": False,
                "data": None,
                "message": f"Error: {str(e)}"
            }
    
    async def broadcast_command(
        self,
        command_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Envía un comando a todos los Runners conectados.
        
        Args:
            command_type: Tipo de comando
            payload: Datos del comando
            
        Returns:
            Diccionario con el resultado
        """
        try:
            command = RunnerCommand(
                command_id=str(uuid.uuid4()),
                command_type=command_type,
                payload=payload
            )
            
            await self.manager.broadcast_command(command)
            
            return {
                "status": True,
                "data": {
                    "command_id": command.command_id,
                    "broadcasted_to": len(self.manager.active_connections)
                },
                "message": f"Comando enviado a {len(self.manager.active_connections)} runner(s)"
            }
            
        except Exception as e:
            logger.error(f"Error broadcasting comando: {str(e)}")
            return {
                "status": False,
                "data": None,
                "message": f"Error: {str(e)}"
            }
