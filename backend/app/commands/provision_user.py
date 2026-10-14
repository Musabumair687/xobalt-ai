"""Interactively create an organization and its first user."""

from __future__ import annotations

import argparse
import asyncio
from getpass import getpass

from sqlalchemy import select

from app.auth import hash_password
from app.database.session import AsyncSessionLocal
from app.models.organization import Organization
from app.models.user import User


async def provision_user(
    organization_name: str,
    organization_slug: str,
    email: str,
    full_name: str,
    password: str,
) -> None:
    async with AsyncSessionLocal() as db:
        existing_user = await db.execute(
            select(User.id).where(User.email == email.lower())
        )
        if existing_user.scalar_one_or_none() is not None:
            raise ValueError(f"A user with email {email!r} already exists.")

        result = await db.execute(
            select(Organization).where(Organization.slug == organization_slug)
        )
        organization = result.scalars().first()
        if organization is None:
            organization = Organization(
                name=organization_name,
                slug=organization_slug,
            )
            db.add(organization)
            await db.flush()

        db.add(
            User(
                organization_id=organization.id,
                email=email.lower(),
                full_name=full_name,
                role="owner",
                hashed_password=hash_password(password),
            )
        )
        await db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organization-name", required=True)
    parser.add_argument("--organization-slug", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()

    password = getpass("Password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match.")
    if len(password) < 12 or len(password) > 1024:
        parser.error("Password must be between 12 and 1024 characters.")

    if not all(
        value.strip()
        for value in (
            args.organization_name,
            args.organization_slug,
            args.email,
            args.full_name,
        )
    ):
        parser.error("Organization name, slug, email, and full name must be non-empty.")

    asyncio.run(
        provision_user(
            args.organization_name,
            args.organization_slug,
            args.email.strip(),
            args.full_name.strip(),
            password,
        )
    )
    print(f"Provisioned owner account for {args.email.strip().lower()}.")


if __name__ == "__main__":
    main()
