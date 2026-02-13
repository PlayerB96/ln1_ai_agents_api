from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websocket.domain.dataModel.model import WsChatMessageRequest
from websocket.infrastructure.ws_controller import WSChatController
from websocket.infrastructure.ws_security import WSSecurityManager
from websocket.utils.utils import WSCode, build_error_response
 
ws = APIRouter()

@ws.websocket("/ws/chat")
async def ia_agent_ws(websocket: WebSocket):
    """
    Endpoint WebSocket seguro para chat con agente IA.
    
    Requiere parámetros en query params:
        - token: Token de autenticación (obligatorio)
        - code_user: Código del usuario (opcional)
        - fullname: Nombre completo del usuario (opcional)
        - area: Area de operacion (opcional, default: general)
    
    Ejemplo de conexión desde JavaScript:
        const ws = new WebSocket('ws://localhost:8000/ws/chat?token=secret123&code_user=USER001&fullname=Juan%20Perez&area=ventas');
    """
    # IMPORTANTE: Aceptar PRIMERO para hacer el handshake WebSocket
    await websocket.accept()
    
    # 1️⃣ Ahora SI validamos después de aceptar
    user_data = await WSSecurityManager.authenticate_websocket(websocket)
    # Si la autenticación falló, cierra con código 1008
    if not user_data["authenticated"]:
        await websocket.close(code=1008, reason=user_data.get("error", "Autenticación rechazada"))
        return
    
    # ✅ Auth pasó, continúa normally
    code_user = user_data["code_user"]
    fullname = user_data["fullname"]
    area = user_data["area"]

    # Validar que code_user no esté vacío
    if not code_user:
        WSSecurityManager.log_connection("UNKNOWN", "ERROR - code_user vacío o no enviado", websocket)
        await websocket.close(code=1008, reason="code_user es obligatorio")
        return

    WSSecurityManager.log_connection(code_user, f"connect - code_user: {code_user}, fullname: {fullname}", websocket)

    try:
        while True:
            raw_message = await websocket.receive_text()
            # ✅ Creamos el payload Pydantic
            payload = WsChatMessageRequest(
                message=raw_message,
                code_user=code_user,
                fullname=fullname,
                area=area,
            )
            # Enviamos el payload al controlador
            controller = WSChatController(payload=payload)
            result = controller.wsController()

            # Convertir modelo Pydantic a dict para enviar como JSON
            await websocket.send_json(result.model_dump(exclude_none=True))

    except WebSocketDisconnect:
        WSSecurityManager.log_connection(code_user, "disconnect", websocket)
    except Exception as e:
        WSSecurityManager.log_connection(code_user, f"ERROR: {str(e)}", websocket)
        await websocket.send_json(
            build_error_response(
                error="Conexión interrumpida",
                detail=str(e),
                ws_code=WSCode.INTERNAL_ERROR
            ).model_dump(exclude_none=True)
        )
