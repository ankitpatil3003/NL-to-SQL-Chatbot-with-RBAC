"""Run the golden set through the real pipeline and score it.

    uv run python -m evals.run                                   # default chain
    uv run python -m evals.run --arm nemotron=openrouter:nvidia/nemotron-3-super-120b-a12b:free \\
                               --arm claude=anthropic:claude-sonnet-5 --only ms-zenovax-exec

Each --arm name=chain overrides the SQL-generation step (LLM_CHAIN_SQL) only, so arms differ in
exactly one variable; understanding and answering use the default chain. Arms run concurrently,
cases within an arm sequentially (free-tier rate limits). Writes evals/reports/<stamp>.json and
<stamp>.md (summary + per-case results) with the git commit and prompt version for reproducibility.
"""

import argparse
import asyncio
import datetime as dt
import json
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import text

from app.auth.repository import get_login_record
from app.core.config import Settings, get_settings
from app.db.engine import build_engine
from app.db.executor import QueryExecutor
from app.knowledge.base import init_knowledge
from app.llm.factory import build_router
from app.nl2sql.pipeline import Pipeline, ask
from app.nl2sql.types import HistoryTurn
from app.rbac.context import UserContext, build_user_context
from evals.compare import compare

HERE = Path(__file__).parent
REPORTS = HERE / "reports"


@dataclass
class CaseResult:
    id: str
    category: str
    user: str
    passed: bool
    reason: str
    status: str
    latency_ms: int
    cost_usd: float | None
    sql_attempts: int
    fell_back: bool
    sql: str | None = None
    answer: str = ""
    models: list[str] = field(default_factory=list)


async def trace_stats(engine: Any, trace_id: str | None) -> dict[str, Any]:
    if not trace_id:
        return {
            "latency_ms": 0,
            "cost_usd": None,
            "sql_attempts": 0,
            "fell_back": False,
            "models": [],
        }
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT latency_ms, cost_usd, detail FROM app.turn_traces WHERE trace_id = CAST(:i AS uuid)"
                ),
                {"i": trace_id},
            )
        ).one()
    calls = row.detail.get("llm_calls", [])
    return {
        "latency_ms": row.latency_ms,
        "cost_usd": float(row.cost_usd) if row.cost_usd is not None else None,
        "sql_attempts": len(row.detail.get("sql_attempts", [])),
        "fell_back": any(c["fell_back"] for c in calls),
        "models": [f"{c['task']}:{c['model']}" for c in calls],
    }


async def run_case(
    case: dict[str, Any],
    user: UserContext,
    pipeline: Pipeline,
    executor: QueryExecutor,
    engine: Any,
) -> CaseResult:
    history: list[HistoryTurn] = []
    for q in case.get("history", []):
        prior = await ask(pipeline, q, history, user)
        history.append(HistoryTurn(q, prior.answer, prior.sql))
    result = await ask(pipeline, case["question"], history, user)
    stats = await trace_stats(engine, result.trace_id)

    passed, reason = True, "ok"
    expected_status = case.get("status", "answered")
    if result.status != expected_status:
        passed, reason = False, f"status {result.status} != {expected_status}"
    elif case.get("reference_sql"):
        if result.table is None:
            passed, reason = False, "no result table"
        else:
            reference = await executor.run(user, case["reference_sql"])
            passed, reason = compare(
                [list(r) for r in reference.rows],
                result.table.rows,
                ordered=case.get("ordered", False),
                extra_rows_ok=case.get("extra_rows_ok", False),
            )
    for needle in case.get("notes_contain", []):
        if passed and not any(needle in n for n in result.notes):
            passed, reason = False, f"notes missing {needle!r}"

    return CaseResult(
        id=case["id"], category=case["category"], user=case["user"], passed=passed, reason=reason,
        status=result.status, sql=result.sql, answer=result.answer, **stats,
    )  # fmt: skip


async def run_arm(
    name: str, chain: str | None, cases: list[dict[str, Any]], users: dict[str, str]
) -> list[CaseResult]:
    base = get_settings()
    settings: Settings = base.model_copy(update={"llm_chain_sql": chain}) if chain else base
    engine = build_engine(settings)
    executor = QueryExecutor(settings)
    llm = build_router(settings)
    kb = await init_knowledge(engine, settings.knowledge_docs_dir, settings.embed_cache_dir)
    assert llm is not None and kb is not None, "assistant not configured"
    pipeline = Pipeline(llm, kb, executor, engine, max_rows=settings.query_row_limit)

    contexts = {}
    for alias, email in users.items():
        record = await get_login_record(engine, email)
        assert record is not None, email
        contexts[alias] = build_user_context(record)

    results = []
    for case in cases:
        started = time.perf_counter()
        try:
            res = await run_case(case, contexts[case["user"]], pipeline, executor, engine)
        except Exception as exc:  # a crashing case is a failed case, not a crashed run
            res = CaseResult(case["id"], case["category"], case["user"], False, f"crash: {exc!r}"[:300],
                             "crash", int((time.perf_counter() - started) * 1000), None, 0, False)  # fmt: skip
        mark = "PASS" if res.passed else "FAIL"
        print(
            f"[{name}] {mark} {res.id} ({res.latency_ms} ms) {'' if res.passed else res.reason[:120]}",
            flush=True,
        )
        results.append(res)
    await llm.aclose()
    await executor.dispose()
    await engine.dispose()
    return results


def summarise(results: list[CaseResult]) -> dict[str, Any]:
    latencies = [r.latency_ms for r in results]
    costs = [r.cost_usd for r in results if r.cost_usd is not None]
    categories: dict[str, list[bool]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r.passed)
    return {
        "cases": len(results),
        "passed": sum(r.passed for r in results),
        "accuracy": round(sum(r.passed for r in results) / len(results), 3) if results else 0,
        "by_category": {c: f"{sum(v)}/{len(v)}" for c, v in sorted(categories.items())},
        "latency_p50_ms": int(statistics.median(latencies)) if latencies else 0,
        "latency_p95_ms": int(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)])
        if latencies
        else 0,
        "cost_usd_total": round(sum(costs), 4),
        "repaired": sum(r.sql_attempts > 1 for r in results),
        "fell_back": sum(r.fell_back for r in results),
    }


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def write_report(
    stamp: str,
    runs: dict[str, list[CaseResult]],
    chains: dict[str, str | None],
    prompt_version: str,
) -> Path:
    REPORTS.mkdir(exist_ok=True)
    summaries = {name: summarise(res) for name, res in runs.items()}
    payload = {
        "stamp": stamp, "git_commit": git_commit(), "prompt_version": prompt_version,
        "arms": {n: {"sql_chain": chains[n], "summary": summaries[n], "cases": [asdict(r) for r in runs[n]]} for n in runs},
    }  # fmt: skip
    (REPORTS / f"{stamp}.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )

    lines = [
        f"# Eval run {stamp}",
        "",
        f"git `{payload['git_commit']}` · prompts `{prompt_version}`",
        "",
    ]
    lines += [
        "| arm | SQL model | accuracy | p50 latency | p95 latency | cost | repaired | fell back |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for n, s in summaries.items():
        lines.append(
            f"| {n} | `{chains[n] or 'default chain'}` | **{s['passed']}/{s['cases']} ({s['accuracy']:.0%})** | "
            f"{s['latency_p50_ms'] / 1000:.1f}s | {s['latency_p95_ms'] / 1000:.1f}s | ${s['cost_usd_total']:.4f} | {s['repaired']} | {s['fell_back']} |"
        )
    categories = sorted({c for s in summaries.values() for c in s["by_category"]})
    lines += [
        "",
        "## By category",
        "",
        "| arm | " + " | ".join(categories) + " |",
        "|---|" + "---|" * len(categories),
    ]
    for n, s in summaries.items():
        lines.append(
            f"| {n} | " + " | ".join(s["by_category"].get(c, "-") for c in categories) + " |"
        )
    lines += [
        "",
        "## Cases",
        "",
        "| case | " + " | ".join(runs) + " |",
        "|---|" + "---|" * len(runs),
    ]
    for i, case_id in enumerate(r.id for r in next(iter(runs.values()))):
        cells = []
        for res in runs.values():
            r = res[i]
            cells.append("✅" if r.passed else f"❌ {r.reason[:80]}".replace("|", "/"))
        lines.append(f"| {case_id} | " + " | ".join(cells) + " |")
    path = REPORTS / f"{stamp}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


async def main(arms: list[str], only: set[str] | None) -> None:
    spec = yaml.safe_load((HERE / "golden.yaml").read_text(encoding="utf-8"))
    cases = [c for c in spec["cases"] if not only or c["id"] in only]
    chains: dict[str, str | None] = {}
    for arm in arms or ["default="]:
        name, _, chain = arm.partition("=")
        chains[name] = chain or None
    print(f"{len(cases)} cases x {len(chains)} arms", flush=True)

    results = await asyncio.gather(
        *(run_arm(n, c, cases, spec["users"]) for n, c in chains.items())
    )
    runs = dict(zip(chains, results, strict=True))

    from app.knowledge.contract import load_contract
    from app.nl2sql.prompts import prompts_hash

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = write_report(stamp, runs, chains, f"p{prompts_hash()}-c{load_contract().content_hash}")
    print(f"\nreport: {path}")
    print(path.read_text(encoding="utf-8").split("## Cases")[0])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--arm",
        action="append",
        default=[],
        help="name=provider:model[,provider:model] for the SQL step",
    )
    parser.add_argument("--only", help="comma-separated case ids")
    args = parser.parse_args()
    asyncio.run(main(args.arm, set(args.only.split(",")) if args.only else None))
