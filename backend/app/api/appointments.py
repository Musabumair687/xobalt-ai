"""API router for Appointments & Booking."""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.workers.calendar_worker import CalendarWorker
from app.schemas.calendar import AvailabilityRequest, BookingRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["Calendar & Appointments"])

@router.post("/availability", status_code=status.HTTP_200_OK)
async def get_availability(
    request: AvailabilityRequest,
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    worker = CalendarWorker(db)
    state = {
        "conversation_id": conversation_id,
        "action": "get_availability",
        "availability_request": request,
        "errors": []
    }
    result = await worker.run_booking_workflow(state)
    return {"available_slots": [s.model_dump() for s in result.get("available_slots", [])]}

@router.post("/book", status_code=status.HTTP_200_OK)
async def book_slot(
    request: BookingRequest,
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    worker = CalendarWorker(db)
    state = {
        "conversation_id": conversation_id,
        "action": "book_slot",
        "booking_request": request,
        "errors": []
    }
    result = await worker.run_booking_workflow(state)
    return result.get("booking_result", {"success": False, "error": "Unknown error"})
