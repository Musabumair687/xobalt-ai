"""Service for managing intent signals in the database."""

import uuid
from typing import List, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.intent_signal import IntentSignal

class IntentSignalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_signals_for_lead(self, lead_id: uuid.UUID) -> Sequence[IntentSignal]:
        """Fetch all intent signals for a lead."""
        result = await self.db.execute(
            select(IntentSignal).where(IntentSignal.lead_id == lead_id).order_by(IntentSignal.detected_at.desc())
        )
        return result.scalars().all()

    async def add_signal(
        self, 
        lead_id: uuid.UUID, 
        signal_type: str, 
        description: str, 
        evidence: str, 
        confidence: float, 
        source: str = "website_intelligence"
    ) -> IntentSignal:
        """Add a new intent signal if it's not a duplicate."""
        # Simple duplicate check: same type for same lead in recent history
        # (A more advanced one would check evidence fingerprint and time window)
        existing = await self.db.execute(
            select(IntentSignal).where(
                IntentSignal.lead_id == lead_id,
                IntentSignal.signal_type == signal_type
            )
        )
        for sig in existing.scalars().all():
            # Very simplistic dedup: if type and description match exactly
            if sig.description == description:
                return sig
                
        new_signal = IntentSignal(
            lead_id=lead_id,
            signal_type=signal_type,
            description=description,
            raw_data={"evidence": evidence},
            confidence=confidence,
            source=source
        )
        self.db.add(new_signal)
        await self.db.flush()
        return new_signal

    async def add_signals(self, lead_id: uuid.UUID, signals_data: List[dict]) -> List[IntentSignal]:
        """Add multiple signals."""
        added = []
        for data in signals_data:
            sig = await self.add_signal(
                lead_id=lead_id,
                signal_type=data["signal_type"],
                description=data["description"],
                evidence=data["evidence"],
                confidence=data["confidence"]
            )
            added.append(sig)
        await self.db.commit()
        return added
