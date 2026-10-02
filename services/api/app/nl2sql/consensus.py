"""Self-consistency: several independently generated SQL candidates, executed, then compared.

Agreement between candidates that differ in model or sampling is strong evidence that the answer
doesn't hinge on one model's misreading. Disagreement is exactly the case worth showing a human:
each distinct result is a different interpretation of the question.
"""

from dataclasses import dataclass, field
from typing import Literal

from app.nl2sql.compare import same_result
from app.nl2sql.types import ResultTable, SqlDraft
from app.sqlguard.guard import GuardedQuery

# (LLM task, temperature) per candidate: the primary model greedy, the same model sampled, and a
# second model family ("sql_cross" falls back to the SQL chain when no LLM_CHAIN_SQL_CROSS is set).
CANDIDATE_SPECS: list[tuple[str, float]] = [("sql", 0.0), ("sql", 0.7), ("sql_cross", 0.0)]

Agreement = Literal["unanimous", "majority", "split", "single", "none"]


@dataclass(slots=True)
class Candidate:
    task: str
    temperature: float
    draft: SqlDraft | None = None
    guarded: GuardedQuery | None = None
    table: ResultTable | None = None
    attempts: int = 0
    cost_usd: float = 0.0

    @property
    def answerable(self) -> bool:
        return self.draft is not None and self.draft.answerable

    @property
    def succeeded(self) -> bool:
        return self.table is not None and self.guarded is not None


@dataclass(slots=True)
class Consensus:
    agreement: Agreement
    groups: list[list[int]] = field(default_factory=list)  # candidate indexes, largest first
    chosen: int | None = None  # None: no candidate produced a result


def _key(c: Candidate) -> str:
    """Candidates that didn't run a query vote by what they concluded."""
    return "unanswerable" if c.draft is not None and not c.draft.answerable else "failed"


def reconcile(candidates: list[Candidate]) -> Consensus:
    """Group candidates whose results agree. A strict majority wins; otherwise it's a split, and
    the primary candidate (index 0) is the default pick."""
    groups: list[list[int]] = []
    for i, c in enumerate(candidates):
        if not c.succeeded:
            continue
        assert c.table is not None
        for g in groups:
            rep = candidates[g[0]].table
            assert rep is not None
            if rep.row_count == c.table.row_count and same_result(rep.rows, c.table.rows):
                g.append(i)
                break
        else:
            groups.append([i])
    groups.sort(key=lambda g: (-len(g), g[0]))
    if not groups:
        # nothing ran: the "unanswerable" vote decides only if it's the majority conclusion
        votes = [_key(c) for c in candidates]
        unanswerable = [i for i, v in enumerate(votes) if v == "unanswerable"]
        return Consensus("none", [unanswerable] if unanswerable else [], None)
    succeeded = sum(len(g) for g in groups)
    if succeeded == 1:
        return Consensus("single", groups, groups[0][0])
    if len(groups) == 1:
        return Consensus("unanimous", groups, groups[0][0])
    if len(groups[0]) * 2 > succeeded:
        return Consensus("majority", groups, groups[0][0])
    primary = next((g[0] for g in groups if 0 in g), groups[0][0])
    return Consensus("split", groups, primary)
