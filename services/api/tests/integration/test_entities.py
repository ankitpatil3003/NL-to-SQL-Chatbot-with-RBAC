"""Entity resolution against real reference data, including the RBAC property: account lookups
go through the user's scoped executor, so out-of-scope organizations are never suggested."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text

from app.core.config import Settings
from app.db.engine import build_engine
from app.db.executor import QueryExecutor
from app.knowledge.contract import Catalog, load_catalog
from app.nl2sql.entities import resolve_mentions
from app.nl2sql.types import Mention

from ..unit.test_sqlguard import EXEC, RAM  # RAM = New York Metro


@pytest.fixture
async def ctx(settings: Settings) -> AsyncIterator[tuple[Catalog, QueryExecutor, dict[str, str]]]:
    engine = build_engine(settings)
    executor = QueryExecutor(settings)
    catalog = await load_catalog(engine)
    names = {}
    async with engine.connect() as conn:
        for territory in ("New York Metro", "Texas"):
            names[territory] = await conn.scalar(
                text(
                    "SELECT o.org_name FROM organizations o JOIN zip_territory z ON z.zip = o.zip "
                    "WHERE z.territory_name = :t AND o.org_type = 'Grandparent' "
                    "AND NOT EXISTS (SELECT 1 FROM organizations x JOIN zip_territory y ON y.zip = x.zip "
                    "  WHERE x.org_name = o.org_name AND y.territory_name <> :t) "
                    "ORDER BY o.org_name LIMIT 1"
                ),
                {"t": territory},
            )
    yield catalog, executor, names
    await executor.dispose()
    await engine.dispose()


async def test_catalogue_values_resolve_with_abbreviations_and_typos(ctx) -> None:  # type: ignore[no-untyped-def]
    catalog, executor, _ = ctx
    mentions = [
        Mention(kind="drug", text="zenovax"),
        Mention(kind="drug", text="Luprex"),
        Mention(kind="territory", text="NY metro"),
        Mention(kind="gpo", text="vital source"),
        Mention(kind="market", text="platinum compounds"),
        Mention(kind="drug", text="carbotrell"),  # typo
    ]
    got = {r.mention: r.values for r in await resolve_mentions(mentions, catalog, executor, EXEC)}
    assert got == {
        "zenovax": ("ZENOVAX",),
        "Luprex": ("LUPREX DEPOT",),
        "NY metro": ("New York Metro",),
        "vital source": ("VitalSource",),
        "platinum compounds": ("Platinum Compounds",),
        "carbotrell": ("CARBOTREL",),
    }


async def test_out_of_scope_geography_is_flagged_for_scoped_users(ctx) -> None:  # type: ignore[no-untyped-def]
    catalog, executor, _ = ctx
    mentions = [Mention(kind="territory", text="Texas"), Mention(kind="territory", text="NY Metro")]
    ram = {
        r.mention: r.outside_scope for r in await resolve_mentions(mentions, catalog, executor, RAM)
    }
    exe = {
        r.mention: r.outside_scope
        for r in await resolve_mentions(mentions, catalog, executor, EXEC)
    }
    assert ram == {"Texas": True, "NY Metro": False}
    assert exe == {"Texas": False, "NY Metro": False}


async def test_account_lookup_respects_scope_and_ignores_generic_phrases(ctx) -> None:  # type: ignore[no-untyped-def]
    catalog, executor, names = ctx
    ny, tx = names["New York Metro"], names["Texas"]
    mentions = [Mention(kind="account", text=ny), Mention(kind="account", text=tx),
                Mention(kind="account", text="top 5 accounts")]  # fmt: skip
    exe = {r.mention: r.values for r in await resolve_mentions(mentions, catalog, executor, EXEC)}
    ram = {r.mention: r.values for r in await resolve_mentions(mentions, catalog, executor, RAM)}
    assert ny in exe[ny] and tx in exe[tx] and "top 5 accounts" not in exe
    assert ny in ram[ny]
    assert tx not in ram  # no hint at all: neither the real name nor a misleading in-scope one
