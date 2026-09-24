from app.core.config import Settings
from app.knowledge.chunker import MAX_CHARS, chunk_docs, chunk_markdown
from app.knowledge.store import rrf_fuse

DOCS = Settings().knowledge_docs_dir


def test_every_doc_chunks_without_losing_content() -> None:
    chunks = chunk_docs(DOCS)
    sources = {c.source for c in chunks}
    assert sources == {p.name for p in DOCS.glob("*.md")} and len(sources) == 8
    for path in DOCS.glob("*.md"):
        original = set(path.read_text(encoding="utf-8").split())
        mine = [c for c in chunks if c.source == path.name]
        kept = set(" ".join(f"{c.title} {c.text}" for c in mine).split())
        # every word survives (headings move into titles, '#' markers may be dropped)
        assert {w for w in original - kept if not set(w) <= {"#"}} == set(), path.name


def test_chunks_are_bounded_and_carry_their_heading_path() -> None:
    chunks = chunk_docs(DOCS)
    assert all(len(c.text) <= MAX_CHARS * 1.5 for c in chunks)
    ms = [c for c in chunks if c.source == "metric_definitions.md"]
    assert any(c.title == "Metric Definitions > Market Share" for c in ms)


def test_small_sections_merge_into_neighbours() -> None:
    md = "# Doc\n## A\nshort\n## B\n" + "long text " * 60
    chunks = chunk_markdown("x.md", md)
    assert len(chunks) == 1 and "### B" in chunks[0].text


def test_rrf_rewards_agreement_between_retrievers() -> None:
    fused = rrf_fuse({"dense": ["a", "b", "c"], "lexical": ["c", "d"]})
    order = [item for item, _, _ in fused]
    assert order[0] == "c"  # ranked by both beats ranked first by one
    assert dict((i, r) for i, _, r in fused)["c"] == {"dense": 3, "lexical": 1}
