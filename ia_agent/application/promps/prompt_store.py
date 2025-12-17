"""
Repository para gestionar prompts almacenados en Redis.
Implementa caché en memoria para reducir llamadas a Redis.
"""
from typing import Dict, Optional
from infrastructure.config.redis_config import RedisConfig


class PromptStore:
    """
    Repository para prompts en Redis.
    Implementa caché en memoria para mejorar performance.
    """
    
    _cache: Dict[str, str] = {}
    
    @classmethod
    def get_prompt(cls, key: str) -> str:
        """
        Obtiene un prompt desde Redis.
        Usa caché en memoria para reducir llamadas.
        
        Args:
            key: Clave del prompt en Redis
            
        Returns:
            str: Contenido del prompt
            
        Raises:
            Exception: Si el prompt no existe en Redis
        """
        # Retornar desde caché si existe
        if key in cls._cache:
            return cls._cache[key]
        
        redis_client = RedisConfig.get_client()
        raw = redis_client.get(key)
        
        if not raw:
            raise Exception(f"Prompt '{key}' no encontrado en Redis")
        
        # Guardar en caché
        cls._cache[key] = raw
        return raw
    
    @classmethod
    def invalidate_cache(cls, key: Optional[str] = None):
        """
        Invalida el caché de prompts.
        
        Args:
            key: Clave específica a invalidar. Si es None, invalida todo el caché.
        """
        if key:
            cls._cache.pop(key, None)
        else:
            cls._cache.clear()
