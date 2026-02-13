import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def get_ws_audit_logger():
    logger = logging.getLogger("ws_audit")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # Permite todos los niveles (DEBUG, INFO, ERROR, etc.)

    # ✅ Crear carpeta logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "ws_audit.log"

    handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
