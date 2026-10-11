"""LangGraph workflow for Phase 9 Calendar Booking."""

import functools
from langgraph.graph import StateGraph, START, END
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.booking.state import BookingState
from app.agents.booking.nodes import (
    load_booking_request,
    route_booking_action,
    check_availability,
    create_booking
)
from app.services.booking_service import BookingService

def build_booking_graph(
    db: AsyncSession,
    booking_service: BookingService
) -> StateGraph:
    """Builds and compiles the Booking execution graph."""
    
    graph = StateGraph(BookingState)
    
    node_load = functools.partial(load_booking_request, db=db)
    node_check = functools.partial(check_availability, booking_svc=booking_service)
    node_book = functools.partial(create_booking, booking_svc=booking_service, db=db)
    
    graph.add_node("load_booking_request", node_load)
    graph.add_node("check_availability", node_check)
    graph.add_node("create_booking", node_book)
    
    graph.add_edge(START, "load_booking_request")
    
    graph.add_conditional_edges("load_booking_request", route_booking_action, {
        "check_availability": "check_availability",
        "create_booking": "create_booking",
        "end": END
    })
    
    graph.add_edge("check_availability", END)
    graph.add_edge("create_booking", END)
    
    return graph.compile()
