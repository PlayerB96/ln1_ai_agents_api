from fastapi import HTTPException
from fastapi.responses import JSONResponse
from ia_agent.application.orchestrator_service import OrchestratorService
from ia_agent.domain.dataModel.model import IaRequest

class IAController:
    def __init__(self, data: IaRequest ):
        self.message = data.message
        self.area = data.area
        self.username = data.username 
        
    def handle_request(self):
        try:
            print("Iniciando procesamiento de la solicitud IA...")
            print(f"Entrada del usuario: {self.message}, Área: {self.area}")
            orchestrator = OrchestratorService(self.message, self.area, self.username )
            result = orchestrator.process()

            return JSONResponse(
                status_code=200,
                content={"status": True, "msg": "Solicitud procesada correctamente", "data": result}
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
