import json
from fastapi import HTTPException
import requests
from gemini.application.gemini_service import GeminiService
from gemini.domain.dataModel.model import GeminiRequest
from sistemas.application.jira_service import JiraService
from .actions.jira_actions import DocumentarAction, SprintsAction

class OrchestratorService:
    ACTION_MAP = {
        "documentar": DocumentarAction,
        "sprints": SprintsAction,
    }

    def __init__(self, user_message: str):
        self.user_message = user_message
        self.jira_service = JiraService(None)  # solo una vez
        self.worker_url = "https://actions-agentia-worker.soporteti-41b.workers.dev/actions"

    def get_actions_from_worker(self):
        try:
            response = requests.get(self.worker_url, timeout=3)
            response.raise_for_status()
            data = response.json()
            return data  # {'documentar': {...}, 'sprints': {...}, ...}
        except Exception as e:
            # fallback a hardcode si el Worker no responde
            print("⚠️ No se pudo obtener acciones del Worker:", e)
            return {
                "documentar": {},
                "sprints": {}
            }

    def process(self):
        actions = self.get_actions_from_worker()
        print("Acciones obtenidas del Worker:", actions)
        # Construir solicitud Gemini
        gemini_req = GeminiRequest(
            question=f"Analiza este mensaje: {self.user_message}",
            context=(
                "Eres un agente de orquestación para un área de sistemas en una empresa retail. "
                "Tu tarea es identificar la intención del usuario en base a su mensaje. "
                "Debes responder SOLO en formato JSON con esta estructura exacta: "
                "{\"action\": \"<acción>\", \"params\": {...}} "
                f"Acciones válidas: {json.dumps(actions)} "
                "No uses texto adicional, ni markdown, ni comentarios."
            ),
            model="gemini-2.5-flash",
            temperature=0.2,
        )

        gemini_agent = GeminiService(gemini_req)
        interpretation = gemini_agent.generate()
        cleaned = interpretation.get("answer", "").replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(cleaned)
            action = data.get("action")
            params = data.get("params", {})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"No se pudo interpretar la respuesta de Gemini: {e}")

        handler_cls = self.ACTION_MAP.get(action)
        if not handler_cls:
            return {"status": False, "msg": f"No se reconoce la acción '{action}'."}

        handler = handler_cls(jira_service=self.jira_service)
        return handler.execute(params)
