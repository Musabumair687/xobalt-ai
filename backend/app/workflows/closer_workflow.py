"""LangGraph workflow for Phase 8 Closer."""

import functools
from langgraph.graph import StateGraph, START, END
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.closer.state import CloserState
from app.agents.closer.nodes import (
    load_conversation,
    build_context,
    classify_intent,
    route_action,
    generate_response,
    route_to_booking,
    mark_opt_out,
    stop_campaign,
    schedule_later,
    wait_ooo,
    human_review
)
from app.services.conversation_context_service import ConversationContextService
from app.services.reply_classification_service import ReplyClassificationService
from app.services.response_service import ResponseService

def build_closer_graph(
    db: AsyncSession,
    context_service: ConversationContextService,
    classification_service: ReplyClassificationService,
    response_service: ResponseService
) -> StateGraph:
    """Builds and compiles the Closer execution graph."""
    
    graph = StateGraph(CloserState)
    
    node_load = functools.partial(load_conversation, db=db)
    node_context = functools.partial(build_context, context_service=context_service)
    node_classify = functools.partial(classify_intent, classification_service=classification_service)
    
    node_gen_response = functools.partial(generate_response, response_service=response_service, db=db)
    node_booking = functools.partial(route_to_booking, db=db)
    node_optout = functools.partial(mark_opt_out, db=db)
    node_stop = functools.partial(stop_campaign, db=db)
    node_later = functools.partial(schedule_later, db=db)
    node_wait = functools.partial(wait_ooo, db=db)
    node_human = functools.partial(human_review, db=db)
    
    graph.add_node("load_conversation", node_load)
    graph.add_node("build_context", node_context)
    graph.add_node("classify_intent", node_classify)
    
    graph.add_node("generate_response", node_gen_response)
    graph.add_node("route_to_booking", node_booking)
    graph.add_node("mark_opt_out", node_optout)
    graph.add_node("stop_campaign", node_stop)
    graph.add_node("schedule_later", node_later)
    graph.add_node("wait", node_wait)
    graph.add_node("human_review", node_human)
    
    graph.add_edge(START, "load_conversation")
    graph.add_edge("load_conversation", "build_context")
    graph.add_edge("build_context", "classify_intent")
    
    graph.add_conditional_edges("classify_intent", route_action, {
        "generate_response": "generate_response",
        "route_to_booking": "route_to_booking",
        "mark_opt_out": "mark_opt_out",
        "stop_campaign": "stop_campaign",
        "schedule_later": "schedule_later",
        "wait": "wait",
        "human_review": "human_review",
        "end": END
    })
    
    graph.add_edge("generate_response", END)
    graph.add_edge("route_to_booking", END)
    graph.add_edge("mark_opt_out", END)
    graph.add_edge("stop_campaign", END)
    graph.add_edge("schedule_later", END)
    graph.add_edge("wait", END)
    graph.add_edge("human_review", END)
    
    return graph.compile()
