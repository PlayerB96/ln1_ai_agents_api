"""
Acción para documentar módulos y estructura de proyectos de software.
Coordina con servicio externo para generar documentación automatizada.
"""
import json
import uuid
import requests
from typing import Dict, Any, Optional
from ia_agent.application.actions.base_action import BaseAction


class DocumentModulesAction(BaseAction):
    """
    Acción que documenta los módulos y estructura de un proyecto.
    
    Funcionalidades:
    - Genera documentación de módulos
    - Crea diagrama de arquitectura
    - Documenta controladores y endpoints
    - Genera reportes de dependencias
    
    Parámetros esperados:
    - project_name: str - Nombre del proyecto
    - repository_url: str - URL del repositorio
    - access_token: str - Token de acceso
    - controllers: list[str] - Controladores
    - modules: list[str] - Módulos
    - languages: list[str] - Lenguajes
    - frameworks: list[str] - Frameworks
    - format: str - Formato (markdown|html|pdf)
    """
    
    # Parámetros requeridos
    required_params = [
        "project_name"
    ]
    
    def __init__(self, **kwargs):
        """Inicializa la acción DocumentModules."""
        super().__init__()
        # Aceptar kwargs sin fallar si hay parámetros extras
        self.external_service_url = kwargs.get(
            "external_service_url", 
            "http://127.0.0.1:8001/api/v1/tasks"
        )
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la acción de documentación de módulos.
        
        Args:
            params: Dict con parámetros:
                - project_name o proyecto: Nombre del proyecto (requerido)
                - repository_url: URL del repositorio (opcional)
                - access_token: Token de acceso (opcional)
                - controllers: Lista de controladores (opcional)
                - modules: Lista de módulos (opcional)
                - languages: Lenguajes utilizados (opcional)
                - frameworks: Frameworks utilizados (opcional)
                - format: Formato de salida (opcional, default: markdown)
                - documentation_scope: Scope de documentación (opcional)
        
        Returns:
            Dict con resultado de la ejecución
        """
        
        try:
            # Normalizar parámetros: aceptar tanto "project_name" como "proyecto"
            # Gemini podría extraer cualquiera de estos nombres
            project_name = params.get("project_name") or params.get("proyecto")
            
            # Validar parámetro requerido
            if not project_name:
                return self.format_response(
                    data={},
                    status=False,
                    msg="Falta parámetro requerido: project_name (o proyecto)"
                )
            
            # Extraer parámetros restantes
            repository_url = params.get("repository_url", "")
            access_token = params.get("access_token", "")
            controllers = params.get("controllers", [])
            modules = params.get("modules", [])
            languages = params.get("languages", ["Python"])
            frameworks = params.get("frameworks", ["FastAPI"])
            output_format = params.get("format", "markdown")
            documentation_scope = params.get("documentation_scope", {})
            
            # Generar IDs únicos
            task_id = str(uuid.uuid4())
            trace_id = str(uuid.uuid4())
            
            # Construir payload dinámico
            payload = {
                "project": {
                    "name": project_name,
                    "description": params.get("description", ""),
                    "repository_url": repository_url,
                    "access_token": access_token
                },
                "structure": {
                    "controllers": controllers if controllers else [],
                    "modules": modules if modules else [],
                    "key_paths": params.get("key_paths", [])
                },
                "technologies": {
                    "languages": languages,
                    "frameworks": frameworks,
                    "external_apis": params.get("external_apis", []),
                    "databases": params.get("databases", [])
                },
                "documentation_scope": {
                    "format": output_format,
                    "output_location": documentation_scope.get(
                        "output_location", 
                        f"./docs/{project_name.lower()}"
                    ),
                    "include_architecture": documentation_scope.get("include_architecture", True),
                    "include_endpoints": documentation_scope.get("include_endpoints", True),
                    "include_models": documentation_scope.get("include_models", True),
                    "include_dependencies": documentation_scope.get("include_dependencies", True)
                }
            }
            
            # Construir request hacia servicio externo
            request_payload = {
                "task_id": task_id,
                "capability": "document_modules",
                "payload": payload,
                "context": {
                    "agent_id": params.get("agent_id", "ia-agent-001"),
                    "user_id": params.get("user_id", "system"),
                    "trace_id": trace_id,
                    "source": "vscode"
                }
            }
            
            print(f"📋 Documentando módulos del proyecto: {project_name}")
            print(f"   Task ID: {task_id}")
            print(f"   Formato: {output_format}")
            print(f"   Módulos: {len(modules)} | Controladores: {len(controllers)}")
            print(f"   URL del servicio: {self.external_service_url}")
            
            # Enviar request al servicio externo
            try:
                response = requests.post(
                    self.external_service_url,
                    json=request_payload,
                    timeout=30,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"✅ Respuesta del servicio: {response.status_code}")
                
                # Verificar respuesta
                if response.status_code in [200, 201]:
                    service_data = response.json()
                    
                    return self.format_response(
                        data={
                            "task_id": task_id,
                            "trace_id": trace_id,
                            "status": "queued",
                            "message": f"Documentación de '{project_name}' encolada para procesamiento",
                            "format": output_format,
                            "output_location": payload["documentation_scope"]["output_location"],
                            "estimated_time": "2-5 minutos",
                            "service_response": service_data
                        },
                        status=True,
                        msg=f"Acción document_modules iniciada para '{project_name}'"
                    )
                else:
                    return self.format_response(
                        data={
                            "task_id": task_id,
                            "error": f"Servicio respondió con código {response.status_code}"
                        },
                        status=False,
                        msg=f"Error al enviar tarea al servicio externo: {response.status_code}"
                    )
                    
            except requests.exceptions.Timeout:
                return self.format_response(
                    data={"task_id": task_id},
                    status=False,
                    msg=f"Timeout al conectar con el servicio externo ({self.external_service_url})"
                )
            except requests.exceptions.ConnectionError:
                return self.format_response(
                    data={"task_id": task_id},
                    status=False,
                    msg=f"No se pudo conectar al servicio externo ({self.external_service_url}). Verifica que esté corriendo."
                )
            except Exception as req_err:
                return self.format_response(
                    data={"task_id": task_id},
                    status=False,
                    msg=f"Error al comunicarse con el servicio: {str(req_err)}"
                )
            
        except Exception as e:
            return self.format_response(
                data={},
                status=False,
                msg=f"Error en DocumentModulesAction: {str(e)}"
            )
