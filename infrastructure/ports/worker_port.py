"""
Puerto para comunicación con Cloudflare Workers.
Define el contrato para adaptadores de workers externos.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class WorkerPort(ABC):
    """
    Puerto/Interface para comunicación con Workers externos.
    """
    
    @abstractmethod
    def call_mutation(self, mutation: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una mutación GraphQL en el worker.
        
        Args:
            mutation: Nombre de la mutación a ejecutar
            variables: Variables para la mutación
            
        Returns:
            Dict con la respuesta del worker
        """
        pass
