"""LangGraph state for Booking workflow."""

import uuid
from typing import TypedDict, Optional, List
from app.schemas.calendar import TimeSlot, AvailabilityRequest, BookingRequest, BookingResult
from app.models.conversation import Conversation
from app.models.lead import Lead

class BookingState(TypedDict, total=False):
    """State for the Booking execution graph."""
    # Inputs
    conversation_id: uuid.UUID
    action: str  # "get_availability" or "book_slot"
    calendar_id: str
    
    # DB Models
    conversation: Optional[Conversation]
    lead: Optional[Lead]
    
    # Check Availability context
    availability_request: Optional[AvailabilityRequest]
    available_slots: List[TimeSlot]
    
    # Book context
    booking_request: Optional[BookingRequest]
    booking_result: Optional[BookingResult]
    
    # Global output
    errors: list[str]
