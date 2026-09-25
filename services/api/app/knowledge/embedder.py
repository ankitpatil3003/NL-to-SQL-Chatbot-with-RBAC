"""Local sentence embeddings (fastembed / ONNX Runtime on CPU): no API key, no per-call cost,
deterministic in tests. bge models embed queries and passages differently (query_embed adds the
retrieval instruction), so the two entry points are kept distinct."""

import asyncio
from collections.abc import Sequence

from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384  # must match vector(384) in db/40_knowledge.sql
# fastembed's default batch (256) pads the whole corpus to its longest chunk in one ONNX run: the
# attention buffers alone need several GB, which OOM-killed the 1 GB API task on first start. The
# ~80-item corpus at 8 per batch peaks at ~480 MB (measured in a 1 GB container).
BATCH_SIZE = 8


class Embedder:
    def __init__(self, cache_dir: str | None = None) -> None:
        self._model = TextEmbedding(MODEL_NAME, cache_dir=cache_dir)

    async def passages(self, texts: Sequence[str]) -> list[list[float]]:
        return await asyncio.to_thread(
            lambda: [
                v.tolist() for v in self._model.passage_embed(list(texts), batch_size=BATCH_SIZE)
            ]
        )

    async def query(self, text: str) -> list[float]:
        return await asyncio.to_thread(lambda: next(iter(self._model.query_embed([text]))).tolist())
