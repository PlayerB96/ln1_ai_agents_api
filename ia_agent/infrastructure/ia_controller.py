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
        self.data = data  # Almacena todo el objeto
    
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
            # Pasar datos como dict - escalable
            result = orchestrator.process(**self.data.model_dump())
            
            # Respetar el status que viene del orquestador
            # Si el result ya tiene status, usarlo; si no, asumir éxito
            result_status = result.get("status", True)
            result_msg = result.get("msg", "Solicitud procesada correctamente")
            result_data = result.get("data", {})
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": result_status,
                    "msg": result_msg,
                    "data": result_data
                }
            )
            
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
