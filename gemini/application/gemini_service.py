import requests
from fastapi import HTTPException
from configparser import ConfigParser
from gemini.domain.dataModel.model import GeminiRequest


class GeminiService:
    def __init__(self, request: GeminiRequest = None):
        self.request = request

        config = ConfigParser()
        config.read("config.ini")

        self.api_key = config.get("GEMINI", "api_key", fallback=None)
        if not self.api_key:
            raise HTTPException(status_code=500, detail="API key de Gemini no configurada.")

        self.headers = {"Content-Type": "application/json"}

    def build_prompt(self) -> str:
        return f"{self.request.context}\n\nPregunta: {self.request.question}\n\nRespuesta:"


    def generate(self) -> dict:
        if not self.request:
            raise HTTPException(status_code=400, detail="No se recibió solicitud válida para generar contenido.")

        url = (
            f"https://generativelanguage.googleapis.com/v1/models/"
            f"{self.request.model}:generateContent?key={self.api_key}"
        )

        payload = {
            "contents": [{"parts": [{"text": self.build_prompt()}]}],
            "generationConfig": {"temperature": self.request.temperature},
        }

        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="Tiempo de espera agotado al conectar con Gemini.")
        except requests.exceptions.ConnectionError:
            raise HTTPException(status_code=503, detail="No se pudo conectar con la API de Gemini.")
        except requests.exceptions.HTTPError:
            status = resp.status_code
            try:
                error_data = resp.json().get("error", {})
                msg = error_data.get("message", resp.text)
            except Exception:
                msg = resp.text
            if status == 503 or error_data.get("status") == "UNAVAILABLE":
                raise HTTPException(status_code=503, detail=f"El modelo de Gemini está saturado: {msg}")
            else:
                raise HTTPException(status_code=status, detail=f"Error en Gemini: {msg}")

        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Error inesperado al conectar con Gemini: {e}")

        # Validar la respuesta
        try:
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No se encontraron candidatos en la respuesta de Gemini.")
            text = candidates[0]["content"]["parts"][0].get("text", "").strip()
            if not text:
                raise ValueError("Gemini devolvió una respuesta vacía.")

            return {"ok": True, "model": self.request.model, "question": self.request.question, "answer": text, "raw": data}

        except (ValueError, KeyError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo procesar la respuesta de Gemini: {e}. Respuesta cruda: {resp.text}"
            )


    def list_models(self):
        url = f"https://generativelanguage.googleapis.com/v1/models?key={self.api_key}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Error al obtener modelos: {e}")
        return resp.json()
