"""Stable response shapes consumed by the web application."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class DashboardLead(BaseModel):
    id: str
    company_name: str
    company_domain: str
    website_url: str
    industry: str
    decision_maker_name: str
    decision_maker_title: str
    email: str | None
    email_status: str
    score: int | None
    qualification_status: str
    message_status: str
    created_at: str | None


class DashboardActivity(BaseModel):
    title: str
    sub: str
    time: str
    status: str


class DashboardSummaryResponse(BaseModel):
    total_leads: int
    qualified_leads: int
    total_companies: int
    messages_sent: int
    messages_drafted: int
    meetings_booked: int
    active_model: str
    llm_provider: str
    recent_discoveries: list[DashboardLead]
    recent_activity: list[DashboardActivity]
    integrations: dict[str, dict[str, Any]]


class CompanyListItem(BaseModel):
    id: str
    name: str
    domain: str | None
    industry: str | None
    employee_count: int | None
    website_url: str | None
    city: str | None
    state: str | None
    country: str | None
    leads_count: int
    intelligence: dict[str, Any] | None
    created_at: str | None


class LeadListItem(BaseModel):
    id: str
    status: str
    score: float | None
    qualification_status: str | None
    priority: str | None
    created_at: str | None
    company: dict[str, Any] | None
    person: dict[str, Any] | None
    messages: list[dict[str, Any]]
    intent_signals: list[dict[str, Any]]
    score_breakdown: dict[str, Any]
    reasoning: str
    intelligence: dict[str, Any] | None


class MessageListItem(BaseModel):
    id: str
    lead_id: str | None
    subject: str | None
    body: str
    status: str
    sent_at: str | None
    created_at: str | None
    recipient_name: str
    recipient_title: str
    recipient_email: str | None
    company_name: str
    company_domain: str | None
    lead_score: int | None


class CampaignListItem(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    target_industry: str | None
    daily_limit: int
    settings: dict[str, Any]
    lead_count: int
    message_count: int
    sent_count: int
    created_at: str | None


class AppointmentListItem(BaseModel):
    id: str
    title: str
    description: str | None
    start_time: str | None
    end_time: str | None
    timezone: str
    status: str
    meeting_link: str | None
    location: str | None
    attendee_name: str
    attendee_email: str
    company_name: str


class FunnelStage(BaseModel):
    stage: str
    count: int
    color: str


class ScoreDistribution(BaseModel):
    high_priority: int
    qualified: int
    nurture: int
    disqualified: int
    unscored: int


class RateCounts(BaseModel):
    numerator: int
    denominator: int


class AnalyticsOverviewResponse(BaseModel):
    funnel: list[FunnelStage]
    score_distribution: ScoreDistribution
    rates: dict[str, float]
    rate_counts: dict[str, RateCounts]
    rate_definitions: dict[str, str]
    data_scope: str
    integrations_status: dict[str, dict[str, Any]]
    total_companies: int
