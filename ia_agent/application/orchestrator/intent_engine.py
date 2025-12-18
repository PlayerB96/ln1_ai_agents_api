"""
Motor de interpretación de intenciones usando Gemini.
Procesa mensajes de usuario y determina la acción a ejecutar.
"""
import json
import re
from typing import Dict, Any
from fastapi import HTTPException
from gemini.application.gemini_service import GeminiService
from gemini.domain.dataModel.model import GeminiRequest
from ia_agent.application.promps.prompt_store import PromptStore


class IntentEngine:
    """Motor de interpretación de intenciones del usuario"""
    
    MODEL_LITE = "gemini-2.5-flash-lite"
    MODEL_FULL = "gemini-2.5-flash"
    TOKEN_THRESHOLD = 4000  # Umbral de tokens para cambiar a modelo full
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        text = (text or "").lower()
        return re.sub(r"[^a-z0-9áéíóúñü\s]", " ", text)

    @staticmethod
    def _tokenize(text: str) -> set:
        return {t for t in IntentEngine._normalize_text(text).split() if t}

    @staticmethod
    def _score_action(name: str, cfg: Dict[str, Any], query_tokens: set) -> float:
        parts = [name, cfg.get("description", "")]
        tags = cfg.get("tags", []) or cfg.get("keywords", []) or []
        if isinstance(tags, list):
            parts.extend(tags)
        elif isinstance(tags, str):
            parts.append(tags)
        text = " ".join(map(str, parts))
        tokens = IntentEngine._tokenize(text)   
        if not tokens or not query_tokens:
            return 0.0
        overlap = len(tokens & query_tokens)
        score = overlap / (len(query_tokens) or 1)
        if name in tokens:
            score += 0.2
        if cfg.get("type") == "composite":
            score += 0.1
        return score

    @staticmethod
    def _condense_action_schema(name: str, cfg: Dict[str, Any], all_actions: Dict[str, Any]) -> Dict[str, Any]:
        schema = cfg.get("parameters", {}) or {}
        required = schema.get("required", []) or []
        brief = {
            "description": cfg.get("description", ""),
            "type": cfg.get("type", "atomic"),
            "required": required,
        }
        if cfg.get("tags"):
            brief["tags"] = cfg.get("tags")
        if cfg.get("type") == "composite":
            steps = []
            for step in cfg.get("steps", []) or []:
                child = all_actions.get(step.get("action", ""), {})
                child_required = (child.get("parameters", {}) or {}).get("required", []) or []
                steps.append({
                    "id": step.get("id"),
                    "action": step.get("action"),
                    "required": child_required
                })
            brief["steps"] = steps
        return brief

    @staticmethod
    def _shortlist_actions(user_message: str, area: str, actions: Dict[str, Any], top_k: int = 8) -> Dict[str, Any]:
        def area_ok(cfg: Dict[str, Any]) -> bool:
            a = cfg.get("area")
            return (a is None) or (a == "global") or (str(a).lower() == str(area).lower())

        filtered = {k: v for k, v in actions.items() if area_ok(v)}

        qtokens = IntentEngine._tokenize(user_message)
        scored = []
        for name, cfg in filtered.items():
            score = IntentEngine._score_action(name, cfg, qtokens)
            scored.append((score, name, cfg))

        scored.sort(key=lambda x: x[0], reverse=True)
        shortlisted = scored[:max(3, top_k)]

        condensed: Dict[str, Any] = {}
        for _, name, cfg in shortlisted:
            condensed[name] = IntentEngine._condense_action_schema(name, cfg, actions)

        return condensed if condensed else {
            name: IntentEngine._condense_action_schema(name, cfg, actions)
            for name, cfg in list(actions.items())[:min(5, len(actions))]
        }

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
            
            # Pre-filtrado y condensación de acciones para reducir tokens
            slim_actions = IntentEngine._shortlist_actions(user_message, area, actions, top_k=8)

            # Renderizar template con datos reales usando acciones condensadas
            context = template.format(
                area=area,
                actions=json.dumps(slim_actions, indent=2, ensure_ascii=False)
            )
            
            import time
            # print(context)
            
            # Siempre empezar con modelo LITE para optimizar costos
            model = IntentEngine.MODEL_LITE
            print(f"🚀 Iniciando con modelo: {model}")
            
            # Llamar a Gemini para interpretar la intención
            gemini_req = GeminiRequest(
                question=user_message,
                context=context,
                model=model,
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
            
            # Verificar uso de tokens y retry con FULL si es necesario
            total_tokens = response.get("usage", {}).get("total_tokens", 0)
            current_model = response.get("model", model)
            
            print(f"📊 Tokens usados: {total_tokens} con modelo {current_model}")
            
            # Si usamos LITE y los tokens superan el umbral, retry con FULL
            if current_model == IntentEngine.MODEL_LITE and total_tokens > IntentEngine.TOKEN_THRESHOLD:
                print(f"⚡ Tokens altos ({total_tokens} > {IntentEngine.TOKEN_THRESHOLD}), reintentando con {IntentEngine.MODEL_FULL}...")
                gemini_req.model = IntentEngine.MODEL_FULL
                gemini = GeminiService(gemini_req)
                response = gemini.generate()
                print(f"✅ Retry completado con {IntentEngine.MODEL_FULL}")

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
                
                print(f"✅ Interpretación exitosa: action='{result.get('action')}', params={result.get('params')}")
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
