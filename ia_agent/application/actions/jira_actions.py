import requests
from ia_agent.application.actions.base_action import BaseAction
from sistemas.application.jira_service import JiraService

class DocumentarAction(BaseAction):
    required_params = ["proyecto_id"]
    desc = "Listar todas las épicas de un proyecto con mensaje amigable generado por GraphQL Worker"

    def __init__(self, jira_service: JiraService, username=None, actions=None):
        super().__init__()
        self.jira_service = jira_service
        self.username = username or "Usuario"
        self.actions = actions or {}
        # URL de tu Worker GraphQL
        self.worker_url = "https://my-graphql-worker.soporteti-41b.workers.dev/"

    def execute(self, params: dict):
        # -----------------------------
        # 1️⃣ Validar parámetros
        # -----------------------------
        print("Validando parámetros para ... , params:", params)
        self.validate_params(params)
        proyecto_id = params["proyecto_id"]

        # -----------------------------
        # 2️⃣ Obtener datos reales desde JIRA
        # -----------------------------
        projects = self.jira_service.get_project_epics(proyecto_id)

        # -----------------------------
        # 3️⃣ Preparar query GraphQL para el Worker (nueva mutation)
        # -----------------------------
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
            "proyectos": projects  # enviamos los datos de JIRA al Worker
        }

        payload = {
            "query": query,
            "variables": variables
        }

        # -----------------------------
        # 4️⃣ Consumir Worker GraphQL
        # -----------------------------
        try:
            response = requests.post(self.worker_url, json=payload, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            return self.format_response(
                data={"projects": projects},
                msg=f"No se pudo conectar al Worker: {e}"
            )

        # -----------------------------
        # 5️⃣ Procesar respuesta del Worker
        # -----------------------------
        try:
            result = response.json()
            worker_data = result.get("data", {}).get("generarResumenProyecto", {})

            if not worker_data.get("status"):
                return self.format_response(
                    data={"projects": projects},
                    msg=worker_data.get("msg", "Error desconocido al generar mensaje amigable")
                )

            # -----------------------------
            # 6️⃣ Retornar datos + mensaje amigable
            # -----------------------------
            return self.format_response(
                data=worker_data.get("data", {"projects": projects}),
                msg=worker_data.get("msg", f"Documentando proyecto_id: {proyecto_id}")
            )

        except Exception as e:
            return self.format_response(
                data={"projects": projects},
                msg=f"Error procesando respuesta del Worker: {e}"
            )
