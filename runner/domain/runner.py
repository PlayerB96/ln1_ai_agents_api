"""
Router principal del módulo Runner.
Define los endpoints WebSocket y REST para gestionar las conexiones del Runner.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Body
from typing import Optional, Dict, Any
import logging

from runner.application.runner_service import connection_manager
from runner.infrastructure.controller import RunnerController
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

runner = APIRouter()


# Modelos para los endpoints REST
class SQLQueryRequest(BaseModel):
    """Modelo para ejecutar consultas SQL."""
    runner_id: str = Field(..., description="ID del Runner donde ejecutar la consulta")
    adapter_type: str = Field(..., description="Tipo de base de datos: mysql|postgres|redis|mongo")
    query: str = Field(..., description="Consulta SQL a ejecutar")
    database: Optional[str] = Field(None, description="Nombre de la base de datos")
    timeout: int = Field(30, description="Timeout en segundos")


class CustomCommandRequest(BaseModel):
    """Modelo para comandos personalizados."""
    runner_id: str = Field(..., description="ID del Runner")
    command_type: str = Field(..., description="Tipo de comando")
    payload: Dict[str, Any] = Field(..., description="Datos del comando")
    timeout: int = Field(30, description="Timeout en segundos")


class BroadcastCommandRequest(BaseModel):
    """Modelo para broadcast de comandos."""
    command_type: str = Field(..., description="Tipo de comando")
    payload: Dict[str, Any] = Field(..., description="Datos del comando")


# ============================================================================
# WEBSOCKET ENDPOINT - Conexión permanente del Runner
# ============================================================================

@runner.websocket("/runner/connect")
async def runner_connect(
    websocket: WebSocket,
    runner_id: str = Query(..., description="ID único del Runner")
):
    """
    **Endpoint Principal WebSocket - Punto de Conexión del Runner Local**
    
    🔌 **URL de Conexión:** `wss://tu-api.com/api/v1/runner/connect?runner_id=RUNNER_001`
    
    Este es el punto de entrada para el "Lazo de Vida":
    
    1. El Runner (en la oficina del cliente) se conecta a este WebSocket
    2. La conexión permanece abierta para comunicación bidireccional
    3. El Runner puede recibir comandos en cualquier momento
    4. El Runner envía respuestas y heartbeats por la misma conexión
    5. Si la conexión se pierde, el Runner intentará reconectarse automáticamente
    
    **Flujo de mensajes:**
    - REGISTRATION: El Runner se registra al conectarse
    - HEARTBEAT: Mensajes periódicos para mantener la conexión viva
    - COMMAND: Comandos enviados desde la API al Runner
    - RESPONSE: Respuestas del Runner a los comandos
    - ERROR: Notificaciones de errores
    
    **Ejemplo de uso desde el cliente Runner:**
    ```python
    # Conectar al WebSocket
    uri = "wss://tu-api.com/api/v1/runner/connect?runner_id=RUNNER_001"
    async with websockets.connect(uri) as websocket:
        # Enviar registro
        await websocket.send(json.dumps({
            "message_type": "REGISTRATION",
            "data": {
                "runner_id": "RUNNER_001",
                "client_name": "Empresa XYZ",
                "hostname": "PC-OFICINA-01",
                "version": "1.0.0"
            }
        }))
        
        # Escuchar mensajes
        async for message in websocket:
            # Procesar comandos...
    ```
    """
    logger.info(f"Intento de conexión WebSocket del Runner: {runner_id}")
    
    # Aceptar la conexión
    connected = await connection_manager.connect(websocket, runner_id)
    
    if not connected:
        logger.error(f"No se pudo establecer conexión con Runner {runner_id}")
        return
    
    try:
        # Enviar mensaje de bienvenida
        welcome_message = {
            "message_type": "WELCOME",
            "data": {
                "runner_id": runner_id,
                "message": "Conexión establecida exitosamente. Tubo permanente creado.",
                "server_time": str(connection_manager.last_heartbeat.get(runner_id))
            }
        }
        await websocket.send_json(welcome_message)
        
        # Loop principal - escuchar mensajes del Runner
        while True:
            try:
                # Esperar mensaje del Runner
                message = await websocket.receive_text()
                print(f"Mensaje recibido del Runner {runner_id}: {message}")
                # Procesar el mensaje
                await connection_manager.handle_message(runner_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"Runner {runner_id} se desconectó normalmente")
                break
                
            except Exception as e:
                logger.error(f"Error procesando mensaje de Runner {runner_id}: {str(e)}")
                # Enviar mensaje de error al Runner
                error_message = {
                    "message_type": "ERROR",
                    "data": {
                        "error": str(e),
                        "message": "Error procesando tu mensaje"
                    }
                }
                try:
                    await websocket.send_json(error_message)
                except:
                    break
                    
    except Exception as e:
        logger.error(f"Error en conexión WebSocket con Runner {runner_id}: {str(e)}")
    
    finally:
        # Limpiar la conexión
        await connection_manager.disconnect(runner_id)
        logger.info(f"Conexión WebSocket cerrada para Runner {runner_id}")


# ============================================================================
# REST ENDPOINTS - Gestión y comandos
# ============================================================================

@runner.get("/runner/status", tags=["Runner"])
def get_runners_status():
    """
    **Obtiene el estado de todos los Runners conectados.**
    
    Retorna información sobre:
    - Runners actualmente conectados
    - Última vez que enviaron heartbeat
    - Información de registro (nombre del cliente, hostname, etc.)
    
    Útil para:
    - Monitoreo del estado de las conexiones
    - Dashboard de administración
    - Verificar que los Runners estén vivos
    """
    controller = RunnerController()
    return controller.get_connected_runners()


@runner.post("/runner/command/sql", tags=["Runner"])
async def execute_sql_query(request: SQLQueryRequest):
    """
    **Ejecuta una consulta SQL en un Runner específico.**
    
    Este endpoint permite enviar consultas SQL al Runner en la oficina del cliente.
    El Runner ejecutará la consulta en su base de datos local y retornará los resultados.
    
    **Ejemplo:**
    ```json
    {
        "runner_id": "RUNNER_001",
        "adapter_type": "mysql",
        "query": "SELECT * FROM ventas WHERE fecha > '2024-01-01'",
        "database": "db_ventas",
        "timeout": 30
    }
    ```
    
    **Casos de uso:**
    - Consultar datos en tiempo real desde bases de datos en la oficina del cliente
    - Obtener reportes sin necesidad de replicación de datos
    - Ejecutar queries de análisis bajo demanda
    """
    controller = RunnerController()
    return await controller.execute_sql_query(
        runner_id=request.runner_id,
        adapter_type=request.adapter_type,
        query=request.query,
        database=request.database,
        timeout=request.timeout
    )


@runner.post("/runner/command/system-info", tags=["Runner"])
async def get_system_info(
    runner_id: str = Body(..., embed=True, description="ID del Runner"),
    timeout: int = Body(15, embed=True, description="Timeout en segundos")
):
    """
    **Obtiene información del sistema donde corre el Runner.**
    
    Retorna datos como:
    - Uso de CPU y memoria
    - Espacio en disco
    - Información del sistema operativo
    - Procesos activos
    
    Útil para:
    - Monitoreo de recursos
    - Diagnóstico de problemas
    - Planificación de capacidad
    """
    controller = RunnerController()
    return await controller.get_system_info(
        runner_id=runner_id,
        timeout=timeout
    )


@runner.post("/runner/command/custom", tags=["Runner"])
async def execute_custom_command(request: CustomCommandRequest):
    """
    **Ejecuta un comando personalizado en el Runner.**
    
    Este endpoint permite enviar cualquier tipo de comando personalizado
    que hayas implementado en tu Runner.
    
    **Ejemplos de comandos personalizados:**
    - FILE_READ: Leer un archivo del sistema
    - FILE_WRITE: Escribir un archivo
    - EXECUTE_SCRIPT: Ejecutar un script
    - BACKUP_DATABASE: Hacer backup de base de datos
    - RESTART_SERVICE: Reiniciar un servicio
    
    **Ejemplo:**
    ```json
    {
        "runner_id": "RUNNER_001",
        "command_type": "FILE_READ",
        "payload": {
            "file_path": "C:\\datos\\config.json"
        },
        "timeout": 30
    }
    ```
    """
    controller = RunnerController()
    return await controller.execute_custom_command(
        runner_id=request.runner_id,
        command_type=request.command_type,
        payload=request.payload,
        timeout=request.timeout
    )


@runner.post("/runner/command/broadcast", tags=["Runner"])
async def broadcast_command(request: BroadcastCommandRequest):
    """
    **Envía un comando a todos los Runners conectados.**
    
    Útil para:
    - Actualizaciones masivas
    - Notificaciones a todos los clientes
    - Comandos de mantenimiento
    - Sincronización de configuraciones
    
    **Ejemplo:**
    ```json
    {
        "command_type": "UPDATE_CONFIG",
        "payload": {
            "config_key": "max_connections",
            "config_value": "100"
        }
    }
    ```
    
    **Nota:** Este comando no espera respuesta de los Runners.
    """
    controller = RunnerController()
    return await controller.broadcast_command(
        command_type=request.command_type,
        payload=request.payload
    )


@runner.get("/runner/health", tags=["Runner"])
async def health_check():
    """
    **Verifica el estado del servicio Runner.**
    
    Endpoint simple para verificar que el servicio está funcionando.
    Útil para:
    - Health checks de Kubernetes/Docker
    - Monitoreo de uptime
    - Load balancers
    """
    return {
        "status": True,
        "data": {
            "service": "runner",
            "version": "1.0.0",
            "active_connections": len(connection_manager.active_connections)
        },
        "message": "Servicio Runner operativo"
    }
