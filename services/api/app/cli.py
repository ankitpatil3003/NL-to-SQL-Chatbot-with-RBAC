"""Ask the assistant from the terminal, as any seeded user (for testing before/without the UI).

    uv run python -m app.cli --user amy.nguyen@novapharma.com "What are our total sales?"
    uv run python -m app.cli --user sarah.chen@novapharma.com "top 5 accounts" "now by quarter"

Several questions run as one conversation (follow-ups see the earlier turns). --sql shows the
executed SQL; --trace prints the per-stage timings and model calls.
"""

import argparse
import asyncio
import json
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.auth.repository import get_login_record
from app.core.config import get_settings
from app.db.engine import build_engine
from app.db.executor import QueryExecutor
from app.knowledge.base import init_knowledge
from app.llm.factory import build_router
from app.nl2sql.pipeline import Pipeline, ask
from app.nl2sql.types import HistoryTurn
from app.rbac.context import build_user_context

TRACE_QUERY = text(
    "SELECT latency_ms, cost_usd, detail FROM app.turn_traces WHERE trace_id = CAST(:i AS uuid)"
)


async def print_trace(engine: AsyncEngine, trace_id: str) -> None:
    async with engine.connect() as conn:
        row = (await conn.execute(TRACE_QUERY, {"i": trace_id})).one()
    stages = json.dumps(row.detail["stages_ms"])
    calls = ", ".join(
        f"{c['task']}:{c['model'].split('/')[-1]} {c['latency_ms']}ms"
        for c in row.detail["llm_calls"]
    )
    print(f"-- trace {trace_id}: {row.latency_ms} ms, ${row.cost_usd}, stages {stages}")
    print(f"   calls: {calls}")


async def main(email: str, questions: list[str], show_sql: bool, show_trace: bool) -> None:
    settings = get_settings()
    engine = build_engine(settings)
    executor = QueryExecutor(settings)
    llm = build_router(settings)
    kb = await init_knowledge(engine, settings.knowledge_docs_dir, settings.embed_cache_dir)
    record = await get_login_record(engine, email)
    if llm is None or kb is None or record is None:
        raise SystemExit("assistant not configured (LLM key / knowledge) or unknown user")
    user = build_user_context(record)
    pipeline = Pipeline(llm, kb, executor, engine, max_rows=settings.query_row_limit)
    print(f"# {user.full_name} ({user.role.value}, {user.scope_label})")

    history: list[HistoryTurn] = []
    for question in questions:
        result = await ask(pipeline, question, history, user)
        print(f"\n> {question}\n[{result.status}]\n{result.answer}")
        if show_sql and result.sql:
            print(f"\n-- SQL\n{result.sql}")
        if show_trace and result.trace_id:
            await print_trace(engine, result.trace_id)
        history.append(HistoryTurn(question, result.answer, result.sql))

    await llm.aclose()
    await executor.dispose()
    await engine.dispose()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # Windows consoles default to cp1252
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--user", required=True, help="email of a seeded user")
    parser.add_argument("--sql", action="store_true", help="print the executed SQL")
    parser.add_argument("--trace", action="store_true", help="print timings and model calls")
    parser.add_argument("questions", nargs="+")
    args = parser.parse_args()
    asyncio.run(main(args.user, args.questions, args.sql, args.trace))
