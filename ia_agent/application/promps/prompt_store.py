from app import redis_client

class PromptStore:

    @staticmethod
    def get_prompt(key: str) -> str:
        raw = redis_client.get(key)
        if not raw:
            raise Exception(f"Prompt '{key}' no encontrado en Redis")
        return raw.decode("utf-8")
