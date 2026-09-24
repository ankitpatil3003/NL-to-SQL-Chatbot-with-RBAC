"""Knowledge store: keep the indexed corpus in sync with the code, and search it (hybrid).

Hybrid retrieval: dense vectors catch paraphrase ("free drug" ~ "patient assistance program"),
full-text search catches exact jargon ("340B", "R6M", "WAC"). Each returns a ranked list, and
Reciprocal Rank Fusion merges them without having to calibrate the two score scales.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.knowledge.chunker import CHUNKER_VERSION, Chunk
from app.knowledge.embedder import MODEL_NAME, Embedder

Kind = Literal["doc", "example"]
RRF_K = 60  # standard RRF constant: dampens the weight of the very top ranks
# Dense-dominant fusion, measured (tests/integration/test_fewshots_live.py, 18 paraphrased
# questions + 10 doc questions). Lexical weight sweep, recall@1 on examples: 0 -> 14/18,
# 0.25 -> 15/18, 0.5 -> 14/18, 1.0 (plain RRF) -> 12/18; docs 10/10 throughout. Small eval, so a
# directional result: keywords help as a light signal and hurt at equal weight (brand names like
# "Zenovax" match half the example bank).
DEFAULT_WEIGHTS = {"dense": 1.0, "lexical": 0.25}


@dataclass(frozen=True, slots=True)
class KbItem:
    item_id: str
    kind: Kind
    source: str
    title: str
    content: str
    embed_text: str  # what gets embedded (for examples: the question only)
    sql: str | None = None


def items_from_chunks(chunks: Sequence[Chunk]) -> list[KbItem]:
    return [
        KbItem(
            item_id=f"doc:{c.source}#{c.index}",
            kind="doc",
            source=c.source,
            title=c.title,
            content=c.text,
            embed_text=f"{c.title}\n{c.text}",
        )
        for c in chunks
    ]


def corpus_hash(items: Sequence[KbItem]) -> str:
    """Changes whenever anything that affects the index changes: content, chunking, or model."""
    payload = json.dumps(
        [MODEL_NAME, CHUNKER_VERSION]
        + [[i.item_id, i.title, i.content, i.embed_text, i.sql] for i in items],
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _vector_literal(vec: Sequence[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


async def sync_knowledge(engine: AsyncEngine, embedder: Embedder, items: Sequence[KbItem]) -> bool:
    """Rebuild app.kb_items if the corpus changed. Returns True if it rebuilt.

    An advisory lock serialises concurrent API replicas starting at once; the loser waits, then
    sees the new hash and does nothing.
    """
    digest = corpus_hash(items)
    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('app.kb_sync'))"))
        current = await conn.scalar(text("SELECT value FROM app.kb_meta WHERE key = 'corpus_hash'"))
        if current == digest:
            return False
        vectors = await embedder.passages([i.embed_text for i in items])
        await conn.execute(text("DELETE FROM app.kb_items"))
        await conn.execute(
            text(
                "INSERT INTO app.kb_items (item_id, kind, source, title, content, sql, embedding) "
                "VALUES (:item_id, :kind, :source, :title, :content, :sql, "
                "CAST(:embedding AS vector))"
            ),
            [
                {
                    "item_id": i.item_id,
                    "kind": i.kind,
                    "source": i.source,
                    "title": i.title,
                    "content": i.content,
                    "sql": i.sql,
                    "embedding": _vector_literal(v),
                }
                for i, v in zip(items, vectors, strict=True)
            ],
        )
        await conn.execute(
            text(
                "INSERT INTO app.kb_meta (key, value) VALUES ('corpus_hash', :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()"
            ),
            {"v": digest},
        )
    return True


@dataclass(slots=True)
class Hit:
    item_id: str
    title: str
    content: str
    sql: str | None
    score: float  # fused RRF score
    ranks: dict[str, int] = field(default_factory=dict)  # retriever -> 1-based rank (for traces)


def rrf_fuse(
    rankings: dict[str, list[str]], weights: dict[str, float] | None = None, k: int = RRF_K
) -> list[tuple[str, float, dict[str, int]]]:
    """Weighted Reciprocal Rank Fusion: score(d) = sum over retrievers of w / (k + rank)."""
    scores: dict[str, float] = {}
    ranks: dict[str, dict[str, int]] = {}
    for retriever, ids in rankings.items():
        weight = (weights or {}).get(retriever, 1.0)
        if weight <= 0:
            continue  # disabled retriever: contributes no candidates at all
        for rank, item_id in enumerate(ids, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + weight / (k + rank)
            ranks.setdefault(item_id, {})[retriever] = rank
    ordered = sorted(scores, key=lambda i: (-scores[i], i))
    return [(i, scores[i], ranks[i]) for i in ordered]


class HybridRetriever:
    def __init__(
        self,
        engine: AsyncEngine,
        embedder: Embedder,
        *,
        candidates: int = 20,
        weights: dict[str, float] | None = None,
    ) -> None:
        self._engine = engine
        self._embedder = embedder
        self._candidates = candidates
        self._weights = weights if weights is not None else DEFAULT_WEIGHTS

    async def search(self, query: str, kind: Kind, k: int) -> list[Hit]:
        vector = _vector_literal(await self._embedder.query(query))
        async with self._engine.connect() as conn:
            dense = await conn.execute(
                text(
                    "SELECT item_id FROM app.kb_items WHERE kind = :kind "
                    "ORDER BY embedding <=> CAST(:v AS vector) LIMIT :n"
                ),
                {"kind": kind, "v": vector, "n": self._candidates},
            )
            # OR over the query's stemmed lexemes: plainto/websearch_to_tsquery AND every word,
            # which almost never matches a natural-language question.
            lexical = await conn.execute(
                text(
                    "WITH q AS (SELECT to_tsquery('simple', array_to_string("
                    "  tsvector_to_array(to_tsvector('english', :query)), ' | ')) AS tsq) "
                    "SELECT item_id FROM app.kb_items, q "
                    "WHERE kind = :kind AND numnode(q.tsq) > 0 AND tsv @@ q.tsq "
                    "ORDER BY ts_rank_cd(tsv, q.tsq) DESC, item_id LIMIT :n"
                ),
                {"kind": kind, "query": query, "n": self._candidates},
            )
            fused = rrf_fuse(
                {"dense": [r[0] for r in dense.all()], "lexical": [r[0] for r in lexical.all()]},
                self._weights,
            )[:k]
            if not fused:
                return []
            rows = await conn.execute(
                text(
                    "SELECT item_id, title, content, sql FROM app.kb_items "
                    "WHERE item_id = ANY(:ids)"
                ),
                {"ids": [f[0] for f in fused]},
            )
            by_id = {r.item_id: r for r in rows}
        return [
            Hit(i, by_id[i].title, by_id[i].content, by_id[i].sql, score, ranks)
            for i, score, ranks in fused
        ]
