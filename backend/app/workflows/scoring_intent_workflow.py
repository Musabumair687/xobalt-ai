"""LangGraph workflow for Scoring and Intent."""

import functools
from langgraph.graph import StateGraph, START, END
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.scoring_intent.state import ScoringIntentState
from app.agents.scoring_intent.nodes import (
    load_context,
    detect_intent,
    validate_intent,
    calculate_score,
    classify_lead,
    store_result
)
from app.services.intent_service import IntentService
from app.services.intent_signal_service import IntentSignalService
from app.services.scoring_service import ScoringService

def build_scoring_intent_graph(
    db: AsyncSession,
    intent_service: IntentService,
    signal_service: IntentSignalService,
    scoring_service: ScoringService
) -> StateGraph:
    """Builds and compiles the Scoring and Intent workflow graph."""
    
    graph = StateGraph(ScoringIntentState)
    
    # Bind dependencies to nodes
    node_load = functools.partial(load_context, db=db)
    node_detect = functools.partial(detect_intent, intent_service=intent_service)
    node_validate = functools.partial(validate_intent, signal_service=signal_service)
    node_calculate = functools.partial(calculate_score, scoring_service=scoring_service)
    node_store = functools.partial(store_result, db=db)
    
    graph.add_node("load_context", node_load)
    graph.add_node("detect_intent", node_detect)
    graph.add_node("validate_intent", node_validate)
    graph.add_node("calculate_score", node_calculate)
    graph.add_node("classify_lead", classify_lead)
    graph.add_node("store_result", node_store)
    
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "detect_intent")
    graph.add_edge("detect_intent", "validate_intent")
    graph.add_edge("validate_intent", "calculate_score")
    graph.add_edge("calculate_score", "classify_lead")
    graph.add_edge("classify_lead", "store_result")
    graph.add_edge("store_result", END)
    
    return graph.compile()
