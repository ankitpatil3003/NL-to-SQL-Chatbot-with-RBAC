import pytest

from app.rbac.context import AccessDenied, Role, Scope, build_user_context


def row(**overrides: object) -> dict[str, object]:
    base = {
        "user_id": "U1",
        "email": "a@b.c",
        "full_name": "A B",
        "role": "ram",
        "territory_name": "New York Metro",
        "region_name": "Northeast",
        "can_view_wac": 0,
    }
    return base | overrides


def test_ram_is_scoped_to_territory_without_wac() -> None:
    ctx = build_user_context(row())
    assert ctx.role is Role.RAM
    assert ctx.scope == Scope("territory", "New York Metro")
    assert not ctx.can_view_wac


def test_director_is_scoped_to_region_without_wac() -> None:
    ctx = build_user_context(row(role="director", territory_name=None))
    assert ctx.scope == Scope("region", "Northeast")
    assert not ctx.can_view_wac


def test_exec_is_unrestricted_with_wac() -> None:
    exec_row = row(role="exec", territory_name=None, region_name=None, can_view_wac=1)
    ctx = build_user_context(exec_row)
    assert ctx.scope is None
    assert ctx.can_view_wac
    assert ctx.scope_label == "All territories and regions"


def test_non_exec_never_gets_wac_even_if_flag_set() -> None:
    assert not build_user_context(row(can_view_wac=1)).can_view_wac
    assert not build_user_context(row(role="director", can_view_wac=1)).can_view_wac


@pytest.mark.parametrize(
    "overrides",
    [
        {"role": "admin"},
        {"role": "ram", "territory_name": None},
        {"role": "ram", "territory_name": ""},
        {"role": "director", "region_name": None},
        {"role": "exec", "can_view_wac": 0},
    ],
)
def test_inconsistent_rows_fail_closed(overrides: dict[str, object]) -> None:
    with pytest.raises(AccessDenied):
        build_user_context(row(**overrides))
