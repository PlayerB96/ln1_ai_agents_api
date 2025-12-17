"""
Adaptador para comunicación con Cloudflare Workers vía GraphQL.
Implementa retry logic y manejo robusto de errores.
"""
import requests
from typing import Dict, Any, Optional
from configparser import ConfigParser
from infrastructure.ports.worker_port import WorkerPort


class CloudflareWorkerAdapter(WorkerPort):
    """
    Adaptador para comunicación con Cloudflare Workers.
    Implementa el puerto WorkerPort con retry logic y timeout.
    """
    
    def __init__(self, worker_url: Optional[str] = None, timeout: int = 30, max_retries: int = 2):
        """
        Inicializa el adaptador.
        
        Args:
            worker_url: URL del worker (si no se proporciona, se lee de config.ini)
            timeout: Timeout en segundos para las peticiones
            max_retries: Número máximo de reintentos en caso de fallo
        """
        if worker_url:
            self.worker_url = worker_url
        else:
            config = ConfigParser()
            config.read("config.ini")
            self.worker_url = config.get("WORKERS", "graphql_url", 
                                        fallback="https://my-graphql-worker.soporteti-41b.workers.dev/")
        
        self.timeout = timeout
        self.max_retries = max_retries
    
    def call_mutation(self, mutation: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una mutación GraphQL en el worker con retry logic.
        
        Args:
            mutation: Query GraphQL de la mutación
            variables: Variables para la mutación
            
        Returns:
            Dict con la respuesta del worker
            
        Raises:
            Exception: Si falla después de todos los reintentos
        """
        payload = {
            "query": mutation,
            "variables": variables
        }
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    self.worker_url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Verificar si hay errores en la respuesta GraphQL
                if "errors" in result:
                    return {
                        "status": False,
                        "msg": f"Error en GraphQL: {result['errors']}",
                        "data": {}
                    }
                
                return result.get("data", {})
                
            except requests.Timeout as e:
                last_error = f"Timeout al conectar con el worker (intento {attempt + 1}/{self.max_retries + 1})"
                continue
                
            except requests.RequestException as e:
                last_error = f"Error de conexión: {str(e)}"
                if attempt == self.max_retries:
                    break
                continue
                
            except Exception as e:
                last_error = f"Error inesperado: {str(e)}"
                break
        
        # Si llegamos aquí, todos los intentos fallaron
        return {
            "status": False,
            "msg": last_error or "Error desconocido al conectar con el worker",
            "data": {}
        }
