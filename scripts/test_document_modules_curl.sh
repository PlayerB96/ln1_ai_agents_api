#!/bin/bash

# ============================================================================
# EJEMPLOS DE CURL PARA PROBAR LA ACCIÓN document_modules
# ============================================================================
# Ejecuta estos comandos en una terminal después de iniciar el servidor
# ============================================================================

# PASOS PREVIOS:
# 1. Terminal 1: Iniciar servidor
#    cd /Users/bryanrafaelandia/Documents/Projects/agenteia_suite/ln1_ai_agents_api
#    uvicorn app:app --reload

# 2. Terminal 2: Ejecutar uno de los ejemplos de abajo

# ============================================================================
# EJEMPLO 1: Documentar proyecto básico
# ============================================================================

echo "=== EJEMPLO 1: Proyecto básico ==="
curl -X POST http://localhost:8000/ia/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Documenta los módulos del proyecto LN1SCRUM",
    "area": "global",
    "username": "Bryan Rafael",
    "company": "ln1",
    "tags": ["documentación", "proyecto"]
  }'

# ============================================================================
# EJEMPLO 2: Con formato específico
# ============================================================================

echo -e "\n=== EJEMPLO 2: Con formato markdown ==="
curl -X POST http://localhost:8000/ia/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Genera documentación en markdown de la estructura del proyecto agenteia_suite",
    "area": "global",
    "username": "Developer",
    "company": "ln1",
    "tags": ["documentación", "markdown"]
  }'

# ============================================================================
# EJEMPLO 3: Con tecnologías especificadas
# ============================================================================

echo -e "\n=== EJEMPLO 3: Con lenguajes y frameworks ==="
curl -X POST http://localhost:8000/ia/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Documenta el proyecto con Python, FastAPI, PostgreSQL y Redis",
    "area": "global",
    "username": "Tech Lead",
    "company": "ln1",
    "tags": ["documentación", "tecnologías"]
  }'

# ============================================================================
# EJEMPLO 4: Con módulos específicos
# ============================================================================

echo -e "\n=== EJEMPLO 4: Con módulos específicos ==="
curl -X POST http://localhost:8000/ia/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Documenta los módulos ia_agent, gemini y runner del proyecto",
    "area": "global",
    "username": "Architect",
    "company": "ln1",
    "tags": ["documentación", "módulos"]
  }'

# ============================================================================
# EJEMPLO 5: Documentación completa
# ============================================================================

echo -e "\n=== EJEMPLO 5: Documentación completa ==="
curl -X POST http://localhost:8000/ia/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quiero documentar completamente el proyecto agenteia_suite. Incluye módulos ia_agent, gemini, runner, sistemas. Tecnologías: Python, FastAPI, Google Gemini, Jira Cloud. Formato PDF.",
    "area": "global",
    "username": "Project Manager",
    "company": "ln1",
    "tags": ["documentación", "completo", "pdf"]
  }'

# ============================================================================
# EJEMPLO 6: Con repositorio
# ============================================================================

echo -e "\n=== EJEMPLO 6: Con URL de repositorio ==="
curl -X POST http://localhost:8000/ia/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Documenta el proyecto desde https://github.com/agenteia/ln1_ai_agents_api.git",
    "area": "global",
    "username": "DevOps",
    "company": "ln1",
    "tags": ["documentación", "repositorio"]
  }'

# ============================================================================
# EJEMPLO 7: Simple
# ============================================================================

echo -e "\n=== EJEMPLO 7: Simple ==="
curl -X POST http://localhost:8000/ia/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quiero documentar mi proyecto",
    "area": "global"
  }'

# ============================================================================
# EJEMPLO 8: Con APIs externas
# ============================================================================

echo -e "\n=== EJEMPLO 8: Con APIs externas ==="
curl -X POST http://localhost:8000/ia/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Documenta nuestro proyecto que usa Google Gemini, Jira Cloud y Cloudflare API",
    "area": "global",
    "username": "Integration Engineer",
    "company": "ln1",
    "tags": ["documentación", "apis"]
  }'

# ============================================================================
# RESPUESTA ESPERADA
# ============================================================================

# {
#   "status": true,
#   "msg": "Acción document_modules iniciada para 'LN1SCRUM'",
#   "data": {
#     "task_id": "uuid-aqui",
#     "trace_id": "uuid-aqui",
#     "status": "queued",
#     "message": "Documentación de 'LN1SCRUM' encolada para procesamiento",
#     "format": "markdown",
#     "output_location": "./docs/ln1scrum",
#     "estimated_time": "2-5 minutos"
#   }
# }

# ============================================================================
# VALIDACIÓN
# ============================================================================

echo -e "\n\n=== VALIDAR CONFIGURACIÓN ==="
python scripts/validate_document_modules.py

# ============================================================================
# HACER ESTO DESPUÉS:
# ============================================================================

# 1. Guardar el task_id y trace_id del response
# 2. Monitorear logs del servidor
# 3. Consultar el estado del task (si hay endpoint)
# 4. Verificar output en ./docs/

