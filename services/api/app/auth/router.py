"""Login / logout / whoami, plus the demo-account list for the login page."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.auth.deps import CurrentUser
from app.auth.passwords import verify_password
from app.auth.repository import get_login_record, list_users
from app.auth.tokens import COOKIE_NAME, issue_token
from app.core.config import Settings, get_settings
from app.rbac.context import AccessDenied, UserContext, build_user_context

router = APIRouter(prefix="/api/auth", tags=["auth"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


class LoginRequest(BaseModel):
    email: str
    password: str


class Me(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    territory: str | None
    region: str | None
    scope_label: str
    can_view_wac: bool

    @classmethod
    def of(cls, u: UserContext) -> "Me":
        return cls(
            user_id=u.user_id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value,
            territory=u.territory,
            region=u.region,
            scope_label=u.scope_label,
            can_view_wac=u.can_view_wac,
        )


class DemoAccount(BaseModel):
    email: str
    full_name: str
    role: str
    scope_label: str


class DemoAccounts(BaseModel):
    password: str | None
    accounts: list[DemoAccount]


@router.post("/login")
async def login(
    body: LoginRequest, request: Request, response: Response, settings: SettingsDep
) -> Me:
    record = await get_login_record(request.app.state.engine, body.email)
    ok = await verify_password(body.password, record["password_hash"] if record else None)
    if not record or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    try:
        user = build_user_context(record)
    except AccessDenied as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from None

    response.set_cookie(
        COOKIE_NAME,
        issue_token(user.user_id, settings.jwt_secret, settings.jwt_ttl_minutes),
        max_age=settings.jwt_ttl_minutes * 60,
        httponly=True,  # unreadable by page JS
        secure=not settings.is_local,  # HTTPS-only in AWS; local dev is plain http
        samesite="lax",  # no cross-site POSTs (CSRF), normal navigation still works
        path="/",
    )
    return Me.of(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me")
async def me(user: CurrentUser) -> Me:
    return Me.of(user)


@router.get("/demo-accounts")
async def demo_accounts(request: Request, settings: SettingsDep) -> DemoAccounts:
    if not settings.demo_show_credentials:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    accounts = []
    for row in await list_users(request.app.state.engine):
        try:
            u = build_user_context(row)
        except AccessDenied:
            continue  # misconfigured users can't log in, so don't advertise them
        accounts.append(
            DemoAccount(
                email=u.email, full_name=u.full_name, role=u.role.value, scope_label=u.scope_label
            )
        )
    return DemoAccounts(password=settings.demo_password, accounts=accounts)
