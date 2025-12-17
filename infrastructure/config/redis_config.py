"""
Configuración centralizada de Redis usando patrón Singleton.
Proporciona una única instancia del cliente Redis para toda la aplicación.
"""
from redis import Redis
from configparser import ConfigParser
from typing import Optional


class RedisConfig:
    """Singleton para gestionar la conexión a Redis"""
    
    _instance: Optional[Redis] = None
    
    @classmethod
    def get_client(cls) -> Redis:
        """
        Obtiene la instancia única del cliente Redis.
        Si no existe, la crea con la configuración de config.ini
        
        Returns:
            Redis: Cliente Redis configurado
        """
        if cls._instance is None:
            config = ConfigParser()
            config.read("config.ini")
            
            cls._instance = Redis(
                host=config.get("REDIS", "host"),
                port=config.getint("REDIS", "port"),
                password=config.get("REDIS", "password"),
                db=config.getint("REDIS", "db"),
                decode_responses=True
            )
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Resetea la instancia (útil para testing)"""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
