import json
from gemini.application.gemini_service import GeminiService
from gemini.domain.dataModel.model import GeminiRequest
from ia_agent.application.promps.prompt_store import PromptStore


class IntentEngine:

    @staticmethod
    def interpret(user_message: str, area: str, actions: dict) -> dict:

        # 1. Obtener prompt base desde redis
        template = PromptStore.get_prompt("intent_rules_prompt")
        print("Template obtenido:", template)
        # 2. Renderizarlo con datos reales
        context = template.format(
            area=area,
            actions=json.dumps(actions, indent=2)
        )

        # 3. Llamada normal a Gemini
        gemini_req = GeminiRequest(
            question=f"Analiza este mensaje: {user_message}",
            context=context,
            model="gemini-2.5-flash",
            temperature=0.2,
        )

        gemini = GeminiService(gemini_req)
        response = gemini.generate()

        cleaned = (
            response.get("answer", "")
                .replace("```json", "")
                .replace("```", "")
                .strip()
        )

        try:
            return json.loads(cleaned)
        except Exception:
            return {"action": "none", "params": {}}
