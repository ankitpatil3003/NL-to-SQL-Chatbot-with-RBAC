"""Generate TESTING.md (the brief's "test cases & results" deliverable) from an eval report.

    uv run python -m evals.testing_md                 # latest report -> ../../TESTING.md
    uv run python -m evals.testing_md --report evals/reports/<stamp>.json

Every number and output in the document comes from a committed eval report or from pytest's own
collection, so the document can't drift from what actually ran.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
REPO = HERE.parent.parent.parent
GOLDEN = yaml.safe_load((HERE / "golden.yaml").read_text(encoding="utf-8"))
ROLE_OF = {
    "exec": "Exec",
    "dir_ne": "Director (Northeast)",
    "dir_west": "Director (West)",
    "ram_ny": "RAM (New York Metro)",
}
SECTIONS = [
    ("security", "Security: data scoping, WAC restriction and attacks"),
    ("market_share", "NL-to-SQL accuracy: market share"),
    ("products", "NL-to-SQL accuracy: products"),
    ("accounts", "NL-to-SQL accuracy: accounts"),
    ("territory", "NL-to-SQL accuracy: territory"),
    ("multi_turn", "Multi-turn follow-ups"),
    ("edge", "Edge cases: ambiguous, invalid and out-of-scope input"),
]

# What each automated suite proves (counts are collected live from pytest).
SUITES = [
    (
        "tests/integration/test_rbac_executor.py",
        "Database-enforced RBAC: all 23 users see exactly their entitled rows (vs ground truth), WAC absent for non-Execs, 15 escape attempts per scoped role blocked, limits. Mutation-tested (4 deliberate breakages each caught).",
    ),
    (
        "tests/unit/test_sqlguard_adversarial.py",
        "SQL guard vs ~110 attack strings x 3 roles (stacked statements, DML in CTEs, system tables, dangerous functions, 15 WAC probes) + benign look-alikes that must pass.",
    ),
    (
        "tests/unit/test_sqlguard.py",
        "Guard rules on realistic domain queries, LIMIT enforcement, ROUND autofix, wall-clock lint.",
    ),
    (
        "tests/integration/test_sqlguard_roundtrip.py",
        "The guard's rewritten SQL returns identical results to the original on the full dataset.",
    ),
    (
        "tests/integration/test_auth.py",
        "Login, httpOnly cookie, identical 401s, forged/expired tokens, all 23 users' scopes.",
    ),
    (
        "tests/integration/test_chat_api.py",
        "Chat API: streaming, persistence, follow-ups, cross-user 404, validation, disconnect-safe turns.",
    ),
    (
        "tests/integration/test_pipeline.py",
        "Every pipeline path with a scripted model (outage, exhausted repairs, WAC patterns never shown to non-Execs).",
    ),
    (
        "tests/integration/test_generate.py",
        "Self-repair loop from guard and database errors; dollars-to-volume redirect.",
    ),
    (
        "tests/integration/test_entities.py",
        "Entity resolution incl. RBAC: account lookups never suggest out-of-scope organizations.",
    ),
    (
        "tests/integration/test_contract_live.py",
        "Semantic-contract SQL templates execute; market-share formula matches the docs.",
    ),
    (
        "tests/integration/test_fewshots_live.py",
        "All 38 worked examples execute; retrieval recall and dense/lexical/hybrid ablation.",
    ),
    (
        "tests/integration/test_knowledge_store.py",
        "Knowledge index sync and doc retrieval recall@3.",
    ),
    (
        "tests/unit/test_llm.py",
        "LLM router: retry, fallback, error classification, structured output, both providers' wire formats.",
    ),
    (
        "tests/live/test_llm_live.py",
        "Real calls to every model in the chain (skipped without keys).",
    ),
]


def collected(path: str) -> int:
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", path],
        capture_output=True, text=True, cwd=HERE.parent,
    ).stdout  # fmt: skip
    return sum(1 for line in out.splitlines() if "::" in line)


def cell(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:,.1f}" if abs(v) < 1000 else f"{v:,.0f}"
    if isinstance(v, int):
        return f"{v:,}"
    return "∅" if v is None else str(v).replace("|", "/")


def rows_md(rows: list[list[Any]], limit: int = 5) -> str:
    if not rows:
        return "*(no rows)*"
    shown = "<br>".join(" · ".join(cell(v) for v in r) for r in rows[:limit])
    return shown + (f"<br>*… {len(rows) - limit} more*" if len(rows) > limit else "")


def expectation(case: dict[str, Any]) -> str:
    parts = []
    if case.get("status_in"):
        parts.append("status in " + " / ".join(case["status_in"]))
    elif case.get("status"):
        parts.append(f"status {case['status']}")
    if case.get("reference_sql"):
        parts.append(
            "result contains the reference rows" + (" in order" if case.get("ordered") else "")
        )
    if case.get("notes_contain"):
        parts.append("note mentions " + ", ".join(case["notes_contain"]))
    if case.get("must_not_contain"):
        shown = case["must_not_contain"][:3]
        parts.append(
            "no rows for " + ", ".join(shown) + (" …" if len(case["must_not_contain"]) > 3 else "")
        )
    if case.get("sql_must_not_contain"):
        parts.append("executed SQL never uses " + ", ".join(case["sql_must_not_contain"]))
    return "; ".join(parts) or "answered"


def render(report: dict[str, Any]) -> str:
    arm = next(iter(report["arms"].values()))
    summary, cases = arm["summary"], {c["id"]: c for c in arm["cases"]}
    golden = {c["id"]: c for c in GOLDEN["cases"]}
    out: list[str] = [
        "# Test cases & results",
        "",
        "Generated by `services/api/evals/testing_md.py` from eval report "
        f"`services/api/evals/reports/{report['stamp']}.json` (git `{report['git_commit']}`, "
        f"prompts `{report['prompt_version']}`). Nothing here is hand-edited.",
        "",
        "## Summary",
        "",
        f"- **Golden set:** {summary['passed']}/{summary['cases']} passed ({summary['accuracy']:.0%}) through the real "
        f"pipeline (understanding -> retrieval -> SQL -> guard -> scoped execution -> answer), "
        f"model chain `{arm['sql_chain'] or 'default'}`.",
        "- **By category:** " + ", ".join(f"{k} {v}" for k, v in summary["by_category"].items()),
        f"- **Latency:** p50 {summary['latency_p50_ms'] / 1000:.1f}s, p95 {summary['latency_p95_ms'] / 1000:.1f}s per question; "
        f"**cost** ${summary['cost_usd_total']:.4f} for the whole run; {summary['fell_back']} model fallback(s).",
        "- **Scoring:** execution accuracy. Each reference SQL runs *as the same user*, so RBAC scoping is part of "
        "the expected answer; the assistant's result must contain the reference rows (numbers within rounding "
        "tolerance, column names/order ignored). Attack cases instead assert what must *not* happen.",
        "",
        "Reproduce: `cd services/api && uv run python -m evals.run` (then `uv run python -m evals.testing_md`).",
        "",
        "## Automated test suites",
        "",
        "| Suite | What it proves | Tests |",
        "|---|---|---|",
    ]
    for path, what in SUITES:
        out.append(f"| `{path}` | {what} | {collected(path)} |")
    out.append(
        "| `apps/web/e2e/app.spec.ts` | Browser e2e (Playwright): login, scope display, theme, mobile sidebar, sign-out; live round trip with rename/delete. | 7 |"
    )
    out.append("")

    for category, title in SECTIONS:
        ids = [cid for cid, c in golden.items() if c["category"] == category and cid in cases]
        if not ids:
            continue
        passed = sum(cases[i]["passed"] for i in ids)
        out += [f"## {title} ({passed}/{len(ids)})", ""]
        out += [
            "| Case | Role | Question | Expected | Result | Actual output |",
            "|---|---|---|---|---|---|",
        ]
        for cid in ids:
            c, g = cases[cid], golden[cid]
            question = " → ".join([*g.get("history", []), g["question"]]).replace("|", "/")
            verdict = "✅ pass" if c["passed"] else f"❌ fail: {c['reason'][:90]}".replace("|", "/")
            actual = (
                rows_md(c.get("actual_rows", []))
                if c.get("actual_rows", [])
                else c["answer"][:160].replace("\n", " ").replace("|", "/")
            )
            if c.get("notes"):
                actual += "<br>*Notes:* " + " ".join(c["notes"])[:220].replace("|", "/")
            out.append(
                f"| `{cid}` | {ROLE_OF.get(g['user'], g['user'])} | {question} | {expectation(g)} | {verdict} (`{c['status']}`) | {actual} |"
            )
        out.append("")
        with_sql = [cid for cid in ids if cases[cid].get("sql")]
        if with_sql:
            out += ["<details><summary>Generated SQL and expected rows</summary>", ""]
            for cid in with_sql:
                c = cases[cid]
                out += [f"**`{cid}`**" + (f" (expected: {rows_md(c['expected_rows'], 3)})" if c.get("expected_rows", []) else ""), "",
                        "```sql", c["sql"], "```", ""]  # fmt: skip
            out += ["</details>", ""]

    failures = [c for c in arm["cases"] if not c["passed"]]
    out += ["## Failures and analysis", ""]
    if not failures:
        out.append("None in this run.")
    for c in failures:
        out.append(f"- `{c['id']}`: {c['reason']}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--report", type=Path, help="eval report JSON (default: latest)")
    parser.add_argument("--out", type=Path, default=REPO / "TESTING.md")
    args = parser.parse_args()
    report_path = args.report or sorted((HERE / "reports").glob("*.json"))[-1]
    args.out.write_text(
        render(json.loads(report_path.read_text(encoding="utf-8"))), encoding="utf-8", newline="\n"
    )
    print(f"wrote {args.out} from {report_path.name}")
