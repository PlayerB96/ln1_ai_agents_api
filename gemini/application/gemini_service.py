import google.generativeai as genai
from fastapi import HTTPException
from configparser import ConfigParser
from gemini.domain.dataModel.model import GeminiRequest


class GeminiService:

    def __init__(self, request: GeminiRequest = None):
        self.request = request

        # Leer config.ini
        config = ConfigParser()
        config.read("config.ini")

        self.api_key = config.get("GEMINI", "api_key", fallback=None)
        if not self.api_key:
            raise HTTPException(status_code=500, detail="API key de Gemini no configurada.")

        # Inicializar cliente oficial
        genai.configure(api_key=self.api_key)

    # ------------------------------------------------------------
    # Construir prompt
    # ------------------------------------------------------------
    def build_prompt(self) -> str:
        return (
            f"{self.request.context}\n\n"
            f"Pregunta: {self.request.question}\n\n"
            f"Respuesta:"
        )

    # ------------------------------------------------------------
    # Generar contenido
    # ------------------------------------------------------------
    def generate(self) -> dict:
        if not self.request:
            raise HTTPException(status_code=400, detail="No se recibió solicitud válida.")

        try:
            model = genai.GenerativeModel(self.request.model)

            response = model.generate_content(
                self.build_prompt(),
                generation_config={
                    "temperature": self.request.temperature,
                }
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error interno en Gemini: {str(e)}")

        # Validar texto
        try:
            text = response.text.strip()

            if not text:
                raise ValueError("Gemini devolvió una respuesta vacía.")

            return {
                "ok": True,
                "model": self.request.model,
                "question": self.request.question,
                "answer": text,
                "raw": response.to_dict(),   # útil para debug
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo procesar la respuesta de Gemini: {e}"
            )

    # ------------------------------------------------------------
    # Listar modelos disponibles
    # ------------------------------------------------------------
    def list_models(self):
        try:
            models = genai.list_models()
            return {"models": [m.name for m in models]}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al obtener modelos: {e}")
