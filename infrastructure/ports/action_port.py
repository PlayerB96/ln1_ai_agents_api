"""
Ports (interfaces) para Clean Architecture Hexagonal.
Define los contratos que deben cumplir los adaptadores.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class ActionPort(ABC):
    """
    Puerto/Interface para acciones del sistema.
    Define el contrato que deben cumplir todas las acciones.
    """
    
    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la acción con los parámetros proporcionados.
        
        Args:
            params: Diccionario con los parámetros de la acción
            
        Returns:
            Dict con el resultado de la acción
        """
        pass
