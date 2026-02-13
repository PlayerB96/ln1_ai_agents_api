from collections import defaultdict
from datetime import datetime, timedelta

from pydantic_core import ValidationError
from websocket.domain.dataModel.model import WSSuccessResponse, WsChatMessage, WsChatMessageRequest
from websocket.infrastructure.ws_security import WSSecurityManager
from websocket.utils.utils import WSCode, build_error_response, build_success_response


class WsChatAplicationResponse:
    MAX_MESSAGES_PER_MINUTE = 10
    user_message_history = defaultdict(list)
    
    def __init__(self, payload: WsChatMessageRequest):
        self.message = payload.message
        self.code_user = payload.code_user
        self.fullname = payload.fullname
        self.canal = "ws"
        self.area = payload.area

    def validate_message(self) -> WsChatMessage:
        return WsChatMessage(message=self.message)
    
    def check_rate_limit(self) -> bool:
        if not self.code_user:
            return False  # ahora no se permite sin code_user
            
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        self.user_message_history[self.code_user] = [
            msg_time for msg_time in self.user_message_history[self.code_user]
            if msg_time > one_minute_ago
        ]
        
        if len(self.user_message_history[self.code_user]) >= self.MAX_MESSAGES_PER_MINUTE:
            return False
        
        self.user_message_history[self.code_user].append(now)
        return True
    
    def sanitize_message(self) -> str:
        sanitized = self.message.strip()
        max_length = 250
        if len(sanitized) > max_length:
            raise ValueError(
                f"Tu mensaje es demasiado largo (máximo {max_length} caracteres, escribiste {len(sanitized)}). Intenta de nuevo con un mensaje más corto."
            )
        return sanitized
    

    def process_request(self) -> WSSuccessResponse:
        """
        Procesa el mensaje y retorna siempre un dict estandarizado
        con los campos:
            - success: True/False
            - ws_code: Código WebSocket (opcional para errores)
            - message: mensaje normal
            - error / detail: para errores
        """
        try:
            # 1️⃣ Rate limit
            if not self.check_rate_limit():
                WSSecurityManager.log_connection(
                    self.code_user or "UNKNOWN",
                    "ERROR - Rate limit excedido"
                )
                return build_error_response(
                    error="Rate limit excedido",
                    detail="Demasiados mensajes. Intenta después de 1 minuto",
                    ws_code=WSCode.POLICY_VIOLATION
                )
            
            # 2️⃣ Sanitización
            self.message = self.sanitize_message()
            
            # 3️⃣ Validación
            chat_message = self.validate_message()
            
            # 4️⃣ Respuesta exitosa
            return build_success_response(
                message=chat_message.message,
                code_user=self.code_user,
                fullname=self.fullname,
                canal=self.canal,
                area=self.area,
                ws_code=WSCode.NORMAL
            )
        
        except ValueError as e:
            WSSecurityManager.log_connection(
                self.code_user or "UNKNOWN",
                f"ERROR - Mensaje demasiado largo: {str(e)}"
            )
            return build_error_response(
                error="Mensaje demasiado largo",
                detail=str(e),
                ws_code=WSCode.POLICY_VIOLATION
            )
        except ValidationError as e:
            WSSecurityManager.log_connection(
                self.code_user or "UNKNOWN",
                f"ERROR - Mensaje inválido: {e.errors()}"
            )
            return build_error_response(
                error="Mensaje inválido",
                ws_code=WSCode.POLICY_VIOLATION,
                details=e.errors()  # Se agrega como campo extra
            )
        except Exception as e:
            WSSecurityManager.log_connection(
                self.code_user or "UNKNOWN",
                f"ERROR - Error interno: {str(e)}"
            )
            return build_error_response(
                error="Error interno",
                detail=str(e),
                ws_code=WSCode.INTERNAL_ERROR
            )
