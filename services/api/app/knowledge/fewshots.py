"""Curated NL->SQL examples (fewshots.yaml): loading, indexing and role-aware selection."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from app.knowledge.store import HybridRetriever, KbItem
from app.rbac.context import UserContext

EXAMPLES_PATH = Path(__file__).with_name("fewshots.yaml")


class Example(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    question: str
    sql: str
    rules: list[str]
    exec_only: bool = False  # uses wac: never shown to users without WAC access

    @property
    def item_id(self) -> str:
        return f"example:{self.id}"


@lru_cache
def load_examples(path: Path = EXAMPLES_PATH) -> tuple[Example, ...]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    examples = tuple(Example.model_validate(e) for e in raw["examples"])
    ids = [e.id for e in examples]
    if len(ids) != len(set(ids)):
        raise ValueError("fewshots.yaml has duplicate example ids")
    return examples


def items_from_examples(examples: tuple[Example, ...]) -> list[KbItem]:
    # Embed the question only: we match the user's question to similar questions, not to SQL.
    return [
        KbItem(
            item_id=e.item_id,
            kind="example",
            source=EXAMPLES_PATH.name,
            title=e.question,
            content=f"{e.question} ({', '.join(e.rules)})",
            embed_text=e.question,
            sql=e.sql.strip(),
        )
        for e in examples
    ]


@dataclass(frozen=True, slots=True)
class SelectedExample:
    example: Example
    score: float
    ranks: dict[str, int]


async def select_examples(
    retriever: HybridRetriever, question: str, user: UserContext, k: int = 4
) -> list[SelectedExample]:
    """Top-k similar examples the user is allowed to see. Over-fetch, then drop exec-only ones
    for non-Exec users, so they never see a wac pattern they must not use."""
    by_id = {e.item_id: e for e in load_examples()}
    hits = await retriever.search(question, "example", k=k * 2)
    allowed = [
        SelectedExample(by_id[h.item_id], h.score, h.ranks)
        for h in hits
        if h.item_id in by_id and (user.can_view_wac or not by_id[h.item_id].exec_only)
    ]
    return allowed[:k]
