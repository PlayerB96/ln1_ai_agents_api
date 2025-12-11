import json
from fastapi import HTTPException
from sistemas.application.jira_service import JiraService

from .redis_action_store import RedisActionStore
from .intent_engine import IntentEngine
from .action_loader import ActionLoader


class OrchestratorService:

    def __init__(self, user_message: str, area: str, username: str):
        self.user_message = user_message
        self.area = area
        self.username = username
        self.jira_service = JiraService(None)

    def process(self):
        # 1. Obtener acciones desde Redis
        actions = RedisActionStore.get_all()

        # 2. Interpretar intención con IA
        interpretation = IntentEngine.interpret(
            self.user_message,
            self.area,
            actions
        )

        action_name = interpretation.get("action")
        params = interpretation.get("params", {})

        # 3. Cargar handler dinámico
        handler_cls = ActionLoader.get(action_name)

        if not handler_cls:
            return {"status": False, "msg": f"Acción no reconocida: {action_name}"}

        # 4. Crear instancia del handler
        handler = handler_cls(
            jira_service=self.jira_service,
            actions=actions,
            username=self.username
        )

        params["_action"] = action_name

        # 5. Ejecutar acción real
        return handler.execute(params)
