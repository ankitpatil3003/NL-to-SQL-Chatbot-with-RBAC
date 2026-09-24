"""bcrypt hashing. Verification runs in a thread: bcrypt is deliberately slow (~250ms)."""

import asyncio

import bcrypt

# bcrypt only uses the first 72 bytes and bcrypt>=5 raises on longer input; treat those as a miss.
MAX_PASSWORD_BYTES = 72

# Checked against when the email is unknown, so response time doesn't reveal which accounts exist.
_DUMMY_HASH = bcrypt.hashpw(b"timing-equalizer", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, password_hash: str) -> bool:
    data = password.encode()
    if len(data) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(data, password_hash.encode())


async def verify_password(password: str, password_hash: str | None) -> bool:
    """Constant-work check: always runs one bcrypt comparison, even for unknown users."""
    ok = await asyncio.to_thread(_verify, password, password_hash or _DUMMY_HASH)
    return ok and password_hash is not None
