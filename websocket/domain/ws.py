from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websocket.infrastructure.ws_controller import WSChatController
from websocket.infrastructure.ws_security import WSSecurityManager

ws = APIRouter()

@ws.websocket("/ws/chat")
async def ia_agent_ws(websocket: WebSocket):
    """
    Endpoint WebSocket seguro para chat con agente IA.
    
    Requiere parámetros en query params:
        - token: Token de autenticación (obligatorio)
        - code_user: Código del usuario (opcional)
        - fullname: Nombre completo del usuario (opcional)
    
    Ejemplo de conexión desde JavaScript:
        const ws = new WebSocket('ws://localhost:8000/ws/chat?token=secret123&code_user=USER001&fullname=Juan%20Perez');
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
    user_id = user_data["user_id"]
    code_user = user_data["code_user"]
    fullname = user_data["fullname"]
    
    print(f"🟢 Usuario {fullname or code_user or user_id[:20]}... conectado al WebSocket")
    WSSecurityManager.log_connection(user_id, f"connect - code_user: {code_user}, fullname: {fullname}")

    try:
        while True:
            # 2️⃣ Recibe TEXTO PLANO desde el frontend
            raw_message = await websocket.receive_text()
            print(f"📩 [{user_id}] Mensaje recibido: {raw_message[:50]}...")

            # 3️⃣ Procesa mediante el controlador (CON seguridad y parámetros del usuario)
            controller = WSChatController(
                message=raw_message,
                user_id=user_id,
                code_user=code_user,
                fullname=fullname
            )
            result = controller.process_request()

            # 4️⃣ Envía respuesta al cliente
            await websocket.send_json(result)

    except WebSocketDisconnect:
        print(f"🔴 Usuario {user_id} desconectado")
        WSSecurityManager.log_connection(user_id, "disconnect")
    except Exception as e:
        print(f"❌ Error en WebSocket [{user_id}]: {str(e)}")
        WSSecurityManager.log_connection(user_id, f"error: {str(e)}")
        await websocket.send_json({
            "error": "Conexión interrumpida",
            "detail": str(e)
        })
