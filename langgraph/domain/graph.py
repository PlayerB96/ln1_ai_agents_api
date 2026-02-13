from langgraph.graph import StateGraph, END
from langgraph.domain.states import ConversationState
from langgraph.domain.nodes import build_prompt_classifier_node, llm_classifier_node , actions_retriever_node


def build_graph():
    # Define un grafo con estado que opera sobre ConversationState.
    graph = StateGraph(ConversationState)

    # Registra el nodo clasificador de reglas (primer paso) / Construye classifier_prompt.
    graph.add_node("build_prompt_classifier", build_prompt_classifier_node)

    # Registra el nodo LLM para clasificación (segundo paso) / Envia classifier_prompt a Gemini.
    graph.add_node("llm_classifier", llm_classifier_node)

    # Registra el nodo que recupera acciones (tercer paso) / Filtro de acciones segun intent identificado por llm_classifier.
    graph.add_node("actions_retriever", actions_retriever_node)

    # Punto de entrada: comienza con clasificación de reglas.
    graph.set_entry_point("build_prompt_classifier")

    # Flujo: build_prompt_classifier → llm_classifier → actions_retriever → END
    graph.add_edge("build_prompt_classifier", "llm_classifier")
    graph.add_edge("llm_classifier", "actions_retriever")
    graph.add_edge("actions_retriever", END)

    # Compila el grafo en un pipeline ejecutable.
    return graph.compile()
