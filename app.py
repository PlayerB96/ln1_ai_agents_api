from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel
import asyncio
from fastapi.responses import JSONResponse
from configparser import ConfigParser
import redis 

# Leer config.ini
config = ConfigParser()
config.read("config.ini")

conf = ConnectionConfig(
    MAIL_USERNAME=config.get("EMAIL", "smtp_user"),
    MAIL_PASSWORD=config.get("EMAIL", "smtp_password"),
    MAIL_FROM=config.get("EMAIL", "smtp_user"),
    MAIL_PORT=config.getint("EMAIL", "smtp_port"),
    MAIL_SERVER=config.get("EMAIL", "smtp_server"),
    MAIL_STARTTLS=config.get("EMAIL", "smtp_secure").lower() == "tls",
    MAIL_SSL_TLS=config.get("EMAIL", "smtp_secure").lower() == "ssl",
    USE_CREDENTIALS=True,
)

fm = FastMail(conf)


# -------------------------
# Configuración Redis
# -------------------------
REDIS_HOST = config.get("REDIS", "host")
REDIS_PORT = config.getint("REDIS", "port")
REDIS_PASSWORD = config.get("REDIS", "password")
REDIS_DB = config.getint("REDIS", "db")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=REDIS_DB,
    decode_responses=True  # devuelve strings en lugar de bytes
)



# =========================
# FastAPI principal
# =========================
app = FastAPI(
    title=config.get("APP", "title", fallback="API LN1 - AI Agents"),
    description=config.get("APP", "description", fallback="""
        Bienvenido a la documentación de **API LN1**.  
        Este servicio Web sirve como plataforma central para todos los agentes de IA
        de la empresa, cada agente atendiendo diferentes áreas de soporte.
    """),
    version=config.get("APP", "version", fallback="1.0.0"),
    contact={
        "name": config.get("EMAIL", "contact_name", fallback="Soporte Intranet LN1"),
        "email": config.get("EMAIL", "contact_email", fallback="soporte@example.com"),
        "url": config.get("EMAIL", "contact_url", fallback="https://intranet.grupolanumero1.com.pe/"),
    },
)


# Middleware CORS para permitir acceso desde cualquier dominio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware para manejar timeout global (240s)
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=240.0)
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=408,
            content={
                "status": False,
                "data": None,
                "message": "Tiempo de espera agotado, intente de nuevo o en otro horario",
            },
        )


# Incluir routers
from sistemas.domain.sistemas import sistemas
from gemini.domain.gemini import gemini
from ia_agent.domain.ia_agent import ia

app.include_router(sistemas, prefix="/api/v1")
app.include_router(gemini, prefix="/api/v1")
app.include_router(ia, prefix="/api/v1")
