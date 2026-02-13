from infrastructure.config.redis_config import RedisConfig
from langgraph.infrastructure.llm_adapter import GeminiLLMAdapter


class NodeContext:
    """
    Contenedor de dependencias compartidas entre nodos LangGraph.
    """
    def __init__(self):
        self.redis = RedisConfig.get_client()
        self.llm = GeminiLLMAdapter()
