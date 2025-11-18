from fastapi import APIRouter

from gemini.domain.dataModel.model import GeminiRequest
from gemini.infrastructure.controller import GeminiController


gemini = APIRouter()

# ---------------------------------------
# Endpoint principal
# ---------------------------------------
@gemini.post("/gemini/query", tags=["Gemini"])
def gemini_query(req: GeminiRequest):
    """
    Envía una pregunta al modelo Gemini y devuelve una respuesta clara y legible.
    """
    controller = GeminiController(req)
    return controller.process_request()


@gemini.get("/gemini/models", tags=["Gemini"])
def list_models():
    """
    Lista los modelos disponibles en tu cuenta de Google Cloud.
    """
    controller = GeminiController()
    return controller.process_request()
