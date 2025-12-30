"""
Controlador de infraestructura para el agente IA.
Maneja las peticiones HTTP y coordina con el orquestador.
"""
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from ia_agent.application.orchestrator.orchestrator_service import OrchestratorGraphService
from ia_agent.domain.dataModel.model import IaRequest
from validations.logger import logErrorJson, logSuccess, logInfo


class IAController:
    """Controlador para procesar solicitudes del agente IA"""
    
    def __init__(self, data: IaRequest):
        """
        Inicializa el controlador.
        
        Args:
            data: Datos de la solicitud
        """
        self.data = data  # Almacena todo el objeto
        self.origin = "IAController"
    
    def handle_request(self) -> JSONResponse:
        """
        Procesa la solicitud del usuario.
        
        Returns:
            JSONResponse con el resultado del procesamiento
            
        Raises:
            HTTPException: Si ocurre un error durante el procesamiento
        """
        try:
            logInfo(f"Procesando solicitud IA: {self.data.message}", origin=self.origin)
            
            orchestrator = OrchestratorGraphService()
            # Pasar datos como dict - escalable
            result = orchestrator.process(**self.data.model_dump())
            
            # Respetar el status que viene del orquestador
            # Si el result ya tiene status, usarlo; si no, asumir éxito
            result_status = result.get("status", True)
            result_msg = result.get("msg", "Solicitud procesada correctamente")
            result_data = result.get("data", {})
            
            logSuccess(f"Solicitud IA procesada: {result_msg}", origin=self.origin, extra_data={"message": self.data.message})
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": result_status,
                    "msg": result_msg,
                    "data": result_data
                }
            )
            
        except HTTPException as e:
            logErrorJson(
                error_message=str(e.detail),
                error_type="HTTPException",
                origin=self.origin,
                extra_data={"status_code": e.status_code}
            )
            raise e
        except Exception as e:
            logErrorJson(
                error_message=str(e),
                error_type=type(e).__name__,
                origin=self.origin,
                exception=e
            )
            raise HTTPException(status_code=500, detail=str(e))
