"""
WebSocket Response Builder - Utilidad para construir respuestas estandarizadas
usando modelos Pydantic. Garantiza consistencia y validación automática.
"""
from typing import Optional, Dict, Any

from websocket.domain.dataModel.model import WSErrorResponse, WSSuccessResponse


def build_success_response(
    message: str,
    code_user: str,
    fullname: Optional[str] = None,
    canal: str = "ws",
    area: str = "general",
    ws_code: int = 1000,
    **extra_fields
) -> WSSuccessResponse:
    """
    Construye una respuesta exitosa estandarizada para WebSocket usando WSSuccessResponse.
    """
    response = WSSuccessResponse(
        message=message,
        code_user=code_user,
        fullname=fullname,
        canal=canal,
        area=area,
        ws_code=ws_code,
        extra=extra_fields or None
    )
    return response


def build_error_response(
    error: str,
    detail: Optional[str] = None,
    ws_code: int = 1008,
    **extra_fields
) -> WSErrorResponse:
    """
    Construye una respuesta de error estandarizada para WebSocket usando WSErrorResponse.
    """
    response = WSErrorResponse(
        error=error,
        detail=detail,
        ws_code=ws_code,
        extra=extra_fields or None
    )
    return response


# Códigos WebSocket comunes como constantes
class WSCode:
    """Códigos WebSocket estándar para respuestas"""
    NORMAL = 1000            # Operación exitosa
    POLICY_VIOLATION = 1008  # Violación de política (validación, auth, etc.)
    INTERNAL_ERROR = 1011    # Error interno del servidor
