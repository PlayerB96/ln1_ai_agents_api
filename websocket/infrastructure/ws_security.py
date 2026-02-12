"""
Utilidades de seguridad para WebSocket.
Maneja autenticación con Bearer tokens simples.
"""
from fastapi import WebSocket
import configparser
from datetime import datetime
from pathlib import Path

from websocket.infrastructure.logging.ws_audit_logger import get_ws_audit_logger

# Lee configuración desde config.ini
config = configparser.ConfigParser()
config_path = Path(__file__).parent.parent.parent / "config.ini"
config.read(config_path)

# Obtiene el secret desde config.ini
SECRET_TOKEN = config.get("WS", "secret", fallback="secret123")


class WSSecurityManager:
    """Gestiona seguridad en conexiones WebSocket con Bearer tokens"""
    
    @staticmethod
    def extract_params_from_query(websocket: WebSocket) -> dict:
        """
        Extrae parámetros de los query parameters.
        
        Args:
            websocket: Conexión WebSocket
            
        Returns:
            dict: Parámetros extraídos (token, code_user, fullname, area)
        """
        token = websocket.query_params.get("token")
        if not token:
            raise ValueError("Token no proporcionado. Usa: ?token=TU_TOKEN")
        
        return {
            "token": token.strip(),
            "code_user": websocket.query_params.get("code_user", "").strip(),
            "fullname": websocket.query_params.get("fullname", "").strip(),
            "area": websocket.query_params.get("area", "general").strip() or "general"
        }
    
    @staticmethod
    def verify_token(token: str) -> bool:
        """
        Verifica si el token es válido comparándolo con el secret de config.ini.
        
        Args:
            token: Token a validar
            
        Returns:
            bool: True si es válido, False en caso contrario
        """
        # Valida que el token coincida con el secret configurado
        return token == SECRET_TOKEN
    
    @staticmethod
    async def authenticate_websocket(websocket: WebSocket) -> dict:
        """
        Autentica una conexión WebSocket con Bearer token y parámetros.
        
        Args:
            websocket: Conexión WebSocket
            
        Returns:
            dict: Datos del usuario autenticado
        """
        try:
            params = WSSecurityManager.extract_params_from_query(websocket)
            token = params["token"]
    
            
            # Valida el token
            if not WSSecurityManager.verify_token(token):
                print(f"   ❌ TOKEN INVÁLIDO")
                return {
                    "authenticated": False,
                    "error": "Token inválido"
                }
            
            print(f"   ✅ TOKEN VÁLIDO - Aceptando conexión")
            # Retorna datos del usuario con todos los parámetros
            return {
                "code_user": params["code_user"],
                "fullname": params["fullname"],
                "area": params["area"],
                "authenticated": True
            }
        except ValueError as e:
            print(f"   ❌ ERROR EN PARÁMETROS: {e}")
            return {
                "authenticated": False,
                "error": str(e)
            }
    
    @staticmethod
    def log_connection(
        code_user: str,
        action: str,
        websocket=None,
        detail: str = None
    ):
        data = {
            "code_user": code_user,
            "action": action,
            "detail": detail,
        }

        if websocket:
            data.update({
                "ip": websocket.client.host,
                "user_agent": websocket.headers.get("user-agent")
            })

        # Usa nivel ERROR si la acción contiene "ERROR"
        logger = get_ws_audit_logger()
        if "ERROR" in action.upper():
            logger.error(data)
        else:
            logger.info(data)
