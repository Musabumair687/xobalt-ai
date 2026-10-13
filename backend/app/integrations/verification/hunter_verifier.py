"""Hunter.io Email Verification Provider."""

from __future__ import annotations

import logging
import httpx

from app.integrations.verification.base import VerificationProvider
from app.schemas.hunter import VerificationResult, VerificationStatus

logger = logging.getLogger(__name__)


class HunterVerificationProvider(VerificationProvider):
    """Email deliverability verification via Hunter.io API."""

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key
        self._base_url = "https://api.hunter.io/v2"

    @property
    def name(self) -> str:
        return "hunter_verifier"

    async def is_available(self) -> bool:
        return bool(self._api_key)

    async def verify_email(self, email: str) -> VerificationResult:
        if not self._api_key or not email:
            return VerificationResult(
                contact_value=email,
                status=VerificationStatus.skipped,
                reason="no_api_key",
            )

        params = {
            "email": email,
            "api_key": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.get(f"{self._base_url}/email-verifier", params=params)
                if res.status_code == 200:
                    data = res.json().get("data", {})
                    raw_status = data.get("status", "unknown").lower()
                    score = data.get("score", 50) / 100.0

                    if raw_status == "valid":
                        status = VerificationStatus.valid
                    elif raw_status == "invalid":
                        status = VerificationStatus.invalid
                    elif raw_status in ("accept_all", "webmail"):
                        status = VerificationStatus.risky
                    else:
                        status = VerificationStatus.unknown

                    return VerificationResult(
                        contact_value=email,
                        status=status,
                        confidence=score,
                        provider=self.name,
                        reason=f"hunter_{raw_status}",
                    )
        except Exception as e:
            logger.warning("Hunter email verification failed for '%s': %s", email, e)

        return VerificationResult(
            contact_value=email,
            status=VerificationStatus.unknown,
            confidence=0.0,
            provider=self.name,
            reason="api_error",
        )
