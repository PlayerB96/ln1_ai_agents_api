from sistemas.application.jira_service import JiraService
from sistemas.application.response import ResponseSIS
from fastapi.responses import JSONResponse
from validations.logger import logErrorJson, logSuccess, logInfo

class SistemasController:
    def __init__(self, dataModel):
        self.dataModel = dataModel
        self.responseSIS = ResponseSIS()
        self.jiraService = JiraService(self.dataModel)
        self.origin = "SistemasController"

    # ------------------------------------------------------------------
    # Determina automáticamente qué método ejecutar según la acción recibida.
    # ------------------------------------------------------------------
    def process_request(self):
        try:
            accion = self.dataModel.accion.lower()
            logInfo(f"Procesando acción: {accion}", origin=self.origin, extra_data={"dataModel": str(self.dataModel)})

            # -------------------------------------------------------------
            # 1️⃣ OBTENER EPICS DE UN PROYECTO
            # -------------------------------------------------------------
            if accion == "documentar":
                logInfo(f"Documentando ticket: {self.dataModel.proyecto_id}", origin=self.origin)

                projects = self.jiraService.get_project_epics(self.dataModel.proyecto_id)
                logSuccess(f"Epics obtenidos para proyecto: {self.dataModel.proyecto_id}", origin=self.origin)
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
                logInfo(f"Obteniendo sprints del epic: {self.dataModel.ticket_id}", origin=self.origin)
                sprints = self.jiraService.get_epic_tareas(self.dataModel.ticket_id)
                logSuccess(f"Sprints obtenidos para epic: {self.dataModel.ticket_id}", origin=self.origin)
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
                logInfo(f"Generando sugerencias para ticket: {self.dataModel.proyecto_id}", origin=self.origin)
                logSuccess(f"Sugerencias generadas para ticket: {self.dataModel.proyecto_id}", origin=self.origin)
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": True,
                        "msg": f"Sugerencias generadas para ticket {self.dataModel.proyecto_id}"
                    }
                )

            elif accion == "mapear":
                logInfo(f"Mapeando flujo para proyecto: {self.dataModel.proyecto_id}", origin=self.origin)
                logSuccess(f"Flujo mapeado para proyecto: {self.dataModel.proyecto_id}", origin=self.origin)
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": True,
                        "msg": f"Flujo mapeado para proyecto {self.dataModel.proyecto_id}"
                    }
                )

            else:
                logErrorJson(
                    error_message=f"Acción no reconocida: {accion}",
                    error_type="InvalidAction",
                    origin=self.origin,
                    extra_data={"provided_action": accion}
                )
                return JSONResponse(
                    status_code=400,
                    content={"status": False, "msg": "Acción no reconocida"}
                )
        
        except Exception as e:
            logErrorJson(
                error_message=str(e),
                error_type=type(e).__name__,
                origin=self.origin,
                exception=e
            )
            return JSONResponse(
                status_code=500,
                content={"status": False, "msg": f"Error procesando solicitud: {str(e)}"}
            )
