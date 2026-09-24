"""Local sentence embeddings (fastembed / ONNX Runtime on CPU): no API key, no per-call cost,
deterministic in tests. bge models embed queries and passages differently (query_embed adds the
retrieval instruction), so the two entry points are kept distinct."""

import asyncio
from collections.abc import Sequence

from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384  # must match vector(384) in db/40_knowledge.sql


class Embedder:
    def __init__(self, cache_dir: str | None = None) -> None:
        self._model = TextEmbedding(MODEL_NAME, cache_dir=cache_dir)

    async def passages(self, texts: Sequence[str]) -> list[list[float]]:
        return await asyncio.to_thread(
            lambda: [v.tolist() for v in self._model.passage_embed(list(texts))]
        )

    async def query(self, text: str) -> list[float]:
        return await asyncio.to_thread(lambda: next(iter(self._model.query_embed([text]))).tolist())
