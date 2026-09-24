"""Stage 3, entity resolution (deterministic): map the user's wording to exact values in the data.

"zenovax" -> drug_name = 'ZENOVAX', "NY metro" -> territory_name = 'New York Metro', "Memorial" ->
the matching organization names. The hints go into the SQL prompt so the model doesn't guess
spellings. Unmatched mentions produce no hint: a wrong hint is worse than none.

Account names are looked up *through the user's scoped executor*, so a RAM's prompt can only ever
contain organizations from their own territory; the owner connection would leak names outside it.
"""

import difflib
import re
from dataclasses import dataclass

from app.db.executor import QueryExecutor
from app.knowledge.contract import Catalog
from app.nl2sql.types import Mention
from app.rbac.context import UserContext

FUZZY_CUTOFF = 0.75  # difflib ratio for catalogue values (drugs, territories, ...)
TOKEN_MATCH = 0.8  # per-word difflib ratio for organization names, tolerating small typos

ABBREVIATIONS = {"ny": "new york", "nyc": "new york", "ne": "new england", "ca": "california"}

ACCOUNT_LOOKUP = """
    SELECT org_name, similarity(org_name, :q) AS score
    FROM organizations
    WHERE org_name % :q OR org_name ILIKE ANY(:patterns)
    ORDER BY score DESC, org_name
    LIMIT 15
"""

# Words that appear in hundreds of organization names and so identify nothing on their own.
# Whole-string trigram similarity can't separate right from wrong matches: measured on the data,
# "goldcrest" -> "Goldcrest Cancer Center" scores 0.45 while "maple health alliance" ->
# "Alliance Health Alliance" scores 0.73. So a candidate must contain every *distinctive* word.
_GENERIC_ORG_WORDS = (
    "health healthcare medical group system systems network networks alliance partners center "
    "centers cancer clinic clinics hospital hospitals services care oncology urology associates "
    "institute infusion pharmacy specialists community regional the of and inc llc account "
    "accounts customer customers idn top my our"
)
GENERIC_ORG_WORDS = frozenset(_GENERIC_ORG_WORDS.split())


@dataclass(frozen=True, slots=True)
class Resolution:
    mention: str
    kind: str
    column: str
    values: tuple[str, ...]
    score: float
    outside_scope: bool = False

    def hint(self) -> str:
        values = ", ".join(f"'{v}'" for v in self.values)
        if len(self.values) > 1:
            line = f'- "{self.mention}" ({self.kind}) -> matching {self.column} values: {values}'
        else:
            line = f'- "{self.mention}" ({self.kind}) -> {self.column} = {values}'
        if self.outside_scope:
            line += " [outside this user's data scope; the database will return nothing for it]"
        return line


def _normalise(text: str) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()
    return " ".join(ABBREVIATIONS.get(w, w) for w in words)


def _best(text: str, candidates: list[str]) -> tuple[str, float] | None:
    """Exact (case-insensitive), then unique containment, then fuzzy."""
    norm = _normalise(text)
    by_norm = {_normalise(c): c for c in candidates}
    if norm in by_norm:
        return by_norm[norm], 1.0
    contained = [c for n, c in by_norm.items() if norm and (norm in n or n in norm)]
    if len(contained) == 1:
        return contained[0], 0.9
    match = difflib.get_close_matches(norm, list(by_norm), n=1, cutoff=FUZZY_CUTOFF)
    if match:
        return by_norm[match[0]], difflib.SequenceMatcher(None, norm, match[0]).ratio()
    return None


def _distinctive_words(text: str) -> list[str]:
    return [w for w in _normalise(text).split() if w not in GENERIC_ORG_WORDS and len(w) > 2]


def _contains_all(name: str, words: list[str]) -> bool:
    name_words = _normalise(name).split()
    return all(
        any(difflib.SequenceMatcher(None, w, n).ratio() >= TOKEN_MATCH for n in name_words)
        for w in words
    )


def _in_scope(user: UserContext, territory: str | None, region: str | None) -> bool:
    if user.scope is None:
        return True
    if user.scope.level == "region":
        return region == user.scope.value
    return territory == user.scope.value if territory else region == user.region


async def _resolve_account(
    text: str, executor: QueryExecutor, user: UserContext
) -> Resolution | None:
    distinct = _distinctive_words(text)
    if not distinct:  # "top 5 accounts", "our health systems": nothing to look up
        return None
    params = {"q": text, "patterns": [f"%{w}%" for w in distinct]}
    rows = (await executor.run(user, ACCOUNT_LOOKUP, params)).rows
    names = [r[0] for r in rows if _contains_all(r[0], distinct)][:3]
    if not names:
        return None
    return Resolution(text, "account", "organizations.org_name", tuple(names), 1.0)


async def resolve_mentions(
    mentions: list[Mention], catalog: Catalog, executor: QueryExecutor, user: UserContext
) -> list[Resolution]:
    drugs = sorted({p[0] for p in catalog.products})
    categories = {p[3] for p in catalog.products}
    markets = sorted(categories | {p[4] for p in catalog.products})
    territories = dict(catalog.territories)
    regions = sorted(set(territories.values()))

    out: list[Resolution] = []
    for m in mentions:
        text = m.text.strip()
        if not text:
            continue
        found: Resolution | None = None
        if m.kind in ("drug", "market", "other"):
            if hit := _best(text, drugs):
                found = Resolution(text, "drug", "drug_name", (hit[0],), hit[1])
            elif hit := _best(text, markets):
                column = "market_category" if hit[0] in categories else "market_subcategory"
                found = Resolution(text, "market", f"products.{column}", (hit[0],), hit[1])
        if not found and m.kind in ("territory", "region", "other"):
            if hit := _best(text, list(territories)):
                outside = not _in_scope(user, hit[0], territories[hit[0]])
                found = Resolution(
                    text, "territory", "zip_territory.territory_name", (hit[0],), hit[1], outside
                )
            elif hit := _best(text, regions):
                outside = not _in_scope(user, None, hit[0])
                found = Resolution(
                    text, "region", "zip_territory.region_name", (hit[0],), hit[1], outside
                )
        if not found and m.kind in ("gpo", "other") and (hit := _best(text, catalog.gpos)):
            found = Resolution(text, "gpo", "organizations.gpo_name", (hit[0],), hit[1])
        if not found and m.kind == "account":
            found = await _resolve_account(text, executor, user)
        if found:
            out.append(found)
    return out
