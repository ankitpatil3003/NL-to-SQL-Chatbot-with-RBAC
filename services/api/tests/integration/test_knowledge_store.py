"""Knowledge index sync + a small retrieval eval (recall@3 over hand-labelled questions)."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.db.engine import build_engine
from app.knowledge.base import corpus_items, get_embedder
from app.knowledge.store import HybridRetriever, sync_knowledge

# question -> doc(s) that answer it (paraphrased on purpose; not keyword copies). Market share for
# a named market is defined in metric_definitions and worked through in market_classification.
LABELLED: dict[str, str | set[str]] = {
    "how do we calculate our share of the docetaxel market": {
        "metric_definitions.md",
        "market_classification.md",
    },
    "does free drug from the patient assistance program count as a sale": "data_source_guide.md",
    "what filter should I use for the prior three months comparison window": "period_offsets.md",
    "roll facilities up to their health system": "org_hierarchy.md",
    "which competitor drugs are in the same class as Gemtara": "market_classification.md",
    "can a regional account manager see pricing data": "security_model.md",
    "what are typical questions about 340B accounts": "account_analytics.md",
    "questions about dosing strengths and NDC level volume": "product_analytics.md",
    "WAC revenue for directors": "security_model.md",
    "R3M vs R6M weighted trend": "metric_definitions.md",
}


@pytest.fixture
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    e = build_engine(settings)
    yield e
    await e.dispose()


@pytest.fixture
async def retriever(engine: AsyncEngine, settings: Settings) -> HybridRetriever:
    embedder = get_embedder(settings.embed_cache_dir)
    await sync_knowledge(engine, embedder, corpus_items(settings.knowledge_docs_dir))
    return HybridRetriever(engine, embedder)


async def test_sync_is_idempotent(
    engine: AsyncEngine, settings: Settings, retriever: HybridRetriever
) -> None:
    items = corpus_items(settings.knowledge_docs_dir)
    assert await sync_knowledge(engine, get_embedder(settings.embed_cache_dir), items) is False
    async with engine.connect() as conn:
        assert await conn.scalar(text("SELECT count(*) FROM app.kb_items")) == len(items)


async def test_retrieval_recall_at_3(retriever: HybridRetriever) -> None:
    misses = []
    for question, expected in LABELLED.items():
        hits = await retriever.search(question, "doc", k=3)
        found = {h.item_id.split(":")[1].split("#")[0] for h in hits}
        if not found & (expected if isinstance(expected, set) else {expected}):
            misses.append((question, expected, [h.item_id for h in hits]))
    recall = 1 - len(misses) / len(LABELLED)
    print(f"\nrecall@3 = {recall:.0%}; misses: {misses}")
    assert recall >= 0.9, misses


async def test_hits_record_which_retrievers_found_them(retriever: HybridRetriever) -> None:
    hits = await retriever.search("340B covered entity volume", "doc", k=5)
    assert hits and all(h.ranks for h in hits)
    assert any("lexical" in h.ranks for h in hits)  # exact jargon should hit full-text search
