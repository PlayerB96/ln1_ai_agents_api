from fastapi.responses import JSONResponse
from fastapi import HTTPException
from gemini.application.gemini_service import GeminiService
from validations.logger import logErrorJson, logSuccess, logInfo

class GeminiController:
    def __init__(self, dataModel=None):
        self.dataModel = dataModel
        self.origin = "GeminiController"

    def process_request(self):
        try:
            service = GeminiService(self.dataModel)

            if self.dataModel:
                logInfo("🧠 Generando contenido con Gemini...", origin=self.origin)
                result = service.generate()
                logSuccess("Contenido generado exitosamente", origin=self.origin, extra_data={"model": "Gemini"})
                return JSONResponse(
                    status_code=200,
                    content={"status": True, "msg": "Texto generado exitosamente.", "data": result}
                )

            logInfo("📋 Listando modelos disponibles...", origin=self.origin)
            models = service.list_models()
            logSuccess("Modelos obtenidos correctamente", origin=self.origin)
            return JSONResponse(
                status_code=200,
                content={"status": True, "msg": "Modelos obtenidos correctamente.", "models": models}
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
