"""Session JWTs. The token carries only the user id; role and scope are re-read from the database
on every request, so a changed assignment takes effect immediately."""

from datetime import UTC, datetime, timedelta

import jwt

ALGORITHM = "HS256"
COOKIE_NAME = "session"


class InvalidToken(Exception):
    pass


def issue_token(user_id: str, secret: str, ttl_minutes: int) -> str:
    now = datetime.now(UTC)
    claims = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=ttl_minutes)}
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def read_token(token: str, secret: str) -> str:
    """Return the user id, or raise InvalidToken (bad signature, expired, malformed)."""
    try:
        claims = jwt.decode(
            token, secret, algorithms=[ALGORITHM], options={"require": ["sub", "exp"]}
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc
    return str(claims["sub"])
