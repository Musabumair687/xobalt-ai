"""LangGraph workflow for Phase 6 Personalization."""

import functools
from langgraph.graph import StateGraph, START, END
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.personalization.state import PersonalizationState
from app.agents.personalization.nodes import (
    load_context,
    build_personalization_context,
    generate_message,
    validate_message,
    store_message
)
from app.services.personalization_service import PersonalizationService
from app.services.message_validation_service import MessageValidationService

def build_personalization_graph(
    db: AsyncSession,
    personalization_service: PersonalizationService,
    validation_service: MessageValidationService
) -> StateGraph:
    """Builds and compiles the Personalization workflow graph."""
    
    graph = StateGraph(PersonalizationState)
    
    # Bind dependencies to nodes
    node_load = functools.partial(load_context, db=db)
    node_build_ctx = functools.partial(build_personalization_context, personalization_service=personalization_service)
    node_generate = functools.partial(generate_message, personalization_service=personalization_service)
    node_validate = functools.partial(validate_message, validation_service=validation_service)
    node_store = functools.partial(store_message, db=db)
    
    graph.add_node("load_context", node_load)
    graph.add_node("build_personalization_context", node_build_ctx)
    graph.add_node("generate_message", node_generate)
    graph.add_node("validate_message", node_validate)
    graph.add_node("store_message", node_store)
    
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "build_personalization_context")
    graph.add_edge("build_personalization_context", "generate_message")
    graph.add_edge("generate_message", "validate_message")
    
    # Conditional branching: if generation/validation failed hard, still store as draft
    graph.add_edge("validate_message", "store_message")
    
    graph.add_edge("store_message", END)
    
    return graph.compile()
