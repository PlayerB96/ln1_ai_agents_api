from fastapi import HTTPException
from fastapi.responses import JSONResponse
from ia_agent.application.orchestrator_service import OrchestratorService

class IAController:
    def __init__(self, message: str):
        self.message = message

    def handle_request(self):
        try:
            print("Iniciando procesamiento de la solicitud IA...")
            print(f"Entrada del usuario: {self.message}")
            orchestrator = OrchestratorService(self.message)
            result = orchestrator.process()

            return JSONResponse(
                status_code=200,
                content={"status": True, "msg": "Solicitud procesada correctamente", "data": result}
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
