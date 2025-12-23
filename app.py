"""
API principal para el sistema de orquestación multi-tenant.
Coordina agentes IA para diferentes áreas de la empresa.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mail import FastMail
from fastapi.responses import JSONResponse
from configparser import ConfigParser
import asyncio

from infrastructure.config.redis_config import RedisConfig
from infrastructure.config.email_config import EmailConfig

# Leer configuración
config = ConfigParser()
config.read("config.ini")

# Configurar email usando módulo centralizado
fm = FastMail(EmailConfig.get_config())

# Inicializar cliente Redis (se crea la instancia singleton)
redis_client = RedisConfig.get_client()

# Configurar FastAPI
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

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware de timeout global
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    """
    Middleware que aplica un timeout global de 240 segundos a todas las peticiones.
    """
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
from ia_agent.domain.ia_agent import ia
from gemini.domain.gemini import gemini
from runner.domain.runner import runner

app.include_router(ia, prefix="/api/v1")
app.include_router(gemini, prefix="/api/v1")
app.include_router(runner, prefix="/api/v1")
