"""
Motor de interpretación de intenciones usando Gemini.
Procesa mensajes de usuario y determina la acción a ejecutar.
"""
import json
from typing import Dict, Any
from fastapi import HTTPException
from gemini.application.gemini_service import GeminiService
from gemini.domain.dataModel.model import GeminiRequest
from ia_agent.application.promps.prompt_store import PromptStore


class IntentEngine:
    """Motor de interpretación de intenciones del usuario"""
    
    @staticmethod
    def interpret(user_message: str, area: str, actions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interpreta la intención del usuario usando Gemini.
        
        Args:
            user_message: Mensaje del usuario
            area: Área del agente (sistemas, rrhh, etc.)
            actions: Diccionario de acciones disponibles
            
        Returns:
            Dict con la acción interpretada y sus parámetros
        """
        try:
            # Obtener template de prompt desde Redis
            template = PromptStore.get_prompt("intent_rules_prompt")
            
            # Renderizar template con datos reales
            context = template.format(
                area=area,
                actions=json.dumps(actions, indent=2, ensure_ascii=False)
            )
            
            import time
        
            # Llamar a Gemini para interpretar la intención
            gemini_req = GeminiRequest(
                question=f"Analiza este mensaje: {user_message}",
                context=context,
                model="gemini-2.5-flash-lite", 
                temperature=0.2,
            )
            
            gemini = GeminiService(gemini_req)
            
            # Implementar retry básico para errores 503 (Sobrecarga)
            max_retries = 3
            response = None # Initialize response
            for attempt in range(max_retries):
                try:
                    response = gemini.generate()
                    break # Si tiene éxito, salir del loop
                except HTTPException as e:
                    # Si es error 503 (Service Unavailable / Overloaded) y no es el último intento
                    if e.status_code == 503 and attempt < max_retries - 1:
                        wait_time = 2 * (attempt + 1) # Backoff simple: 2s, 4s
                        print(f"⚠️ Gemini sobrecargado (503). Reintentando en {wait_time}s... (Intento {attempt+1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise e # Re-lanzar error si no es 503 o es el último intento
            
            # Si después de los reintentos no hubo respuesta, lanzar un error
            if response is None:
                raise HTTPException(
                    status_code=500,
                    detail="Gemini did not respond after multiple retries."
                )

            # Limpiar respuesta (remover markdown si existe)
            cleaned = (
                response.get("answer", "")
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
            )
            
            # Parsear JSON
            try:
                result = json.loads(cleaned)
                
                # Validar estructura de respuesta
                if not isinstance(result, dict) or "action" not in result:
                    print(f"⚠️ Respuesta inválida de Gemini: {cleaned}")
                    return {"action": "none", "params": {}}
                
                # Asegurar que params existe
                if "params" not in result:
                    result["params"] = {}
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Error parseando JSON de Gemini: {e}")
                print(f"Respuesta recibida: {cleaned}")
                return {"action": "none", "params": {}}
                
        except HTTPException as e:
            # Capturar errores HTTP de Gemini y propagarlos con más detalle
            print(f"❌ HTTPException en IntentEngine: {e.status_code} - {e.detail}")
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Error en IntentEngine: {e.detail}"
            )
        except Exception as e:
            # Capturar cualquier otro error
            print(f"❌ Error inesperado en IntentEngine: {type(e).__name__} - {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error inesperado en IntentEngine: {str(e)}"
            )
