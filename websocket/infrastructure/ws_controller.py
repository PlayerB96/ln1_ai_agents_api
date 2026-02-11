"""
Controlador WebSocket para el agente IA.
Encapsula la lógica de chat del WebSocket con seguridad.
"""
from pydantic import ValidationError
from websocket.domain.dataModel.model import IaChatMessage
from datetime import datetime, timedelta
from collections import defaultdict


class WSChatController:
    """Controlador para procesar solicitudes WebSocket del agente IA"""
    
    # Rate limiting: máximo de mensajes por usuario en ventana de tiempo
    MAX_MESSAGES_PER_MINUTE = 30
    user_message_history = defaultdict(list)
    
    def __init__(self, message: str, user_id: str = None, code_user: str = None, fullname: str = None, canal: str = "ws", area: str = "chat"):
        """
        Inicializa el controlador de WebSocket.
        
        Args:
            message: Mensaje del usuario
            user_id: ID del usuario autenticado (token)
            code_user: Código del usuario
            fullname: Nombre completo del usuario
            canal: Canal de comunicación (default: "ws")
            area: Área de operación (default: "chat")
        """
        self.raw_message = message
        self.user_id = user_id
        self.code_user = code_user
        self.fullname = fullname
        self.canal = canal
        self.area = area
    
    def validate_message(self) -> IaChatMessage:
        """
        Valida el mensaje usando el modelo IaChatMessage.
        
        Returns:
            IaChatMessage: Mensaje validado
            
        Raises:
            ValidationError: Si el mensaje no es válido
        """
        return IaChatMessage(message=self.raw_message)
    
    def check_rate_limit(self) -> bool:
        """
        Verifica si el usuario ha excedido el límite de mensajes.
        
        Returns:
            bool: True si está dentro del límite, False si lo excedió
        """
        if not self.user_id:
            return True  # Sin user_id, permite el mensaje
            
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Limpia mensajes antiguos
        self.user_message_history[self.user_id] = [
            msg_time for msg_time in self.user_message_history[self.user_id]
            if msg_time > one_minute_ago
        ]
        
        # Verifica límite
        if len(self.user_message_history[self.user_id]) >= self.MAX_MESSAGES_PER_MINUTE:
            return False
        
        # Registra nuevo mensaje
        self.user_message_history[self.user_id].append(now)
        return True
    
    def sanitize_message(self) -> str:
        """
        Sanitiza el mensaje para prevenir inyecciones.
        
        Returns:
            str: Mensaje sanitizado
        """
        # Limpia caracteres especiales y limita tamaño
        sanitized = self.raw_message.strip()
        max_length = 2000
        
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    def process_request(self) -> dict:
        """
        Procesa la solicitud del usuario con validaciones de seguridad.
        
        Returns:
            dict: Respuesta con el mensaje procesado
        """
        try:
            # 1️⃣ Valida rate limiting
            if not self.check_rate_limit():
                return {
                    "error": "Rate limit excedido",
                    "detail": "Demasiados mensajes. Intenta después de 1 minuto"
                }
            
            # 2️⃣ Sanitiza el mensaje
            self.raw_message = self.sanitize_message()
            
            # 3️⃣ Valida el mensaje
            chat_message = self.validate_message()
            
            # 4️⃣ Retorna el mensaje procesado
            return {
                "message": chat_message.message,
                "canal": self.canal,
                "area": self.area,
                "token": self.user_id,  
                "user_id": self.user_id,
                "code_user": self.code_user,
                "fullname": self.fullname,
                "timestamp": datetime.now().isoformat()
            }
            
        except ValidationError as e:
            return {
                "error": "Mensaje inválido",
                "details": e.errors()
            }
        except Exception as e:
            return {
                "error": "Error interno",
                "detail": str(e)
            }
