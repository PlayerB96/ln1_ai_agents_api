import json
from infrastructure.config.redis_config import RedisConfig

class LangGraphResponse:

    @staticmethod
    def fetch_and_filter_actions(redis_client, intent: str) -> list:
        """
        Función helper que realiza el parseo y filtrado de acciones desde Redis.
        
        Args:
            redis_client: Cliente de Redis
            intent: Intención clasificada para filtrar acciones
        
        Returns:
            Lista de acciones coincidentes ordenadas por prioridad
        """
        action_keys = redis_client.keys("agente:actions:*")
        matched_actions = []
        intent_lower = intent.lower()
                
        for key in action_keys:
            try:
                key_type = redis_client.type(key)
                actions_data = None
                
                # Leer según el tipo de dato
                if key_type == "ReJSON-RL":
                    json_data = redis_client.execute_command('JSON.GET', key)
                    actions_data = json.loads(json_data) if isinstance(json_data, str) else json_data
                    print(actions_data)
                elif key_type == "string":
                    json_str = redis_client.get(key)
                    actions_data = json.loads(json_str) if json_str else None
                
                if not actions_data:
                    continue
                
                # Detectar si es acción individual o estructura múltiple
                actions_list = []
                if isinstance(actions_data, list):
                    actions_list = actions_data
                elif isinstance(actions_data, dict) and "id" in actions_data and "tags" in actions_data:
                    # Es una acción individual con estructura: {"id": ..., "tags": ...}
                    actions_list = [actions_data]
                elif isinstance(actions_data, dict):
                    # Es un diccionario con múltiples acciones como valores
                    actions_list = list(actions_data.values())
                else:
                    continue
                                
                # Iterar sobre cada acción
                for action_detail in actions_list:
                    if not isinstance(action_detail, dict):
                        continue
                    
                    action_id = action_detail.get("id", "unknown")
                    tags = action_detail.get("tags", [])
                    if not isinstance(tags, list):
                        tags = [tags]
                    tags_lower = [tag.lower() for tag in tags]
                    
                    print(f"    - {action_id}: tags={tags_lower}")
                    
                    # Si hay coincidencia
                    if intent_lower in tags_lower:
                        matched_actions.append({
                            "id": action_detail.get("id", action_id),
                            "description": action_detail.get("description", ""),
                            "tags": tags,
                            "priority": action_detail.get("priority", 0),
                            "params": action_detail.get("params", {}),
                            "required": action_detail.get("required", []),
                            "examples": action_detail.get("examples", []),
                            "source_key": key
                        })
            
            except Exception as e:
                print(f"  ⚠️ Error procesando {key}: {e}")
                continue
        
        # Ordenar por prioridad (descendente)
        matched_actions.sort(key=lambda x: x["priority"], reverse=True)
        
        return matched_actions
