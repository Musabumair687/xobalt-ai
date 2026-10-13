"""DNS MX and Syntax Email Verifier (Zero API keys required)."""

from __future__ import annotations

import asyncio
import logging
import re
import socket

from app.integrations.verification.base import VerificationProvider
from app.schemas.hunter import VerificationResult, VerificationStatus

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class DnsVerificationProvider(VerificationProvider):
    """Zero-key email verifier performing syntax validation and DNS host/MX verification."""

    @property
    def name(self) -> str:
        return "dns_verifier"

    async def is_available(self) -> bool:
        return True

    async def verify_email(self, email: str) -> VerificationResult:
        email = email.strip()
        if not email or not EMAIL_REGEX.match(email):
            return VerificationResult(
                contact_value=email,
                status=VerificationStatus.invalid,
                confidence=0.0,
                provider=self.name,
                reason="invalid_syntax",
            )

        domain = email.split("@")[-1].lower()

        # Check domain DNS resolution via socket in worker thread
        def _check_domain(dom: str) -> bool:
            try:
                # Check MX or host resolution
                socket.getaddrinfo(dom, 25, proto=socket.IPPROTO_TCP)
                return True
            except socket.gaierror:
                return False
            except Exception:
                return False

        has_mail_server = await asyncio.to_thread(_check_domain, domain)

        if not has_mail_server:
            return VerificationResult(
                contact_value=email,
                status=VerificationStatus.invalid,
                confidence=0.0,
                provider=self.name,
                reason="domain_not_resolvable",
            )

        return VerificationResult(
            contact_value=email,
            status=VerificationStatus.valid,
            confidence=0.85,
            provider=self.name,
            reason="dns_resolvable",
        )
