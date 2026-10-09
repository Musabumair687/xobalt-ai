"""LangGraph workflow for Phase 7 Enforcer."""

import functools
from langgraph.graph import StateGraph, START, END
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.enforcer.state import EnforcerState
from app.agents.enforcer.nodes import (
    load_message,
    evaluate_policy,
    execute_send,
    record_event,
    schedule_followup
)
from app.services.policy_service import PolicyService
from app.services.outreach_service import OutreachService
from app.services.message_event_service import MessageEventService
from app.services.followup_service import FollowupService

def build_enforcer_graph(
    db: AsyncSession,
    policy_service: PolicyService,
    outreach_service: OutreachService,
    event_service: MessageEventService,
    followup_service: FollowupService
) -> StateGraph:
    """Builds and compiles the Enforcer execution graph."""
    
    graph = StateGraph(EnforcerState)
    
    node_load = functools.partial(load_message, db=db)
    node_policy = functools.partial(evaluate_policy, policy_service=policy_service)
    node_send = functools.partial(execute_send, outreach_service=outreach_service)
    node_record = functools.partial(record_event, event_service=event_service)
    node_followup = functools.partial(schedule_followup, followup_service=followup_service)
    
    graph.add_node("load_message", node_load)
    graph.add_node("evaluate_policy", node_policy)
    graph.add_node("execute_send", node_send)
    graph.add_node("record_event", node_record)
    graph.add_node("schedule_followup", node_followup)
    
    graph.add_edge(START, "load_message")
    graph.add_edge("load_message", "evaluate_policy")
    graph.add_edge("evaluate_policy", "execute_send")
    
    # We record event whether blocked or sent
    graph.add_edge("execute_send", "record_event")
    graph.add_edge("record_event", "schedule_followup")
    graph.add_edge("schedule_followup", END)
    
    return graph.compile()
