from sistemas.application.jira_service import JiraService
from sistemas.application.response import ResponseSIS
from fastapi.responses import JSONResponse

class SistemasController:
    def __init__(self, dataModel):
        self.dataModel = dataModel
        self.responseSIS = ResponseSIS()
        self.jiraService = JiraService(self.dataModel)

    # ------------------------------------------------------------------
    # Determina automáticamente qué método ejecutar según la acción recibida.
    # ------------------------------------------------------------------
    def process_request(self):
        accion = self.dataModel.accion.lower()
        print(self.dataModel)

        # -------------------------------------------------------------
        # 1️⃣ OBTENER EPICS DE UN PROYECTO
        # -------------------------------------------------------------
        if accion == "documentar":
            print(self.dataModel.proyecto_id)
            print("Documentando ticket en Jira...")

            projects = self.jiraService.get_project_epics(self.dataModel.proyecto_id)
            return JSONResponse(
                status_code=200,
                content={
                    "status": True,
                    "msg": f"Documentando ticket {self.dataModel.proyecto_id}",
                    "projects": projects
                }
            )

        # -------------------------------------------------------------
        # 2️⃣ OBTENER SPRINTS DE UN EPIC
        # -------------------------------------------------------------
        elif accion == "sprints":
            sprints = self.jiraService.get_epic_tareas(self.dataModel.ticket_id)
            return JSONResponse(
                status_code=200,
                content={
                    "status": True,
                    "msg": f"Sprints asociados al epic {self.dataModel.ticket_id}",
                    "data": sprints.get("data", {})
                }
            )


        # -------------------------------------------------------------
        # 3️⃣ OTRAS ACCIONES
        # -------------------------------------------------------------
        elif accion == "sugerir":
            return JSONResponse(
                status_code=200,
                content={
                    "status": True,
                    "msg": f"Sugerencias generadas para ticket {self.dataModel.proyecto_id}"
                }
            )

        elif accion == "mapear":
            return JSONResponse(
                status_code=200,
                content={
                    "status": True,
                    "msg": f"Flujo mapeado para proyecto {self.dataModel.proyecto_id}"
                }
            )

        else:
            return JSONResponse(
                status_code=400,
                content={"status": False, "msg": "Acción no reconocida"}
            )
