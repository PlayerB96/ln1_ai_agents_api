import json
from fastapi import HTTPException
import requests
from gemini.application.gemini_service import GeminiService
from gemini.domain.dataModel.model import GeminiRequest
from ia_agent.application.actions.saludar_actions import SaludarAction
from sistemas.application.jira_service import JiraService
from .actions.jira_actions import DocumentarAction
from app import redis_client

class OrchestratorService:
    ACTION_MAP = {
        "saludar": SaludarAction,
        "documentar": DocumentarAction,
    }

    def __init__(self, user_message: str, area: str, username: str ):
        self.user_message = user_message
        self.area = area
        self.username = username
        self.jira_service = JiraService(None)  # solo una vez

    # -----------------------------
    # 2️⃣ Obtener acciones desde Redis
    # -----------------------------
    def get_actions_from_redis(self) -> dict:
        """
        Lee las acciones almacenadas en Redis y devuelve un diccionario.
        Compatible con RedisJSON o string JSON. 
        Fallback a hardcode si algo falla.
        """
        try:
            # Primero intentar RedisJSON
            if hasattr(redis_client, "json"):  # RedisJSON disponible
                actions = redis_client.json().get("actions")
                if actions:
                    return actions

            # Si no hay RedisJSON o la clave es string
            actions_json = redis_client.get("actions")
            if actions_json:
                if isinstance(actions_json, bytes):
                    actions_json = actions_json.decode("utf-8")
                return json.loads(actions_json)

            # fallback hardcode si no existe la clave
            print("⚠️ No se encontraron acciones en Redis, usando hardcode")
            return {
                "saludar": {"description": "Saludo inicial al usuario"},
                "documentar": {"description": "Listar épicas de proyecto"},
                "sprints": {"description": "Listar sprints de epic"}
            }

        except Exception as e:
            print("⚠️ Error leyendo acciones desde Redis:", e)
            return {
                "saludar": {"description": "Saludo inicial al usuario"},
                "documentar": {"description": "Listar épicas de proyecto"},
                "sprints": {"description": "Listar sprints de epic"}
            }

            
            
    def process(self):
        actions = self.get_actions_from_redis()
        print("Acciones obtenidas de Redis:", actions)
        # Construir solicitud Gemini
        gemini_req = GeminiRequest(
            question=f"Analiza este mensaje: {self.user_message}",
            context=(
                f"Eres un agente del área de {self.area} en una empresa Retail. "
                "Tu objetivo es identificar si el usuario en su mensaje solicita una acción técnica "
                "como 'documentar', 'sprints', etc., O si el usuario simplemente está saludando.\n\n"

                "Acciones válidas disponibles para esta área (no incluyas saludar):\n"
                f"{json.dumps(actions)}\n\n"

                "Instrucciones de clasificación:\n"
                "1. Si el mensaje contiene saludos como 'hola', 'buenas', 'qué tal', 'hey', 'buenos días', "
                "'buenas tardes', 'hola bot', 'hola asistente', o variantes, "
                "entonces devuelve EXACTAMENTE:\n"
                "{\"action\": \"saludar\", \"params\": {}}\n\n"

                "2. Si el mensaje requiere una acción válida, responde SOLO:\n"
                "{\"action\": \"<acción>\", \"params\": {...}}\n\n"

                "3. Si el mensaje no coincide con ninguna acción, devuelve:\n"
                "{\"action\": \"none\", \"params\": {}}\n\n"
 
                "No uses texto adicional ni markdown."
            ),

            model="gemini-2.5-flash",
            temperature=0.2,
        )

        # print("Gemini Request:", gemini_req)
        gemini_agent = GeminiService(gemini_req)
        interpretation = gemini_agent.generate()
        cleaned = interpretation.get("answer", "").replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(cleaned)
            action = data.get("action")
            params = data.get("params", {})
            print(f"Acción interpretada: {action}, params: {params}")
            # ✅ Validación adicional para la acción 'documentar'
            if action == "documentar" and "proyecto_id" not in params:
                raise HTTPException(status_code=400, detail="Se requiere 'proyecto_id' para la acción documentar")

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"No se pudo interpretar la respuesta de Gemini: {e}")

        handler_cls = self.ACTION_MAP.get(action)
        if not handler_cls:
            return {"status": False, "msg": f"No se reconoce la acción '{action}'."}

        handler = handler_cls(
            jira_service=self.jira_service,
            actions=actions,
            username=self.username
        )

        print(f"Ejecutando handler: {handler} con params: {params}")
        return handler.execute(params)
