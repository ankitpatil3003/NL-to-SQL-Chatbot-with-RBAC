"""Examples are executable: each passes the guard and runs on the full data. Plus role-aware
selection and a paraphrase retrieval eval (with a dense / lexical / hybrid ablation)."""

from collections.abc import AsyncIterator

import pytest

from app.core.config import Settings
from app.db.engine import build_engine
from app.db.executor import QueryExecutor
from app.knowledge.base import corpus_items, get_embedder
from app.knowledge.fewshots import Example, load_examples, select_examples
from app.knowledge.store import HybridRetriever, sync_knowledge
from app.sqlguard.guard import guard

from ..unit.test_sqlguard import EXEC, RAM

EXAMPLES = load_examples()


@pytest.fixture
async def executor(settings: Settings) -> AsyncIterator[QueryExecutor]:
    ex = QueryExecutor(settings)
    yield ex
    await ex.dispose()


@pytest.fixture
async def retriever(settings: Settings) -> AsyncIterator[HybridRetriever]:
    engine = build_engine(settings)
    embedder = get_embedder(settings.embed_cache_dir)
    await sync_knowledge(engine, embedder, corpus_items(settings.knowledge_docs_dir))
    yield HybridRetriever(engine, embedder)
    await engine.dispose()


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.id)
async def test_example_runs_for_exec_and_returns_data(
    executor: QueryExecutor, example: Example
) -> None:
    result = await executor.run(EXEC, guard(example.sql, EXEC, max_rows=1000).sql)
    assert result.rows, example.id


@pytest.mark.parametrize("example", [e for e in EXAMPLES if not e.exec_only], ids=lambda e: e.id)
async def test_example_runs_for_scoped_user(executor: QueryExecutor, example: Example) -> None:
    await executor.run(RAM, guard(example.sql, RAM, max_rows=1000).sql)  # may be empty in-scope


async def test_non_exec_users_never_get_wac_examples(retriever: HybridRetriever) -> None:
    question = "what is our total revenue in dollars by product"
    ram = await select_examples(retriever, question, RAM, k=4)
    exe = await select_examples(retriever, question, EXEC, k=4)
    assert ram and not any(s.example.exec_only for s in ram)
    assert any(s.example.exec_only for s in exe)


# Paraphrases (not copies) of example questions -> the example that should be retrieved.
PARAPHRASES = {
    "biggest ten customers by units in Q3": "top-accounts-quarter",
    "accounts whose volume dropped over 20 percent from the previous quarter": "accounts-declining-qoq",
    "order the territories by how much NovaPharma product they move": "rank-territories",
    "independent sites with no parent organization and their units": "standalone-facilities",
    "units broken out by group purchasing organization": "volume-by-gpo",
    "how much of our volume is from 340B covered entities, as a percent": "share-340b",
    "which customers get a lot of patient assistance free goods relative to their total": "hub-heavy-accounts",
    "Zenovax share of the docetaxel market": "market-share-product",
    "quarterly Carbotrel share over the past year": "share-trend-quarters",
    "territories where Gemtara share is under the average": "share-below-average-territories",
    "Zenovax 80mg versus 20mg vials": "strength-split",
    "how much Gemtara goes out as free drug percentage-wise": "hub-pct-product",
    "size of the alkylating agents market": "market-size-category",
    "top five states for Oncosetron": "top-states-product",
    "annual growth for each of our brands": "yoy-growth-products",
    "3 month moving average of Paxelium units": "rolling-3m-average",
    "accounts losing docetaxel share recently, weighted by size": "account-share-trend-weighted",
    "how many facilities does each IDN have": "facilities-per-system",
}


async def recall_at(
    retriever: HybridRetriever, k: int
) -> tuple[float, list[tuple[str, str, list[str]]]]:
    misses = []
    for question, expected in PARAPHRASES.items():
        hits = await retriever.search(question, "example", k=k)
        if f"example:{expected}" not in [h.item_id for h in hits]:
            misses.append((question, expected, [h.item_id for h in hits]))
    return 1 - len(misses) / len(PARAPHRASES), misses


async def test_example_retrieval_recall_and_ablation(
    settings: Settings, retriever: HybridRetriever
) -> None:
    engine = build_engine(settings)
    embedder = get_embedder(settings.embed_cache_dir)
    arms = {
        "dense": HybridRetriever(engine, embedder, weights={"dense": 1.0, "lexical": 0.0}),
        "lexical": HybridRetriever(engine, embedder, weights={"dense": 0.0, "lexical": 1.0}),
        "equal_rrf": HybridRetriever(engine, embedder, weights={"dense": 1.0, "lexical": 1.0}),
        "hybrid": retriever,  # production default weights
    }
    scores = {}
    for name, arm in arms.items():
        scores[name], misses = await recall_at(arm, k=4)
        if name == "hybrid":
            hybrid_misses = misses
    await engine.dispose()
    print(f"\nexample recall@4: {scores}; hybrid misses: {hybrid_misses}")
    assert scores["hybrid"] >= 0.85, hybrid_misses
    assert scores["hybrid"] >= scores["equal_rrf"]
