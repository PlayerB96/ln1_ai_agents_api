"""
Acción para operaciones con Jira.
Maneja múltiples operaciones de Jira de forma dinámica.
"""
from typing import Dict, Any, Optional
from ia_agent.application.actions.base_action import BaseAction
from sistemas.application.jira_service import JiraService
from infrastructure.adapters.cloudflare_worker_adapter import CloudflareWorkerAdapter


class JiraAction(BaseAction):
    """
    Action multiuso para operaciones con Jira: epicas, sprints, subtareas, tareas, etc.
    Funciona leyendo dinámicamente la acción y parámetros desde Redis.
    """
    
    def __init__(
        self, 
        jira_service: JiraService, 
        username: Optional[str] = None, 
        actions: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Inicializa la acción de Jira.
        
        Args:
            jira_service: Servicio de Jira para operaciones
            username: Nombre del usuario
            actions: Diccionario de acciones disponibles
            **kwargs: Argumentos adicionales (ignorados)
        """
        super().__init__()
        self.jira_service = jira_service
        self.username = username or "Usuario"
        self.actions = actions or {}
        self.worker = CloudflareWorkerAdapter()
        
        # Mapa dinámico acción → método JIRA
        self.ACTION_METHODS = {
            "epicas": {
                "param": "proyecto_id",
                "method": self.jira_service.get_project_epics
            },
            "sprints": {
                "param": "epic_id",
                "method": self.jira_service.get_epic_tareas
            }
        }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una operación de Jira.
        
        Args:
            params: Parámetros de la acción
            
        Returns:
            Dict con el resultado de la operación
        """
        action_name = params.get("_action")
        if not action_name:
            return self.format_response(
                data={}, 
                status=False,
                msg="No se recibió acción a ejecutar"
            )
        
        # Validar que la acción existe
        if action_name not in self.ACTION_METHODS:
            return self.format_response(
                data={},
                status=False,
                msg=f"La acción '{action_name}' no está definida en JiraAction"
            )
        
        config = self.ACTION_METHODS[action_name]
        param_name = config["param"]
        method = config["method"]
        
        # Validar parámetro
        if param_name not in params or not params[param_name]:
            return self.format_response(
                data={},
                status=False,
                msg=f"Falta el parámetro requerido '{param_name}' para la acción '{action_name}'"
            )
        
        param_value = params[param_name]
        
        # Ejecutar acción real en Jira
        try:
            result_data = method(param_value)
        except Exception as e:
            return self.format_response(
                data={}, 
                status=False,
                msg=f"Error obteniendo datos de Jira: {e}"
            )
        
        # Llamar al Worker GraphQL
        mutation = """
        mutation GenerarResumenProyecto($actions: JSON!, $username: String!, $proyectos: JSON!) {
          generarResumenProyecto(actions: $actions, username: $username, proyectos: $proyectos) {
            status
            msg
            data
            executed_at
          }
        }
        """
        
        variables = {
            "username": self.username,
            "actions": self.actions,
            "proyectos": result_data
        }
        
        try:
            result = self.worker.call_mutation(mutation, variables)
            
            # Verificar si hubo error
            if isinstance(result, dict) and not result.get("status", True):
                return self.format_response(
                    data=result_data,
                    status=False,
                    msg=result.get("msg", "Error conectando al Worker")
                )
            
            worker_data = result.get("generarResumenProyecto", {})
            
            return self.format_response(
                data=worker_data.get("data", result_data),
                status=worker_data.get("status", True),
                msg=worker_data.get("msg", f"Resultado de acción '{action_name}'")
            )
            
        except Exception as e:
            return self.format_response(
                data=result_data, 
                status=False,
                msg=f"Error conectando al Worker: {e}"
            )
