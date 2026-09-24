"""Resolves the caller. Every protected route depends on CurrentUser."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.auth.repository import get_user_by_id
from app.auth.tokens import COOKIE_NAME, InvalidToken, read_token
from app.core.config import Settings, get_settings
from app.rbac.context import AccessDenied, UserContext, build_user_context


def _unauthenticated() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")


async def current_user(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> UserContext:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise _unauthenticated()
    try:
        user_id = read_token(token, settings.jwt_secret)
    except InvalidToken:
        raise _unauthenticated() from None
    row = await get_user_by_id(request.app.state.engine, user_id)
    if row is None:  # user removed since the token was issued
        raise _unauthenticated()
    try:
        return build_user_context(row)
    except AccessDenied as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from None


CurrentUser = Annotated[UserContext, Depends(current_user)]
