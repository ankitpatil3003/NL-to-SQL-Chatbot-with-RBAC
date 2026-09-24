"""The assembled knowledge layer the NL-to-SQL pipeline depends on."""

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.knowledge.chunker import chunk_docs
from app.knowledge.contract import Catalog, Contract, load_catalog, load_contract
from app.knowledge.embedder import Embedder
from app.knowledge.fewshots import items_from_examples, load_examples
from app.knowledge.store import HybridRetriever, KbItem, items_from_chunks, sync_knowledge

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class KnowledgeBase:
    contract: Contract
    catalog: Catalog
    retriever: HybridRetriever


@lru_cache
def get_embedder(cache_dir: str | None) -> Embedder:
    """One ONNX model per process (loading takes seconds; tests build many apps)."""
    return Embedder(cache_dir)


def corpus_items(docs_dir: Path) -> list[KbItem]:
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"knowledge docs directory not found: {docs_dir}")
    return items_from_chunks(chunk_docs(docs_dir)) + items_from_examples(load_examples())


async def init_knowledge(
    engine: AsyncEngine, docs_dir: Path, embed_cache_dir: str | None
) -> KnowledgeBase | None:
    """Load the contract, sync the retrieval index, read the catalogue. Returns None (and logs)
    on failure: the API keeps serving auth/history/health and readiness shows the database."""
    try:
        contract = load_contract()
        embedder = get_embedder(embed_cache_dir)
        items = corpus_items(docs_dir)
        if await sync_knowledge(engine, embedder, items):
            log.info("knowledge index rebuilt: %d items", len(items))
        catalog = await load_catalog(engine)
    except Exception:
        log.exception("knowledge layer unavailable; the assistant is disabled until restart")
        return None
    return KnowledgeBase(contract, catalog, HybridRetriever(engine, embedder))
