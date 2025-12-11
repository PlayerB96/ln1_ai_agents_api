import json
from app import redis_client

class RedisActionStore:

    @staticmethod
    def get_all():
        try:
            if hasattr(redis_client, "json"):
                actions = redis_client.json().get("actions")
                if actions:
                    return actions

            raw = redis_client.get("actions")
            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                return json.loads(raw)

            print("⚠️ No se encontraron acciones en Redis.")
            return {}

        except Exception as e:
            print(f"⚠️ Error leyendo acciones desde Redis: {e}")
            return {}
