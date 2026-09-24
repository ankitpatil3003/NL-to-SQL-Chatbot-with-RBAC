"""Database access for identities: public.users (read-only) and app.credentials."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.auth.passwords import hash_password, verify_password

_USER_COLUMNS = [
    "user_id",
    "email",
    "full_name",
    "role",
    "territory_name",
    "region_name",
    "can_view_wac",
]
_SELECT_USER = ", ".join(f"u.{c}" for c in _USER_COLUMNS)


async def get_user_by_id(engine: AsyncEngine, user_id: str) -> dict[str, Any] | None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT {_SELECT_USER} FROM public.users u WHERE u.user_id = :id"),
            {"id": user_id},
        )
        row = result.mappings().first()
    return dict(row) if row else None


async def get_login_record(engine: AsyncEngine, email: str) -> dict[str, Any] | None:
    """User row plus password_hash (NULL if no credential); email is case-insensitive."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                f"SELECT {_SELECT_USER}, c.password_hash "
                "FROM public.users u LEFT JOIN app.credentials c USING (user_id) "
                "WHERE lower(u.email) = lower(:email)"
            ),
            {"email": email.strip()},
        )
        row = result.mappings().first()
    return dict(row) if row else None


async def list_users(engine: AsyncEngine) -> list[dict[str, Any]]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT {_SELECT_USER} FROM public.users u ORDER BY u.user_id")
        )
        return [dict(r) for r in result.mappings()]


async def sync_demo_credentials(engine: AsyncEngine, password: str) -> int:
    """Set every user's password to `password`; returns rows written.

    Cheap on restart: all users share one hash, so a single bcrypt check tells whether anything
    changed (rotating DEMO_PASSWORD re-hashes everyone; an unchanged one writes nothing).
    """
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT count(*) FILTER (WHERE c.user_id IS NULL) AS missing, "
                "array_agg(DISTINCT c.password_hash) "
                "FILTER (WHERE c.password_hash IS NOT NULL) AS hashes "
                "FROM public.users u LEFT JOIN app.credentials c USING (user_id)"
            )
        )
        state = result.one()
        hashes = state.hashes or []
        if state.missing == 0 and len(hashes) == 1 and await verify_password(password, hashes[0]):
            return 0
        written = await conn.execute(
            text(
                "INSERT INTO app.credentials (user_id, password_hash) "
                "SELECT user_id, :hash FROM public.users "
                "ON CONFLICT (user_id) DO UPDATE "
                "SET password_hash = EXCLUDED.password_hash, updated_at = now()"
            ),
            {"hash": hash_password(password)},
        )
        return int(written.rowcount)
