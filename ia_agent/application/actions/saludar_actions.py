import requests
from ia_agent.application.actions.base_action import BaseAction

class SaludarAction(BaseAction):
    desc = "Genera un saludo cálido y amigable, mencionando las acciones disponibles para el usuario."

    def __init__(self, jira_service=None, actions=None, username=None):
        super().__init__()
        self.jira_service = jira_service
        self.actions = actions or {}   # acciones dinámicas desde KV
        self.username = username or "Usuario"
        # URL de tu Worker GraphQL
        self.worker_url = "https://my-graphql-worker.soporteti-41b.workers.dev/"

    def execute(self, params=None):
        """
        Genera un saludo llamando al Worker GraphQL.
        params se puede usar si quieres pasar datos adicionales, pero no es obligatorio.
        """

        # -----------------------------
        # 1️⃣ Preparar la query GraphQL
        # -----------------------------
        query = """
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

        payload = {
            "query": query,
            "variables": variables
        }

        # -----------------------------
        # 2️⃣ Hacer request al Worker
        # -----------------------------
        try:
            response = requests.post(
                self.worker_url,
                json=payload,
                timeout=30  # timeout de 30 segundos
            )
            response.raise_for_status()
        except requests.RequestException as e:
            # Si falla la conexión con el Worker
            return self.format_response(
                data={"opciones": list(self.actions.keys())},
                msg=f"No se pudo conectar al Worker: {e}"
            )

        # -----------------------------
        # 3️⃣ Procesar respuesta
        # -----------------------------
        try:
            result = response.json()
            data = result.get("data", {}).get("generarSaludo", {})
            if not data.get("status"):
                # Si el Worker devolvió error
                return self.format_response(
                    data={"opciones": list(self.actions.keys())},
                    msg=data.get("msg", "Error desconocido al generar saludo")
                )

            # -----------------------------
            # 4️⃣ Retornar saludo formateado
            # -----------------------------
            return self.format_response(
                data=data.get("data", {"opciones": list(self.actions.keys())}),
                msg=data.get("msg", "")
            )

        except Exception as e:
            return self.format_response(
                data={"opciones": list(self.actions.keys())},
                msg=f"Error procesando respuesta del Worker: {e}"
            )
