"""LangGraph nodes for the Booking workflow."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.agents.booking.state import BookingState
from app.services.booking_service import BookingService
from app.models.conversation import Conversation
from app.models.lead import Lead
from app.models.person import Person
from app.models.contact import Contact

logger = logging.getLogger(__name__)

async def load_booking_request(state: BookingState, db: AsyncSession) -> dict:
    """Load DB context for the booking request."""
    conv_id = state.get("conversation_id")
    if not conv_id:
        return {"errors": ["Missing conversation_id"]}
        
    res_conv = await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.lead)
            .selectinload(Lead.person)
            .selectinload(Person.contacts)
        )
        .where(Conversation.id == conv_id)
    )
    conv = res_conv.scalars().first()
    
    if not conv:
        return {"errors": [f"Conversation {conv_id} not found"]}
        
    return {
        "conversation": conv,
        "lead": conv.lead
    }

def route_booking_action(state: BookingState) -> str:
    if state.get("errors"): return "end"
    if state.get("action") == "get_availability": return "check_availability"
    if state.get("action") == "book_slot": return "create_booking"
    return "end"

async def check_availability(state: BookingState, booking_svc: BookingService) -> dict:
    """Query available slots."""
    req = state.get("availability_request")
    if not req: return {"errors": ["Missing availability_request"]}
    
    calendar_id = "default"  # Normally we lookup the org's calendar
    slots = await booking_svc.get_available_slots(req, calendar_id)
    
    return {"available_slots": slots}

async def create_booking(state: BookingState, booking_svc: BookingService, db: AsyncSession) -> dict:
    """Attempt to create the booking."""
    req = state.get("booking_request")
    if not req: return {"errors": ["Missing booking_request"]}
    
    lead = state["lead"]
    email = next((c.value for c in lead.person.contacts if c.type == "email"), "")
    
    result = await booking_svc.book_meeting(
        request=req,
        conv_id=state["conversation_id"],
        title=f"Meeting with {lead.person.first_name} {lead.person.last_name}",
        attendees=[email] if email else []
    )
    
    if result.success:
        state["conversation"].status = "BOOKED"
        await db.commit()
        
    return {"booking_result": result}
