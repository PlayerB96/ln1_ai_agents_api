import requests
from sistemas.domain.dataModel.model import JiraRequest
from configparser import ConfigParser
from requests.auth import HTTPBasicAuth

# ------------------------------------------------------
#  Capa de aplicación que orquesta el flujo del agente Jira.
# ------------------------------------------------------ 
class JiraService:

    def __init__(self, request: JiraRequest):
        self.request = request

        # Cargar config.ini
        config = ConfigParser()
        config.read("config.ini")

        self.base_url = config.get("JIRA", "base_url")  # ej: https://tuempresa.atlassian.net
        self.user = config.get("JIRA", "user")
        self.api_token = config.get("JIRA", "api_token")
        self.auth = HTTPBasicAuth(self.user, self.api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_project_epics(self, project_key: str):
        """
        Obtiene todas las epics de un proyecto usando la API moderna de Jira (2024+).
        """
        url = f"{self.base_url}/rest/api/3/search/jql"
        jql_query = f'project = "{project_key}" AND issuetype = Epic AND statusCategory != Done ORDER BY created DESC'

        payload = {
            "jql": jql_query,
            "fields": ["summary", "issuetype", "status", "created", "updated"],
            "maxResults": 50
        }

        try:
            response = requests.post(url, auth=self.auth, json=payload)
            if response.status_code == 200:
                data = response.json()
                epics = [
                    {
                        "key": issue["key"],
                        "summary": issue["fields"]["summary"],
                        "status": issue["fields"]["status"]["name"]
                    }
                    for issue in data.get("issues", [])
                ]
                return {"count": len(epics), "epics": epics}
            else:
                return {"error": response.status_code, "msg": response.text}
        except Exception as e:
            return {"error": 500, "msg": str(e)}


    def get_epic_tareas(self, epic_key: str):
        """
        Obtiene todas las tareas hijas de un Epic específico (Jira Cloud moderno),
        incluyendo información del sprint si está disponible.
        Usar el campo 'customfield_10020' en lugar de 'sprint'.
        """
        url = f"{self.base_url}/rest/api/3/search/jql"
        jql_query = f'parent = "{epic_key}" ORDER BY created DESC'

        payload = {
            "jql": jql_query,
            "fields": ["summary", "status", "issuetype", "customfield_10020"],
            "maxResults": 100
        }

        try:
            response = requests.post(url, auth=self.auth, json=payload)
            if response.status_code == 200:
                data = response.json()
                issues = data.get("issues", [])
                tareas = []

                for issue in issues:
                    fields = issue.get("fields", {})
                    sprint_field = fields.get("customfield_10020")

                    # El campo puede contener una lista de sprints, tomamos el último si existe
                    sprint_info = sprint_field[-1] if isinstance(sprint_field, list) and sprint_field else None

                    tareas.append({
                        "issue_key": issue.get("key"),
                        "issue_summary": fields.get("summary"),
                        "status": fields.get("status", {}).get("name"),
                        "issue_type": fields.get("issuetype", {}).get("name"),
                        "sprint_name": sprint_info.get("name") if sprint_info else None,
                        "sprint_state": sprint_info.get("state") if sprint_info else None,
                        "sprint_start": sprint_info.get("startDate") if sprint_info else None,
                        "sprint_end": sprint_info.get("endDate") if sprint_info else None,
                    })

                return {
                    "status": True,
                    "msg": f"Tareas asociadas al Epic {epic_key}",
                    "data": {
                        "count": len(tareas),
                        "tareas": tareas
                    }
                }
            else:
                return {"status": False, "msg": response.text}
        except Exception as e:
            return {"status": False, "msg": str(e)}



