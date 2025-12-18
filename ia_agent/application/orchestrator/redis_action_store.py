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
    
    # Caché en memoria por key de Redis (e.g., actions:default, actions:ln1)
    _caches: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def get_all(cls, key: str = "actions") -> Dict[str, Any]:
        """
        Obtiene todas las acciones desde Redis.
        Usa caché en memoria para reducir llamadas a Redis.
        
        Args:
            key: Clave de Redis a consultar (ej: 'actions:ln1', 'actions:shared')
        
        Returns:
            Dict con todas las acciones disponibles
        """
        # Para multi-tenancy, usar caché por key
        if key in cls._caches:
            return cls._caches[key]
        
        try:
            redis_client = RedisConfig.get_client()
            
            # Intentar obtener usando RedisJSON si está disponible
            if hasattr(redis_client, "json"):
                actions = redis_client.json().get(key)
                if actions:
                    cls._caches[key] = actions
                    return actions
            
            # Fallback a string JSON
            raw = redis_client.get(key)
            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                actions = json.loads(raw)
                cls._caches[key] = actions
                return actions
            
            print(f"⚠️ No se encontraron acciones en Redis para key: {key}")
            return {}
            
        except Exception as e:
            print(f"⚠️ Error leyendo acciones desde Redis ({key}): {e}")
            return {}
    
    @classmethod
    def invalidate_cache(cls):
        """Invalida el caché de acciones"""
        cls._caches.clear()
    
    @classmethod
    def get_action(cls, action_name: str, key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Obtiene una acción específica por nombre.
        
        Args:
            action_name: Nombre de la acción
            key: Clave específica de Redis a consultar (e.g., 'actions:default').
                 Si no se provee, intentará buscar primero en 'actions:default' y luego en 'actions'.
            
        Returns:
            Dict con la configuración de la acción o None si no existe
        """
        # Si se especifica una key concreta, buscar solo ahí
        if key:
            actions = cls.get_all(key)
            return actions.get(action_name)

        # Búsqueda por defecto: primero en actions:default, luego en actions
        for k in ("actions:default", "actions"):
            actions = cls.get_all(k)
            if action_name in actions:
                return actions.get(action_name)
        return None
