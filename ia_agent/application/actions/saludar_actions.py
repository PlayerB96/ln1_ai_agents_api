"""
Acción de saludo inicial al usuario.
Genera un saludo personalizado usando Cloudflare Worker.
"""
from typing import Dict, Any, Optional
from ia_agent.application.actions.base_action import BaseAction
from infrastructure.adapters.cloudflare_worker_adapter import CloudflareWorkerAdapter


class SaludarAction(BaseAction):
    """
    Acción que genera un saludo cálido y amigable,
    mencionando las acciones disponibles para el usuario.
    """
    
    def __init__(
        self, 
        actions: Optional[Dict[str, Any]] = None, 
        username: Optional[str] = None,
        **kwargs
    ):
        """
        Inicializa la acción de saludo.
        
        Args:
            actions: Diccionario de acciones disponibles
            username: Nombre del usuario
            **kwargs: Argumentos adicionales (ignorados)
        """
        super().__init__()
        self.actions = actions or {}
        self.username = username or "Usuario"
        self.worker = CloudflareWorkerAdapter()
    
    def execute(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Genera un saludo llamando al Worker GraphQL.
        
        Args:
            params: Parámetros adicionales (opcional)
            
        Returns:
            Dict con el saludo generado
        """
        # Preparar la mutación GraphQL
        mutation = """
        mutation GenerarSaludo($actions: JSON!, $username: String!) {
          generarSaludo(actions: $actions, username: $username) {
            status
            msg
            data
            executed_at
          }
        }
        """
        
        variables = {
            "username": self.username,
            "actions": self.actions
        }
        
        # Llamar al worker
        try:
            result = self.worker.call_mutation(mutation, variables)
            
            # Verificar si hubo error en la llamada
            if isinstance(result, dict) and not result.get("status", True):
                return self.format_response(
                    data={"opciones": list(self.actions.keys())},
                    status=False,
                    msg=result.get("msg", "Error al generar saludo")
                )
            
            # Extraer datos de la respuesta GraphQL
            data = result.get("generarSaludo", {})
            
            if not data.get("status"):
                return self.format_response(
                    data={"opciones": list(self.actions.keys())},
                    status=False,
                    msg=data.get("msg", "Error desconocido al generar saludo")
                )
            
            # Retornar saludo formateado
            return self.format_response(
                data=data.get("data", {"opciones": list(self.actions.keys())}),
                status=True,
                msg=data.get("msg", "")
            )
            
        except Exception as e:
            return self.format_response(
                data={"opciones": list(self.actions.keys())},
                status=False,
                msg=f"Error inesperado: {str(e)}"
            )
