import requests
from ia_agent.application.actions.base_action import BaseAction
from sistemas.application.jira_service import JiraService

class JiraAction(BaseAction):
    """
    Action multiuso: epicas, sprints, subtareas, tareas, etc.
    Funciona leyendo dinámicamente la acción y parámetros.
    """

    def __init__(self, jira_service: JiraService, username=None, actions=None):
        super().__init__()
        self.jira_service = jira_service
        self.username = username or "Usuario"
        self.actions = actions or {}
        self.worker_url = "https://my-graphql-worker.soporteti-41b.workers.dev/"

        # Mapa dinámico acción → método JIRA
        self.ACTION_METHODS = {
            "epicas": {
                "param": "proyecto_id",
                "method": self.jira_service.get_project_epics
            },
            # "sprints": {
            #     "param": "epic_id",
            #     "method": self.jira_service.get_epic_sprints
            # },
            # "subtareas": {
            #     "param": "issue_id",
            #     "method": self.jira_service.get_issue_subtasks
            # }
        }

    def execute(self, params: dict):
        action_name = params.get("_action")  # viene desde el orchestrator
        if not action_name:
            return self.format_response(data={}, msg="No se recibió acción a ejecutar")

        # 1️⃣ Validar que la acción existe
        if action_name not in self.ACTION_METHODS:
            return self.format_response(
                data={},
                msg=f"La acción '{action_name}' no está definida en JiraAction"
            )

        config = self.ACTION_METHODS[action_name]
        param_name = config["param"]
        method = config["method"]

        # 2️⃣ Validar parámetro
        if param_name not in params or not params[param_name]:
            return self.format_response(
                data={},
                msg=f"Falta el parámetro requerido '{param_name}' para la acción '{action_name}'"
            )

        param_value = params[param_name]

        # 3️⃣ Ejecutar acción real en Jira
        try:
            result_data = method(param_value)
        except Exception as e:
            return self.format_response(data={}, msg=f"Error obteniendo datos de Jira: {e}")

        # 4️⃣ Llamar al Worker GraphQL
        query = """
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
            response = requests.post(self.worker_url, json={"query": query, "variables": variables}, timeout=30)
            response.raise_for_status()
            worker_data = response.json().get("data", {}).get("generarResumenProyecto", {})

            return self.format_response(
                data=worker_data.get("data", result_data),
                msg=worker_data.get("msg", f"Resultado de acción '{action_name}'")
            )

        except Exception as e:
            return self.format_response(data=result_data, msg=f"Error conectando al Worker: {e}")
