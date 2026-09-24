"""Prompt templates are code: versioned files, hashed into every trace (PROMPT_VERSION)."""

import hashlib
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache
def prompt(name: str) -> str:
    return (_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


@lru_cache
def prompts_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(_DIR.glob("*.md")):
        digest.update(path.name.encode() + path.read_bytes())
    return digest.hexdigest()[:8]
