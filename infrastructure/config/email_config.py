"""
Configuración centralizada de Email usando FastAPI-Mail.
Proporciona una única instancia de configuración de email.
"""
from fastapi_mail import ConnectionConfig
from configparser import ConfigParser
from typing import Optional


class EmailConfig:
    """Singleton para gestionar la configuración de email"""
    
    _config: Optional[ConnectionConfig] = None
    
    @classmethod
    def get_config(cls) -> ConnectionConfig:
        """
        Obtiene la configuración de email.
        Si no existe, la crea desde config.ini
        
        Returns:
            ConnectionConfig: Configuración de FastAPI-Mail
        """
        if cls._config is None:
            config = ConfigParser()
            config.read("config.ini")
            
            cls._config = ConnectionConfig(
                MAIL_USERNAME=config.get("EMAIL", "smtp_user"),
                MAIL_PASSWORD=config.get("EMAIL", "smtp_password"),
                MAIL_FROM=config.get("EMAIL", "smtp_user"),
                MAIL_PORT=config.getint("EMAIL", "smtp_port"),
                MAIL_SERVER=config.get("EMAIL", "smtp_server"),
                MAIL_STARTTLS=config.get("EMAIL", "smtp_secure").lower() == "tls",
                MAIL_SSL_TLS=config.get("EMAIL", "smtp_secure").lower() == "ssl",
                USE_CREDENTIALS=True,
            )
        return cls._config
