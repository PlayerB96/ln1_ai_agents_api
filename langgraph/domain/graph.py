from langgraph.graph import StateGraph, END
from langgraph.domain.states import ConversationState
from langgraph.domain.nodes import (
    entry_router_node,
    build_prompt_classifier_node,
    llm_classifier_node,
    actions_retriever_node,
    action_selector_node,
    execute_action_node,
    params_processor_node,
    wait_for_user_input_node
)
from langgraph.application.node_context import NodeContext
from langgraph.domain.nodes import entry_router, action_selector_router, params_router


def build_graph():
    graph = StateGraph(ConversationState)
    context = NodeContext()

    # Paso 0: Router de entrada - detecta si es params_required o flujo normal
    graph.add_node("entry_router", entry_router_node(context))

    # Paso 1: Construye el prompt para el clasificador
    graph.add_node("build_prompt_classifier", build_prompt_classifier_node(context))
    
    # Paso 2: Clasifica la intención del usuario usando LLM
    graph.add_node("llm_classifier", llm_classifier_node(context))
    
    # Paso 3: Recupera las acciones disponibles según la clasificación
    graph.add_node("actions_retriever", actions_retriever_node(context))
    
    # Paso 4: Selecciona la acción más apropiada
    graph.add_node("action_selector", action_selector_node(context))
    
    # Paso 5: Ejecuta la acción seleccionada y solicita parámetros
    graph.add_node("execute_action", execute_action_node(context))
    
    # Paso 6: Procesa los parámetros enviados por el usuario
    graph.add_node("params_processor", params_processor_node(context))
    
    # Paso 7: Espera input adicional del usuario cuando sea necesario
    graph.add_node("wait_for_user_input", wait_for_user_input_node(context))

    # Define el punto de entrada del grafo
    graph.set_entry_point("entry_router")

    # Routing condicional desde entry_router
    graph.add_conditional_edges(
        "entry_router",
        entry_router,
        {
            "classify": "build_prompt_classifier",
            "params": "params_processor",
            "action_select": "action_selector"
        }
    )

    # Conexiones entre nodos del flujo de clasificación
    graph.add_edge("build_prompt_classifier", "llm_classifier")
    graph.add_edge("llm_classifier", "actions_retriever")
    graph.add_edge("actions_retriever", "action_selector")

    # Routing condicional desde action_selector
    graph.add_conditional_edges("action_selector", action_selector_router, {"valid": "execute_action", "wait": "wait_for_user_input"})

    # Después de ejecutar la acción, procesar los parámetros
    graph.add_edge("execute_action", "params_processor")
    
    # Routing condicional desde params_processor
    graph.add_conditional_edges("params_processor", params_router, {"complete": END, "wait": "wait_for_user_input"})

    return graph.compile()
