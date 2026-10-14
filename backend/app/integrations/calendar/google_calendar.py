"""Google Calendar Integration (Real API with simulation fallback)."""

import logging
import uuid
from typing import List, Optional
from datetime import datetime, timedelta
import httpx

from app.integrations.calendar.base import CalendarProvider
from app.integrations.provider_errors import ProviderConfigurationError
from app.schemas.calendar import TimeSlot, CalendarEvent

logger = logging.getLogger(__name__)


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar Provider.
    
    Live calls require OAuth credentials. Simulation is available only when
    the service explicitly selects mock mode.
    """

    def __init__(
        self,
        access_token: str = "",
        refresh_token: str = "",
        client_id: str = "",
        client_secret: str = "",
        simulation: bool = False,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.simulation = simulation
        self._api_base = "https://www.googleapis.com/calendar/v3"

    @property
    def name(self) -> str:
        return "google_calendar"

    async def _ensure_access_token(self) -> str:
        if self.access_token:
            return self.access_token
        if self.refresh_token and self.client_id and self.client_secret:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                            "refresh_token": self.refresh_token,
                            "grant_type": "refresh_token",
                        },
                    )
                    if res.status_code == 200:
                        self.access_token = res.json().get("access_token", "")
                        if self.access_token:
                            return self.access_token
                    raise RuntimeError(
                        f"Google OAuth token refresh failed with HTTP {res.status_code}."
                    )
            except Exception as exc:
                if self.simulation:
                    logger.warning(
                        "Google Calendar token refresh failed in mock mode (%s).",
                        type(exc).__name__,
                    )
                else:
                    raise RuntimeError(
                        f"Google OAuth token refresh failed ({type(exc).__name__})."
                    ) from exc
        if self.simulation:
            return ""
        raise ProviderConfigurationError(
            "Google Calendar requires a valid OAuth refresh token, client ID, and client secret."
        )

    async def get_busy_slots(self, calendar_id: str, start_time: datetime, end_time: datetime) -> List[TimeSlot]:
        token = await self._ensure_access_token()
        if token:
            try:
                url = "https://www.googleapis.com/calendar/v3/freeBusy"
                payload = {
                    "timeMin": start_time.isoformat(),
                    "timeMax": end_time.isoformat(),
                    "items": [{"id": calendar_id}],
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
                    if res.status_code == 200:
                        data = res.json()
                        busy_list = data.get("calendars", {}).get(calendar_id, {}).get("busy", [])
                        slots = []
                        for b in busy_list:
                            slots.append(
                                TimeSlot(
                                    start_time=datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
                                    end_time=datetime.fromisoformat(b["end"].replace("Z", "+00:00")),
                                    timezone="UTC",
                                )
                            )
                        return slots
            except Exception as exc:
                if not self.simulation:
                    raise RuntimeError(
                        f"Google Calendar availability request failed ({type(exc).__name__})."
                    ) from exc
                logger.warning(
                    "Google Calendar availability failed in mock mode (%s).",
                    type(exc).__name__,
                )
            else:
                if not self.simulation:
                    raise RuntimeError(
                        f"Google Calendar availability request failed with HTTP {res.status_code}."
                    )

        # Simulation fallback
        busy = []
        current = start_time
        while current < end_time:
            busy.append(TimeSlot(
                start_time=current.replace(hour=12, minute=0, second=0, microsecond=0),
                end_time=current.replace(hour=13, minute=0, second=0, microsecond=0),
                timezone="UTC"
            ))
            current += timedelta(days=1)
        return busy

    async def create_event(
        self,
        calendar_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendee_emails: List[str],
        description: Optional[str] = None
    ) -> CalendarEvent:
        token = await self._ensure_access_token()
        if token:
            try:
                url = f"{self._api_base}/calendars/{calendar_id}/events"
                payload = {
                    "summary": title,
                    "description": description or "",
                    "start": {"dateTime": start_time.isoformat()},
                    "end": {"dateTime": end_time.isoformat()},
                    "attendees": [{"email": e} for e in attendee_emails],
                    "conferenceData": {
                        "createRequest": {
                            "requestId": uuid.uuid4().hex,
                            "conferenceSolutionKey": {"type": "hangoutsMeet"},
                        }
                    },
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.post(
                        url,
                        json=payload,
                        headers={"Authorization": f"Bearer {token}"},
                        params={"conferenceDataVersion": 1},
                    )
                    if res.status_code in (200, 201):
                        data = res.json()
                        meet_link = data.get("hangoutLink") or ""
                        return CalendarEvent(
                            id=data.get("id", f"gcal_{uuid.uuid4().hex[:12]}"),
                            title=title,
                            start_time=start_time,
                            end_time=end_time,
                            meeting_link=meet_link,
                            status="confirmed",
                        )
            except Exception as exc:
                if not self.simulation:
                    raise RuntimeError(
                        f"Google Calendar event creation failed ({type(exc).__name__})."
                    ) from exc
                logger.warning(
                    "Google Calendar event creation failed in mock mode (%s).",
                    type(exc).__name__,
                )
            else:
                if not self.simulation:
                    raise RuntimeError(
                        f"Google Calendar event creation failed with HTTP {res.status_code}."
                    )

        event_id = f"gcal_{uuid.uuid4().hex[:12]}"
        return CalendarEvent(
            id=event_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            meeting_link=f"https://meet.google.com/{uuid.uuid4().hex[:10]}",
            status="confirmed"
        )

    async def cancel_event(self, calendar_id: str, event_id: str) -> bool:
        token = await self._ensure_access_token()
        if token:
            try:
                url = f"{self._api_base}/calendars/{calendar_id}/events/{event_id}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.delete(url, headers={"Authorization": f"Bearer {token}"})
                    return res.status_code in (200, 204)
            except Exception as exc:
                if not self.simulation:
                    raise RuntimeError(
                        f"Google Calendar event cancellation failed ({type(exc).__name__})."
                    ) from exc
                logger.warning(
                    "Google Calendar event cancellation failed in mock mode (%s).",
                    type(exc).__name__,
                )
            else:
                if not self.simulation and res.status_code not in (200, 204):
                    raise RuntimeError(
                        f"Google Calendar event cancellation failed with HTTP {res.status_code}."
                    )
                return res.status_code in (200, 204)
        return self.simulation
