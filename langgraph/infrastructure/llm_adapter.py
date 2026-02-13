import configparser
import google.generativeai as genai
import json
from langgraph.infrastructure.tools import LangGraphTools

# Leer config.ini
config = configparser.ConfigParser()
config.read("config.ini")

GEMINI_API_KEY = config.get("GEMINI", "api_key")

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)


class GeminiLLMAdapter:
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        self.model = genai.GenerativeModel(model_name)
        self.tools = LangGraphTools()

    def generate_text(self, prompt: str) -> dict:
        """
        Genera texto y retorna respuesta con metadata (tokens, confianza, etc)
        
        Returns:
            Dict con:
            - text: El texto generado
            - tokens: Dict con información de tokens
            - finish_reason: Razón de finalización
        """
        response = self.model.generate_content(prompt)
        
        # Extraer información de tokens
        tokens_info = {}
        if hasattr(response, 'usage_metadata'):
            tokens_info = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            }
        
        # Extraer razón de finalización (indicador de confianza)
        finish_reason = "FINISH_REASON_UNSPECIFIED"
        if hasattr(response, 'candidates') and response.candidates:
            finish_reason = response.candidates[0].finish_reason
        
        return {
            "text": response.text,
            "tokens": tokens_info,
            "finish_reason": finish_reason
        }
    
    def generate_text_with_tools(self, prompt: str, include_actions: bool = True) -> dict:
        """
        Genera texto con herramientas disponibles y contexto de acciones
        
        Args:
            prompt: El prompt del usuario
            include_actions: Si incluir las acciones disponibles en el contexto
        
        Returns:
            Dict con respuesta y acciones utilizadas
        """
        # Obtener acciones disponibles si se requieren
        actions_context = ""
        if include_actions:
            actions_result = self.tools.get_agent_actions()
            # print(prompt)
            print("Acciones obtenidas para el LLM:", json.dumps(actions_result, indent=2, ensure_ascii=False))
            if actions_result["success"]:
                actions_context = f"\n\nAcciones disponibles:\n{json.dumps(actions_result['actions'], indent=2)}"
        
        # Crear prompt mejorado con contexto
        enhanced_prompt = f"{prompt}{actions_context}"
        
        try:
            response = self.model.generate_content(enhanced_prompt)
            return {
                "success": True,
                "response": response.text,
                "actions_used": []  # Aquí puedes parsear qué acciones usó
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": None
            }
