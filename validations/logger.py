import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional

# ============================================================
# 🔹 Configuración de logging para Docker/stdout
# ============================================================

# Crear logger principal
logger = logging.getLogger("LN1_API")
logger.setLevel(logging.INFO)  # Cambiar a INFO para reducir verbosidad

# Evitar handlers duplicados
if not logger.handlers:
    # Handler para stdout (Docker logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Formato detallado con timestamp, nivel y mensaje
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


# ============================================================
# 🔹 Función principal de logging con JSON (solo en caso de error)
# ============================================================
def logErrorJson(
    error_message: str, 
    error_type: str, 
    origin: str = "API_LN1_FASTAPI",
    exception: Optional[Exception] = None,
    extra_data: Optional[dict] = None
):
    """
    Registra ERRORES SOLO en formato JSON en Docker logs.
    Solo se registra cuando hay un error real.
    
    Args:
        error_message: Mensaje del error
        error_type: Tipo de error (ValueError, ConnectionError, etc.)
        origin: Origen del error (nombre del controlador/servicio)
        exception: Objeto de excepción (opcional)
        extra_data: Datos adicionales a registrar (opcional)
    """
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "origin": origin,
            "error_type": error_type,
            "message": error_message,
            "extra_data": extra_data or {}
        }
        
        # Si hay excepción, incluir traceback
        if exception:
            import traceback
            log_entry["exception_traceback"] = traceback.format_exc()
        
        # Registrar como JSON en Docker logs
        logger.error(json.dumps(log_entry, ensure_ascii=False, indent=2))
        
    except Exception as log_err:
        logger.error(f"Error al escribir el log: {log_err}", exc_info=True)


# ============================================================
# 🔹 Funciones auxiliares de logging (línea simple, no JSON)
# ============================================================
def logInfo(message: str, origin: str = "API_LN1_FASTAPI", extra_data: Optional[dict] = None):
    """Registra información general (línea simple)."""
    try:
        data_str = json.dumps(extra_data) if extra_data else ""
        log_msg = f"[{origin}] {message}" + (f" {data_str}" if data_str else "")
        logger.info(log_msg)
    except Exception as e:
        logger.error(f"Error al escribir log INFO: {e}")


def logWarning(message: str, origin: str = "API_LN1_FASTAPI", extra_data: Optional[dict] = None):
    """Registra advertencias (línea simple)."""
    try:
        data_str = json.dumps(extra_data) if extra_data else ""
        log_msg = f"[{origin}] {message}" + (f" {data_str}" if data_str else "")
        logger.warning(log_msg)
    except Exception as e:
        logger.error(f"Error al escribir log WARNING: {e}")


def logSuccess(message: str, origin: str = "API_LN1_FASTAPI", extra_data: Optional[dict] = None):
    """Registra operaciones exitosas (línea simple)."""
    try:
        data_str = json.dumps(extra_data) if extra_data else ""
        log_msg = f"✅ [{origin}] {message}" + (f" {data_str}" if data_str else "")
        logger.info(log_msg)
    except Exception as e:
        logger.error(f"Error al escribir log SUCCESS: {e}")
