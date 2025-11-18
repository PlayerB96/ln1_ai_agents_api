from fastapi import APIRouter

from ia_agent.domain.dataModel.model import IaRequest
from ia_agent.infrastructure.ia_controller import IAController

ia = APIRouter()

@ia.post("/ia/agent", tags=["IA Agent"])
def process_agent_message(data: IaRequest):
    """
    Recibe un texto natural y deja que el agente IA determine la acción.
    Ejemplo:
    {
        "message": "Muéstrame las tareas del epic LN1-234"
    }
    """
    controller = IAController(data)
    return controller.handle_request()
