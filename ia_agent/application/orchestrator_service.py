import json
from fastapi import HTTPException
from gemini.application.gemini_service import GeminiService
from gemini.domain.dataModel.model import GeminiRequest
from sistemas.application.jira_service import JiraService
from ia_agent.application.actions.saludar_actions import SaludarAction
from .actions.jira_actions import JiraAction
from app import redis_client


class OrchestratorService:

    def __init__(self, user_message: str, area: str, username: str):
        self.user_message = user_message
        self.area = area
        self.username = username
        self.jira_service = JiraService(None)

    # -----------------------------
    # Obtener acciones desde Redis
    # -----------------------------
    def get_actions_from_redis(self) -> dict:
        try:
            # RedisJSON
            if hasattr(redis_client, "json"):
                actions = redis_client.json().get("actions")
                if actions:
                    return actions

            # String JSON
            actions_json = redis_client.get("actions")
            if actions_json:
                if isinstance(actions_json, bytes):
                    actions_json = actions_json.decode("utf-8")
                return json.loads(actions_json)

            print("⚠️ No se encontraron acciones en Redis.")
            return {}

        except Exception as e:
            print("⚠️ Error leyendo acciones desde Redis:", e)
            return {}

    # -----------------------------
    # Cargar clase dinámica
    # -----------------------------
    def load_action_class(self, action_name: str):
        actions = self.get_actions_from_redis()
        info = actions.get(action_name)

        if not info:
            return None

        class_name = info.get("class")
        if not class_name:
            return None

        # buscar en el namespace actual
        return globals().get(class_name)

    # -----------------------------
    # Procesar mensaje
    # -----------------------------
    def process(self):
        actions = self.get_actions_from_redis()

        gemini_req = GeminiRequest(
            question=f"Analiza este mensaje: {self.user_message}",
            context=(
                f"Eres un agente técnico del área {self.area}. "
                "Tu tarea es interpretar la intención del usuario usando SOLO "
                "las acciones siguientes:\n\n"
                f"{json.dumps(actions, indent=2)}\n\n"

                "REGLAS:\n"
                "1. Detectar saludo → devolver exactamente:\n"
                "{\"action\": \"saludar\", \"params\": {}}\n\n"
                "2. Identificar acción según 'description'. No inventar acciones.\n"
                "3. Leer parámetros desde 'parameters.properties'.\n"
                "4. Para requeridos: si no vienen → string vacío.\n"
                "5. Si no hay match → devolver:\n"
                "{\"action\": \"none\", \"params\": {}}\n\n"

                "IMPORTANTE:\n"
                "- SOLO devolver JSON válido sin texto extra."
            ),
            model="gemini-2.5-flash",
            temperature=0.2,
        )

        gemini_agent = GeminiService(gemini_req)
        interpretation = gemini_agent.generate()

        cleaned = (
            interpretation.get("answer", "")
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        try:
            data = json.loads(cleaned)
            action = data.get("action")
            params = data.get("params", {})
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo interpretar la respuesta de Gemini: {e}"
            )

        # cargar clase dinámica
        handler_cls = self.load_action_class(action)

        if not handler_cls:
            return {"status": False, "msg": f"No se reconoce la acción '{action}'."}

        # instanciar handler
        handler = handler_cls(
            jira_service=self.jira_service,
            actions=actions,
            username=self.username
        )
        params["_action"] = action  
        return handler.execute(params)
