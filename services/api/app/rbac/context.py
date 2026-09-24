"""Who is asking, and what they may see. Built server-side from public.users on every request.

Fails closed: a users row that doesn't fit the documented model (docs/security_model.md) raises
AccessDenied rather than being granted a guessed scope.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal


class AccessDenied(Exception):
    """The user may not use the assistant (unknown role or inconsistent assignment)."""


class Role(StrEnum):
    EXEC = "exec"
    DIRECTOR = "director"
    RAM = "ram"


@dataclass(frozen=True, slots=True)
class Scope:
    """Row-level restriction. Execs have none (UserContext.scope is None)."""

    level: Literal["territory", "region"]
    value: str


@dataclass(frozen=True, slots=True)
class UserContext:
    user_id: str
    email: str
    full_name: str
    role: Role
    territory: str | None
    region: str | None
    scope: Scope | None
    can_view_wac: bool

    @property
    def scope_label(self) -> str:
        """Human-readable data scope, for the UI badge and the system prompt."""
        if self.scope is None:
            return "All territories and regions"
        return f"{self.scope.value} {self.scope.level}"


def build_user_context(row: dict[str, Any]) -> UserContext:
    """Map a public.users row to a UserContext, enforcing the role model."""
    try:
        role = Role(row["role"])
    except ValueError as exc:
        raise AccessDenied(f"unknown role {row['role']!r}") from exc

    territory, region = row.get("territory_name"), row.get("region_name")
    wac_flag = row.get("can_view_wac") == 1

    scope: Scope | None
    if role is Role.EXEC:
        # Execs get unrestricted rows *and* WAC. An exec without the WAC flag is a combination the
        # security model doesn't define; refuse rather than invent one.
        if not wac_flag:
            raise AccessDenied("exec without can_view_wac is not a supported configuration")
        scope = None
    elif role is Role.DIRECTOR:
        if not region:
            raise AccessDenied("director has no region assigned")
        scope = Scope("region", region)
    else:
        if not territory:
            raise AccessDenied("RAM has no territory assigned")
        scope = Scope("territory", territory)

    return UserContext(
        user_id=row["user_id"],
        email=row["email"],
        full_name=row["full_name"],
        role=role,
        territory=territory,
        region=region,
        scope=scope,
        # Role wins over the flag: only Execs ever see WAC, even if a non-exec row says 1.
        can_view_wac=role is Role.EXEC,
    )
