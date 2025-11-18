from ia_agent.application.actions.email_actions import BaseAction
from sistemas.application.jira_service import JiraService
from fastapi import HTTPException

class DocumentarAction(BaseAction):
    required_params = ["proyecto_id"]

    def __init__(self, jira_service: JiraService):
        self.jira_service = jira_service

    def execute(self, params: dict):
        # Validación de parámetros
        for param in self.required_params:
            if param not in params:
                raise HTTPException(status_code=400, detail=f"Falta parámetro '{param}'")

        proyecto_id = params["proyecto_id"]
        projects = self.jira_service.get_project_epics(proyecto_id)
        return {
            "status": True,
            "msg": f"Documentando proyect_id: {proyecto_id}",
            "projects": projects
        }


class SprintsAction(BaseAction):
    required_params = ["ticket_id"]

    def __init__(self, jira_service: JiraService):
        self.jira_service = jira_service

    def execute(self, params: dict):
        # Validación de parámetros
        for param in self.required_params:
            if param not in params:
                raise HTTPException(status_code=400, detail=f"Falta parámetro '{param}'")

        epic_id = params["ticket_id"]
        sprints = self.jira_service.get_epic_tareas(epic_id)
        return {
            "status": True,
            "msg": f"Sprints asociados al epic {epic_id}",
            "data": sprints.get("data", {})
        }
