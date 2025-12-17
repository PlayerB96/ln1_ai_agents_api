"""
Controlador de infraestructura para el agente IA.
Maneja las peticiones HTTP y coordina con el orquestador.
"""
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from ia_agent.application.orchestrator.orchestrator_service import OrchestratorGraphService
from ia_agent.domain.dataModel.model import IaRequest


class IAController:
    """Controlador para procesar solicitudes del agente IA"""
    
    def __init__(self, data: IaRequest):
        """
        Inicializa el controlador.
        
        Args:
            data: Datos de la solicitud
        """
        self.message = data.message
        self.area = data.area
        self.username = data.username
    
    def handle_request(self) -> JSONResponse:
        """
        Procesa la solicitud del usuario.
        
        Returns:
            JSONResponse con el resultado del procesamiento
            
        Raises:
            HTTPException: Si ocurre un error durante el procesamiento
        """
        try:
            orchestrator = OrchestratorGraphService()
            result = orchestrator.process(
                user_message=self.message,
                area=self.area,
                username=self.username
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": True,
                    "msg": "Solicitud procesada correctamente",
                    "data": result
                }
            )
            
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
