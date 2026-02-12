"""
Herramientas - Funciones y servicios disponibles para el agente
Implementa MCP (Model Context Protocol) con reglas y contratos
"""
from typing import Dict, Any
from infrastructure.config.redis_config import RedisConfig
import json


class ToolContract:
    """Define el contrato de una herramienta con reglas y validaciones"""
    def __init__(self, name: str, description: str, params: Dict[str, str]):
        self.name = name
        self.description = description
        self.params = params
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.params
        }


class LangGraphTools:
    """MCP Tools - Herramientas disponibles para el LLM con reglas"""
    
    # Definir contratos de herramientas disponibles
    AVAILABLE_TOOLS = {
        "get_agent_actions": ToolContract(
            name="get_agent_actions",
            description="Obtiene todas las acciones disponibles del agente desde Redis (ln1 y default)",
            params={
                "agent_type": "Tipo de agente (ej: ln1 o default)"
            }
        ),
        "execute_action": ToolContract(
            name="execute_action",
            description="Ejecuta una acción específica del agente",
            params={
                "action_name": "Nombre de la acción a ejecutar",
                "parameters": "Parámetros de la acción"
            }
        )
    }
    
    @staticmethod
    def get_agent_actions(agent_type: str = None) -> Dict[str, Any]:
        """
        Obtiene las acciones disponibles del agente desde Redis
        
        Reglas:
        - Si agent_type es None, trae todas las acciones (ln1 + default)
        - Si agent_type es específico, trae solo esas
        
        Returns:
            Dict con las acciones formateadas para el LLM
        """
        redis_client = RedisConfig.get_client()
        actions_data = {}
        
        try:
            if agent_type:
                # Buscar tipo específico
                key = f"agente:actions:{agent_type}"
                key_type = redis_client.type(key)
                
                if key_type == "ReJSON-RL":
                    value = redis_client.execute_command('JSON.GET', key)
                    actions_data[agent_type] = json.loads(value) if isinstance(value, str) else value
            else:
                # Buscar todas las acciones
                action_keys = redis_client.keys("agente:actions:*")
                for key in action_keys:
                    agent_name = key.split(":")[-1]
                    key_type = redis_client.type(key)
                    
                    if key_type == "ReJSON-RL":
                        value = redis_client.execute_command('JSON.GET', key)
                        actions_data[agent_name] = json.loads(value) if isinstance(value, str) else value
            
            return {
                "success": True,
                "actions": actions_data,
                "count": len(actions_data)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "actions": {}
            }
    
    @staticmethod
    def get_available_tools() -> list:
        """Retorna la lista de herramientas disponibles y sus contratos"""
        return [tool.to_dict() for tool in LangGraphTools.AVAILABLE_TOOLS.values()]
