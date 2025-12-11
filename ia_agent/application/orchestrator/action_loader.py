from ia_agent.application.actions.saludar_actions import SaludarAction
from ia_agent.application.actions.jira_actions import JiraAction

class ActionLoader:

    @staticmethod
    def get(action_name: str):
        mapping = {
            "saludar": SaludarAction,
            "epicas": JiraAction,
            "none": None
        }

        return mapping.get(action_name)
