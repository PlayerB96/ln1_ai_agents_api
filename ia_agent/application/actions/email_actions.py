# ia_agent/application/actions/base_action.py
from abc import ABC, abstractmethod
from fastapi import HTTPException

class BaseAction(ABC):
    """
    Clase base abstracta para cualquier acción que el Orchestrator pueda ejecutar.
    """
    @abstractmethod
    def execute(self, params: dict):
        """
        Ejecuta la acción con los parámetros proporcionados.
        Debe retornar un diccionario con resultado.
        """
        pass
