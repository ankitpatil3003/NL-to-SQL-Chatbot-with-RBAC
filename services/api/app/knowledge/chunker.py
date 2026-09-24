"""Split the markdown business docs into retrieval chunks along their heading structure.

A chunk is one `##` section (with its `###` subsections) and carries its heading path
("Metric Definitions > Market Share") so it reads sensibly out of context. Oversized sections
split at `###`; tiny adjacent sections merge, so no chunk is a lone heading.
"""

from dataclasses import dataclass
from pathlib import Path

CHUNKER_VERSION = "1"  # part of the corpus hash: bump when chunking changes
MAX_CHARS = 1800
MIN_CHARS = 250


@dataclass(frozen=True, slots=True)
class Chunk:
    source: str  # file name
    index: int
    title: str  # "Doc Title > Section"
    text: str


def _split(lines: list[str], marker: str) -> list[tuple[str, list[str]]]:
    """[(heading, body_lines)] split on lines starting with `marker`; text before the first
    heading gets heading ''."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in lines:
        if line.startswith(marker):
            sections.append((line[len(marker) :].strip(), []))
        else:
            sections[-1][1].append(line)
    return [(h, body) for h, body in sections if h or "".join(body).strip()]


def chunk_markdown(source: str, markdown: str) -> list[Chunk]:
    lines = markdown.splitlines()
    doc_title = next((ln[2:].strip() for ln in lines if ln.startswith("# ")), Path(source).stem)
    body = [ln for ln in lines if not ln.startswith("# ")]

    pieces: list[tuple[str, str]] = []
    for heading, section in _split(body, "## "):
        text = "\n".join(section).strip()
        if len(text) <= MAX_CHARS:
            pieces.append((heading, text))
            continue
        for sub, sub_lines in _split(section, "### "):
            label = f"{heading} > {sub}" if sub else heading
            pieces.append((label, "\n".join(sub_lines).strip()))

    merged: list[tuple[str, str]] = []
    for heading, text in pieces:
        if merged and len(merged[-1][1]) < MIN_CHARS:
            prev_heading, prev_text = merged.pop()
            joined_heading = " / ".join(h for h in (prev_heading, heading) if h)
            merged.append((joined_heading, f"{prev_text}\n\n### {heading}\n{text}".strip()))
        else:
            merged.append((heading, text))

    return [
        Chunk(source, i, f"{doc_title} > {heading}" if heading else doc_title, text)
        for i, (heading, text) in enumerate(merged)
        if text
    ]


def chunk_docs(docs_dir: Path) -> list[Chunk]:
    return [
        chunk
        for path in sorted(docs_dir.glob("*.md"))
        for chunk in chunk_markdown(path.name, path.read_text(encoding="utf-8"))
    ]
