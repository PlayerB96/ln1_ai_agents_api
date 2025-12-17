"""
Repository para gestionar acciones almacenadas en Redis.
Implementa caché en memoria para reducir llamadas a Redis.
"""
import json
from typing import Dict, Any, Optional
from infrastructure.config.redis_config import RedisConfig


class RedisActionStore:
    """
    Repository para acciones en Redis.
    Implementa patrón Repository con caché en memoria.
    """
    
    _cache: Optional[Dict[str, Any]] = None
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """
        Obtiene todas las acciones desde Redis.
        Usa caché en memoria para reducir llamadas a Redis.
        
        Returns:
            Dict con todas las acciones disponibles
        """
        # Retornar caché si existe
        if cls._cache is not None:
            return cls._cache
        
        try:
            redis_client = RedisConfig.get_client()
            
            # Intentar obtener usando RedisJSON si está disponible
            if hasattr(redis_client, "json"):
                actions = redis_client.json().get("actions")
                if actions:
                    cls._cache = actions
                    return actions
            
            # Fallback a string JSON
            raw = redis_client.get("actions")
            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                actions = json.loads(raw)
                cls._cache = actions
                return actions
            
            print("⚠️ No se encontraron acciones en Redis.")
            return {}
            
        except Exception as e:
            print(f"⚠️ Error leyendo acciones desde Redis: {e}")
            return {}
    
    @classmethod
    def invalidate_cache(cls):
        """Invalida el caché de acciones"""
        cls._cache = None
    
    @classmethod
    def get_action(cls, action_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una acción específica por nombre.
        
        Args:
            action_name: Nombre de la acción
            
        Returns:
            Dict con la configuración de la acción o None si no existe
        """
        actions = cls.get_all()
        return actions.get(action_name)
