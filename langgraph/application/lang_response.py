from infrastructure.config.redis_config import RedisConfig

class LangGraphResponse:

    @staticmethod
    def response_actions():
        redis_client = RedisConfig.get_client()
        
        try:
            # Buscar todas las keys que empiezan con "agente:actions:"
            action_keys = redis_client.keys("agente:actions:*")
            
            if action_keys:
                print("📋 Acciones guardadas en Redis:")
                for key in action_keys:
                    key_type = redis_client.type(key)  # Verificar tipo
                    print(f"Tipo de {key}: {key_type}")
                    
                    if key_type == "string":
                        value = redis_client.get(key)
                    elif key_type == "hash":
                        value = redis_client.hgetall(key)
                    elif key_type == "list":
                        value = redis_client.lrange(key, 0, -1)
                    elif key_type == "set":
                        value = redis_client.smembers(key)
                    elif key_type == "ReJSON-RL":
                        # Para JSON en Redis
                        value = redis_client.execute_command('JSON.GET', key)
                    else:
                        value = "Tipo desconocido"
                    
                    print(f"🔑 {key}: {value}")
            else:
                print("⚠️ No hay acciones guardadas")
                
        except Exception as e:
            print(f"❌ Error al leer Redis: {e}")
        
