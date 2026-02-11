"""
Utilidad para generar tokens JWT para testing del WebSocket.
"""
from datetime import datetime, timedelta
from jose import jwt
import configparser
from pathlib import Path

# Lee configuración desde config.ini
config = configparser.ConfigParser()
config_path = Path(__file__).parent.parent.parent / "config.ini"
config.read(config_path)

SECRET_KEY = config.get("WS", "secret", fallback="your-secret-key-here-change-in-production")
ALGORITHM = config.get("WS", "algorithm", fallback="HS256")


def create_test_token(user_id: str, email: str = None, expires_in_hours: int = 24) -> str:
    """
    Crea un token JWT para testing.
    
    Args:
        user_id: ID del usuario (ej: "user123")
        email: Email del usuario (opcional)
        expires_in_hours: Horas hasta que expire el token
        
    Returns:
        str: Token JWT
    """
    expire = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    payload = {
        "sub": user_id,  # subject (user_id)
        "email": email or f"{user_id}@example.com",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


if __name__ == "__main__":
    # Genera un token para testing
    test_token = create_test_token("user123", "user123@example.com")
    print(f"🔑 Token JWT generado:\n{test_token}\n")
    print(f"📌 URL para WebSocket:\nws://localhost:8000/ws/chat?token={test_token}")
