from fastapi.responses import JSONResponse
from fastapi import HTTPException
from gemini.application.gemini_service import GeminiService

class GeminiController:
    def __init__(self, dataModel=None):
        self.dataModel = dataModel
        self.origin = "GeminiController"

    def process_request(self):
        try:
            service = GeminiService(self.dataModel)

            if self.dataModel:
                result = service.generate()
                return JSONResponse(
                    status_code=200,
                    content={"status": True, "msg": "Texto generado exitosamente.", "data": result}
                )

            models = service.list_models()
            return JSONResponse(
                status_code=200,
                content={"status": True, "msg": "Modelos obtenidos correctamente.", "models": models}
            )

        except HTTPException as e:
            
            raise e
        except Exception as e:
            
            raise HTTPException(status_code=500, detail=str(e))
