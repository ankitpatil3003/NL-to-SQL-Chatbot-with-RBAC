"""Load, validate and render the semantic contract (semantic_contract.yaml).

The rendered contract is the always-on domain context for SQL generation:
  * block 1 (cacheable, identical for every user): schema, joins, rules, output conventions, and a
    catalogue of real values (brands, markets, territories, GPOs) read from the database;
  * block 2 (per user, never cached): the user's data scope and WAC permission.
Its version is a content hash, so every trace records exactly which rules the model saw.
"""

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.llm.base import SystemBlock
from app.rbac.context import UserContext

CONTRACT_PATH = Path(__file__).with_name("semantic_contract.yaml")


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    rule: str
    sql: str | None = None


class TableSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grain: str
    columns: dict[str, str]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    data: dict[str, str]
    tables: dict[str, TableSpec]
    joins: list[str]
    rules: list[Rule]
    output: list[str]
    content_hash: str = ""

    def rule(self, rule_id: str) -> Rule:
        return next(r for r in self.rules if r.id == rule_id)


@lru_cache
def load_contract(path: Path = CONTRACT_PATH) -> Contract:
    raw = path.read_bytes()
    contract = Contract.model_validate(yaml.safe_load(raw))
    ids = [r.id for r in contract.rules]
    if len(ids) != len(set(ids)):
        raise ValueError("semantic contract has duplicate rule ids")
    contract.content_hash = hashlib.sha256(raw).hexdigest()[:12]
    return contract


@dataclass(frozen=True, slots=True)
class Catalog:
    """Real values from reference data, so the model uses exact spellings ('LUPREX DEPOT',
    'New York Metro') instead of guessing. Loaded once at startup."""

    products: list[
        tuple[str, int, str, str, str]
    ]  # drug_name, brand_flag, specialty, category, subcategory
    territories: list[tuple[str, str]]  # territory_name, region_name
    gpos: list[str]
    archetypes: list[str]


async def load_catalog(engine: AsyncEngine) -> Catalog:
    async with engine.connect() as conn:
        products = await conn.execute(
            text(
                "SELECT DISTINCT drug_name, brand_flag, specialty, market_category, "
                "market_subcategory FROM products "
                "ORDER BY brand_flag DESC, market_category, drug_name"
            )
        )
        territories = await conn.execute(
            text(
                "SELECT DISTINCT territory_name, region_name FROM zip_territory "
                "ORDER BY region_name, territory_name"
            )
        )
        gpos = await conn.execute(
            text(
                "SELECT DISTINCT gpo_name FROM organizations WHERE gpo_name IS NOT NULL ORDER BY 1"
            )
        )
        archetypes = await conn.execute(
            text(
                "SELECT DISTINCT org_archetype FROM organizations "
                "WHERE org_archetype IS NOT NULL ORDER BY 1"
            )
        )
        return Catalog(
            products=[tuple(r) for r in products.all()],
            territories=[tuple(r) for r in territories.all()],
            gpos=[r[0] for r in gpos.all()],
            archetypes=[r[0] for r in archetypes.all()],
        )


def render_contract(contract: Contract, catalog: Catalog) -> str:
    out: list[str] = [
        f"# Data model (semantic contract v{contract.version}-{contract.content_hash})"
    ]
    out += [f"- {v}" for v in contract.data.values()]
    out.append("\n## Tables")
    for name, spec in contract.tables.items():
        out.append(f"### {name} ({spec.grain})")
        out += [f"- {col}: {desc}" for col, desc in spec.columns.items()]
    out.append("\n## Joins")
    out += [f"- {j}" for j in contract.joins]
    out.append("\n## Business rules (cite ids in `rules_applied`)")
    for r in contract.rules:
        out.append(f"- [{r.id}] {r.rule}")
        if r.sql:
            out.append(f"  Example:\n```sql\n{r.sql.strip()}\n```")
    out.append("\n## Catalogue (exact values in the data)")
    nova = [p for p in catalog.products if p[1] == 1]
    others = [p for p in catalog.products if p[1] == 0]
    out.append(
        "- NovaPharma brands (brand_flag = 1): "
        + "; ".join(f"{d} ({sub}, {cat}, {spec})" for d, _, spec, cat, sub in nova)
    )
    by_market: dict[str, list[str]] = {}
    for d, _, _, cat, sub in others:
        by_market.setdefault(f"{cat} / {sub}", []).append(d)
    out.append(
        "- Competitor products by market: "
        + "; ".join(f"{m}: {', '.join(ds)}" for m, ds in by_market.items())
    )
    regions: dict[str, list[str]] = {}
    for terr, region in catalog.territories:
        regions.setdefault(region, []).append(terr)
    out.append(
        "- Regions and territories: "
        + "; ".join(f"{r}: {', '.join(t)}" for r, t in regions.items())
    )
    out.append(f"- GPOs: {', '.join(catalog.gpos)}")
    out.append(f"- Organization archetypes: {', '.join(catalog.archetypes)}")
    out.append("\n## Output conventions")
    out += [f"- {o}" for o in contract.output]
    return "\n".join(out)


def render_user_scope(user: UserContext) -> str:
    wac = (
        # docs/security_model.md scenario 3: an Exec asking for "total sales" sees pricing.
        # Measured: without this the model copied the units-only example (eval 20260924-182739).
        "This user MAY see WAC (dollar) figures: for sales or revenue totals, report both "
        "dollars (SUM(wac), M-3) and units."
        if user.can_view_wac
        else "This user may NOT see WAC: never reference the wac column; use volume (SEC-1)."
    )
    return (
        f"# Current user\n- {user.full_name}, role: {user.role.value}\n"
        f"- Data scope: {user.scope_label} (enforced by the database; SEC-2)\n- {wac}"
    )


def contract_blocks(contract: Contract, catalog: Catalog, user: UserContext) -> list[SystemBlock]:
    return [
        SystemBlock(render_contract(contract, catalog), cache=True),
        SystemBlock(render_user_scope(user)),
    ]
