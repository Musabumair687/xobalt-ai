from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ScoreBreakdownCategory(BaseModel):
    score: int
    reason: str
    confidence: Optional[float] = None


class ScoreBreakdown(BaseModel):
    industry_match: Optional[ScoreBreakdownCategory] = None
    company_size: Optional[ScoreBreakdownCategory] = None
    location: Optional[ScoreBreakdownCategory] = None
    decision_maker: Optional[ScoreBreakdownCategory] = None
    website: Optional[ScoreBreakdownCategory] = None
    intent: Optional[ScoreBreakdownCategory] = None

    def total_score(self) -> int:
        total = 0
        if self.industry_match:
            total += self.industry_match.score
        if self.company_size:
            total += self.company_size.score
        if self.location:
            total += self.location.score
        if self.decision_maker:
            total += self.decision_maker.score
        if self.website:
            total += self.website.score
        if self.intent:
            total += self.intent.score
        return min(total, 100)


class IntentSignalResult(BaseModel):
    signal_type: str
    description: str
    evidence: str
    confidence: float


class ScoringResult(BaseModel):
    lead_id: uuid.UUID
    score: int
    classification: str
    breakdown: ScoreBreakdown
    intent_signals: list[IntentSignalResult] = Field(default_factory=list)


class LeadScoreResponse(BaseModel):
    lead_id: uuid.UUID
    score: int
    classification: str
    breakdown: ScoreBreakdown
    intent_signals: list[IntentSignalResult]
