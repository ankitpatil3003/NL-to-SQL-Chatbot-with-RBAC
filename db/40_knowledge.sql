-- Retrieval corpus for the NL-to-SQL prompt: doc chunks and curated NL->SQL examples, each with a
-- dense embedding (pgvector) and a full-text vector, searched together and fused with RRF
-- (services/api/app/knowledge/store.py). Rebuilt by the API at startup whenever the corpus hash
-- changes, so what's indexed always matches the deployed code.
--
-- vector(384) = BAAI/bge-small-en-v1.5. Changing the embedding model to another dimension needs a
-- migration. No ANN index: ~100 rows, so an exact scan is faster and has perfect recall.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS app.kb_items (
    item_id     TEXT PRIMARY KEY,                 -- e.g. 'doc:metric_definitions.md#3', 'example:ms-by-territory'
    kind        TEXT NOT NULL CHECK (kind IN ('doc', 'example')),
    source      TEXT NOT NULL,                    -- file the item came from
    title       TEXT NOT NULL,                    -- heading path, or the example question
    content     TEXT NOT NULL,                    -- chunk text, or question + tags for examples
    sql         TEXT,                             -- examples only
    embedding   vector(384) NOT NULL,
    tsv         tsvector GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || content)) STORED
);
CREATE INDEX IF NOT EXISTS ix_kb_items_tsv ON app.kb_items USING GIN (tsv);

CREATE TABLE IF NOT EXISTS app.kb_meta (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
