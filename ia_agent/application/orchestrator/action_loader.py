"""
Factory para crear instancias de acciones dinámicamente.
Implementa patrón Factory con registro dinámico.
"""
from typing import Dict, Type, Optional, Any
from ia_agent.application.actions.base_action import BaseAction
from ia_agent.application.actions.saludar_actions import SaludarAction
from ia_agent.application.actions.jira_actions import JiraAction


class ActionFactory:
    """
    Factory para crear acciones dinámicamente.
    Permite registro de nuevas acciones sin modificar el código.
    """
    
    _handlers: Dict[str, Type[BaseAction]] = {}
    
    @classmethod
    def register(cls, handler_name: str, handler_class: Type[BaseAction]):
        """
        Registra un handler de acción.
        
        Args:
            handler_name: Nombre del handler (ej: "saludar", "jira")
            handler_class: Clase del handler
        """
        cls._handlers[handler_name] = handler_class
    
    @classmethod
    def create(cls, handler_name: str, **dependencies) -> Optional[BaseAction]:
        """
        Crea una instancia de acción con sus dependencias.
        
        Args:
            handler_name: Nombre del handler a crear
            **dependencies: Dependencias a inyectar en el constructor
            
        Returns:
            Instancia de la acción o None si no existe
        """
        handler_class = cls._handlers.get(handler_name)
        if not handler_class:
            return None
        return handler_class(**dependencies)
    
    @classmethod
    def get_handler_class(cls, handler_name: str) -> Optional[Type[BaseAction]]:
        """
        Obtiene la clase del handler sin instanciarla.
        
        Args:
            handler_name: Nombre del handler
            
        Returns:
            Clase del handler o None si no existe
        """
        return cls._handlers.get(handler_name)


# Registro automático de handlers conocidos
ActionFactory.register("saludar", SaludarAction)
ActionFactory.register("jira", JiraAction)

# Mappings para compatibilidad con estructura actual de Redis
ActionFactory.register("epicas", JiraAction)
ActionFactory.register("sprints", JiraAction)
