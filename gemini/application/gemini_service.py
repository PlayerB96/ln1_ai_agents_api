import google.generativeai as genai
from fastapi import HTTPException
from configparser import ConfigParser
from gemini.domain.dataModel.model import GeminiRequest


class GeminiService:

    MODEL_LITE = "gemini-2.5-flash-lite"
    MODEL_FULL = "gemini-2.5-flash"
    TOKEN_THRESHOLD = 4000  # Umbral de tokens para cambiar a modelo full

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
                    "max_output_tokens": 512, 
                }
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error interno en Gemini: {str(e)}")

        # Validar texto
        try:
            text = response.text.strip()
            usage = response.usage_metadata
            print(f"📊 Uso de tokens: {usage.total_token_count} (modelo: {self.request.model})")
            
            if not text:
                raise ValueError("Gemini devolvió una respuesta vacía.")

            # Devolver datos sin tomar decisiones de retry
            # La lógica de cambio de modelo está en IntentEngine
            return {
                "ok": True,
                "model": self.request.model,
                "question": self.request.question,
                "answer": text,
                "usage": {
                    "total_tokens": usage.total_token_count,
                    "prompt_tokens": usage.prompt_token_count,
                    "candidates_tokens": usage.candidates_token_count
                },
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
