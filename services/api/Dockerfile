# syntax=docker/dockerfile:1.7
# Build context: the repository root (the API needs docs/ for the knowledge index).
#   docker build -f services/api/Dockerfile .
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /srv

# Dependencies first for layer caching.
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
ENV PATH="/srv/.venv/bin:$PATH"

# Bake the embedding model into the image: no download on cold start, works without egress.
ENV EMBED_CACHE_DIR=/srv/models
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/srv/models')"

COPY services/api/app ./app
COPY docs ./docs
ENV KNOWLEDGE_DOCS_DIR=/srv/docs

RUN useradd --system --uid 10001 api && chown -R api /srv
USER api
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
