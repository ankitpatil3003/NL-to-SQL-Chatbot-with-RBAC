# Design: NovaPharma NL-to-SQL chat assistant

A Claude.ai-style chat app. Commercial users (Exec, Director, RAM) ask questions in plain English and
get answers computed by model-written SQL over the 2M-row dataset. Role-based row and column security
holds on every query, whatever the prompt says.

Companion documents: [`TESTING.md`](TESTING.md) (generated test results),
[`infra/README.md`](infra/README.md) (deployment runbook and costs), [`CLAUDE.md`](CLAUDE.md) (the
build contract and every recorded decision). Each change is a Conventional Commit whose body gives the
reason and the evidence, so `git log` works as a decision log.

---

## 1. Architecture

```
Browser ──HTTPS──▶ CloudFront ──HTTP + secret header──▶ ALB ─┬─ /*     ▶ web  (Next.js, ECS Fargate)
                                                            └─ /api/* ▶ api  (FastAPI, ECS Fargate)
                                                                          │
              ┌───────────────────────────────────────────────────────────┤
              ▼                                                           ▼
   RDS Postgres 16 (private subnets)                          Claude in Amazon Bedrock (task role)
     public.*  frozen base tables                             OpenRouter Nemotron (fallback)
     scoped.*  RBAC views (no wac column)
     app.*     credentials, chats, turn traces, knowledge index (pgvector + tsvector)
```

Two services, one origin. The ALB (behind CloudFront) routes `/api/*` straight to FastAPI. The browser
therefore talks to a single host: the httpOnly auth cookie and the SSE answer stream need no proxy hop
through Next.js.

### The turn pipeline (`services/api/app/nl2sql/`)

```
question ─▶ 1 context      UserContext from public.users (role, territory/region, WAC) by JWT user id
         ─▶ 2 understand   one structured LLM call: intent, standalone rewrite of follow-ups,
                           asks_for_dollars, mentions, a direct reply (small talk / refusal), chat title
         ─▶ 3 retrieve     hybrid search: 3 doc chunks + 4 role-filtered worked examples
         ─▶ 4 resolve      mentions → exact values (drugs, markets, territories, GPOs, accounts)
         ─▶ 5 generate     structured SqlDraft {answerable, sql, rules_applied, assumptions}
         ─▶ 6 guard        sqlglot AST validation, autofix, LIMIT
         ─▶ 7 execute      scoped read-only transaction on a role-specific DB login
             ↺ repair      guard / DB error fed back to the model, at most 2 times
         ─▶ 8 answer       deterministic notes + a short insight; table/chart/SQL go to the UI
         ─▶ 9 trace        every stage, model call, SQL attempt, token and cent → app.turn_traces
```

Each stage is a module with typed inputs and outputs. Providers, retriever and executor are injected,
so every stage runs in tests against fakes or the real database. The same `Pipeline` serves the SSE
endpoint, the CLI (`python -m app.cli --user <email> "q1" "q2"`) and the eval harness, so what gets
evaluated is exactly what users run.

A typical turn is three LLM calls. Routing and follow-up rewriting were planned as separate calls; they
were merged into one "understand" call to save a round trip per turn. That call also produces the chat
title, so reasoning-model thinking can't leak into titles.

---

## 2. Database choice: PostgreSQL 16

- **One engine for everything:** analytics over 2M rows, RBAC enforcement, chat history, traces, and
  the vector + full-text knowledge index (`pgvector`, `tsvector`, `pg_trgm`). No separate vector store
  to deploy, secure or keep in sync.
- **Real security primitives:** LOGIN roles, grants, views, `SECURITY DEFINER` functions, read-only
  transactions, `statement_timeout`. SQLite has none of these, and the design depends on them (§5).
- **Managed on AWS as RDS**, with the same image (`pgvector/pgvector:pg16`) locally in docker-compose.

**Frozen base tables.** Grading is blind against the generated dataset, so the five base tables keep
their names, columns and semantics. `db/00_base_schema.sql` is a dialect-only port of
`schema/create_tables.sql`:

- `AUTOINCREMENT` becomes an identity column.
- `REAL` becomes `DOUBLE PRECISION`. SQLite's REAL is 8 bytes, but Postgres's is 4 bytes, and a 4-byte
  `SUM` over 2M WAC values would corrupt revenue totals.

Everything else is additive: indexes, the `scoped` views, and the separate `app` schema.

**Loading** (`scripts/load_data.py`): migrations, then `COPY ... NULL ''`, then users from
`seed_data.sql`, then invariant checks, all in one transaction. The generator writes `None` as an
empty field. Without `NULL ''`, 10,000 standalone facilities would get `''` instead of NULL, and
`COALESCE(grandparent_org_name, org_name)` account roll-ups would break. The invariants guard the RBAC
backbone (every sale's zip maps to a territory; every RAM territory and Director region exists), and
any failure rolls the whole load back. Load time: about 36 s locally for 2M rows.

**Indexes, kept only where measured** (full data, EXPLAIN ANALYZE, warm, best of 3):

| Query shape | No index | Indexed |
|---|---|---|
| RAM territory total units | 97 ms | 49 ms |
| RAM top-10 accounts, last quarter | 107 ms | 50 ms |
| Exec last-month revenue | 103 ms | 5 ms |
| Single-account drill-down | 74 ms | 0 ms |

A plain `sales(org_id)` index was rejected because it made scoped queries 1.6–2.8× slower. It
fetched about 52 sales per facility, then discarded 50 of them on the source, brand and month
filters. The composite `sales(org_id, data_source, brand_flag, mo_offset)` index filters inside the
index instead.

**Data findings**, recorded because they change answers:

- `sales` has no geography. Every territory or region question goes through
  `sales → organizations.zip → zip_territory`, which is also the backbone of RBAC scoping.
- The generator's `market_data` rows are **competitor products only**, although the docs say that
  source includes NovaPharma. The documented market-share formula (Nova distributor equivalents ÷
  market_data equivalents) therefore exceeds 100% for 6 of 7 brands (e.g. Carboplatin 181%). We keep
  the documented formula exactly, since a blind grader most likely computes it the same way. Answers
  explain any value over 100% with a deterministic note (contract rule MS-3).
- `seed_data.sql` uses a 9-territory naming scheme that differs from `users` and the generator
  (15 territories), so 10 of 15 RAMs have no seed data. Development and CI use the full generated
  dataset.

---

## 3. Domain knowledge: a compiled semantic layer + hybrid retrieval

The docs are integrated in three complementary ways.

**1. Semantic contract, always in the prompt**
(`app/knowledge/semantic_contract.yaml`)

The eight business docs are compiled into a precise, versioned rulebook:
- table grain and column meanings;
- the only valid join paths;
- 26 rules with stable IDs that traces, examples and evals cite. The families are DS (data sources),
  M (measures), MS (market share), T (time), ORG (hierarchy), GEO, P (products) and SEC. Examples:
  - `DS-1`: "sales" means `distributor AND brand_flag = 1`;
  - `MS-1`: market share uses separate CTEs per source, matched on subcategory, with `NULLIF`;
  - `T-*`: relative time uses `mo_offset`/`wk_offset`, never `CURRENT_DATE`;
  - `ORG-*`: "accounts" means the grandparent level.

The contract is validated strictly (pydantic, `extra=forbid`, unique IDs) and versioned by content
hash.

At startup it also pulls a **live catalogue** from reference data (brands by market, competitors,
regions → territories, GPOs), so the model always uses exact spellings.

It renders as two system blocks:
- A **shared, cacheable** block with the instructions, rules and catalogue. It is identical for every
  user, so there is one prompt-cache entry.
- A small **per-user** block with the user's scope and WAC permission, kept out of the cached prefix.

**2. Hybrid retrieval** (`app/knowledge/store.py`)

- **Corpus.** The docs are chunked along their headings; each chunk keeps its heading path, e.g.
  "Metric Definitions > Market Share". Alongside them sits a bank of **38 curated NL→SQL examples**.
  These are executable documentation: tests run every one through the guard and against the full
  dataset.
- **Embedding.** Chunks are embedded locally with `BAAI/bge-small-en-v1.5` (fastembed/ONNX on CPU,
  baked into the image). There is no API key and no per-call cost, and results are deterministic in
  tests.
- **Search.** Dense (pgvector cosine) and lexical (Postgres full-text) searches run side by side.
  They are fused with **weighted Reciprocal Rank Fusion**.
- **Weights were chosen by ablation.** Plain equal-weight RRF was the worst arm, because brand names
  like "Zenovax" match half the example bank lexically and push good dense hits down. A lexical-weight
  sweep scored example recall@1 as follows:

  | Lexical weight | Recall@1 |
  |---|---|
  | 0 | 14/18 |
  | **0.25 (default)** | **15/18** |
  | 0.5 | 14/18 |
  | 1.0 | 12/18 |

  Doc recall@3 is 10/10 in every arm.
- **Rebuilds.** The index rebuilds only when the corpus hash changes, under an advisory lock so
  replicas don't race.

**3. Dynamic few-shot selection, role-aware**

The top 4 similar examples go into the SQL prompt. Examples that use `wac` are marked `exec_only`; a
unit test checks that the flag is set exactly when the SQL references `wac`. Those examples are
dropped for Directors and RAMs.

WAC-using SQL lines are also redacted from retrieved doc chunks for non-Execs. Before this fix, a
RAM's prompt contained the `SUM(wac)` revenue recipe. That leaked no data, but it invited failing
queries.

**Deterministic entity resolution** (`app/nl2sql/entities.py`) maps mentions to exact values: drugs,
markets, territories and regions (with NY/NE/CA abbreviations), GPOs, and accounts. Account lookup
uses `pg_trgm` candidates, and a candidate must contain every *distinctive* word of the mention;
generic words like health, medical and alliance don't count. Account lookups run **through the user's
scoped executor**, so a RAM's prompt can only ever contain organisations from their own territory.

---

## 4. LLM provider and prompt design

**Provider-agnostic router** (`app/llm/`)

- Everything above `app/llm` uses neutral types; only the adapters touch a vendor SDK. There are two
  adapters: an OpenAI-compatible httpx adapter (OpenRouter and similar) and an Anthropic SDK adapter.
  The Anthropic adapter serves both the first-party API and **Claude in Amazon Bedrock**.
- Chains are configuration: `LLM_CHAIN=provider:model,...`, with per-task overrides
  `LLM_CHAIN_SQL/_ROUTER/_ANSWER/...`.
- The router retries once on retryable errors (429, 5xx, timeouts, schema-invalid JSON), then falls
  back to the next target. Non-retryable errors (a 401, a bad request) skip straight to the next
  target. Every attempt is traced.

**Model choice, by evaluation rather than anecdote.** Golden set with only the SQL step varied:

| SQL model | Accuracy | p50 | Cost / 30 cases |
|---|---|---|---|
| Nemotron 3 Super 120B (free) | 97% | ~17 s | $0 |
| Claude Sonnet 5 | 97% | ~12 s | ~$0.26 |
| Nex n2.5-mini (free) | 77–87% | ~14 s | $0 (empty and truncated outputs) |

Nemotron's only failure was an upstream outage, so its SQL was effectively 30/30. The first
single-question anecdote, which suggested Nemotron got market share wrong, pointed the wrong way;
that is why the choice was left to the eval.

The chains in use:

- **Local and dev default:** Nemotron (free), falling back to Claude Sonnet 5. Normal operation costs
  about $0.
- **Production, paid from AWS credits:** Claude in Amazon Bedrock. Haiku 4.5 handles understanding,
  answers and titles; Sonnet 5 writes the SQL; free Nemotron is the fallback. The reason is latency:
  free-tier p50 is about 18 s per question. There is no Anthropic key in production, because the ECS
  task role signs requests (`bedrock-mantle:CreateInference`).
- **Bedrock caveat:** Bedrock's Messages endpoint lacks `output_config` structured outputs. On that
  provider the schema is sent as a single forced tool call, and the router validates the result the
  same way.

**Prompt design**

- **Prompts are code:** `app/nl2sql/prompts/{understand,sql,answer}.md`, versioned. The prompts hash
  plus the contract hash forms the `prompt_version` stored in every trace and eval report.
- **Structured outputs everywhere a program reads the result:** `Understanding`, and `SqlDraft`
  (`answerable`, `sql`, `rules_applied`, `assumptions`, `unanswerable_reason`). Strict JSON schemas
  are generated from pydantic models. A tolerant parser handles free models that wrap JSON in fences.
- **Prompt caching:** stable blocks (instructions + contract + catalogue) carry `cache_control`; the
  per-user scope block stays outside the cached prefix.
- **Multi-turn:** the understanding step rewrites follow-ups into standalone questions. It receives
  the user's role and scope, so "my region" is never ambiguous. The SQL step receives the previous
  question *and its SQL*, so "now by month" edits the last query instead of starting over. History is
  the last 4 turns, read from the database.
- **Self-correction with execution feedback:** guard violations and Postgres errors (message +
  DETAIL + HINT) go back to the model as a follow-up turn, at most 2 times. Guard messages are written
  for the model, e.g. "don't reference wac; answer in pack_units".
- **Rules that must hold are enforced in code, not asked for.** The model is never trusted to notice
  these things; the pipeline adds them as notes or fixes:
  - the "dollars aren't available at your access level" note;
  - out-of-scope mention notes;
  - the >100% market-share note;
  - the truncation note;
  - the `ROUND(double)` autofix;
  - replacing raw column names in answers (the model wrote "pack_units" after being told not to).
- **The answer gives the insight, not the table:** the UI already shows the table, chart and SQL, so
  the answer model leads with the point and cites at most 3 values.

---

## 5. Security: defence in depth

The prompt is not a security boundary. Four independent layers each assume the ones before them
failed:

| Layer | Mechanism | Catches |
|---|---|---|
| L1 prompt | scope + "no WAC" in the per-user system block | most cases, cheaply (UX only) |
| L2 intent | understanding flags dollar asks from non-Execs → answered in units with a note; out-of-scope geography → direct scope answer | clear behaviour for the doc's security scenarios |
| L3 SQL guard | sqlglot AST: see list below | model mistakes, prompt injection |
| **L4 database** | role-specific LOGIN roles + views without `wac` + sealed row scope | anything L1–L3 miss: the data is unreachable |

L3 checks, in `app/sqlguard/guard.py`:
- exactly one `SELECT`;
- no write nodes anywhere, including inside CTEs;
- a table allowlist, with CTE names resolved **per scope** (a global CTE list let a real `users`
  table pass as a CTE; the adversarial suite found this);
- an **allowlist** of functions: every dangerous Postgres function parses as `exp.Anonymous`, so the
  guard denies by default;
- any `wac` identifier rejected for non-Execs;
- a `LIMIT` enforced.

The guard executes sqlglot's **regeneration of the validated tree**, so a disagreement between the
sqlglot and Postgres parsers can't become a bypass.

**Authentication.** Email + password, bcrypt hashes in `app.credentials`, and a JWT in an httpOnly,
SameSite=Lax, Secure cookie.
- The JWT carries only the user id. Role and scope are re-read from `public.users` on every request
  and never taken from the client.
- Login does constant work: an unknown email still runs one bcrypt check, and both failures return an
  identical 401.
- The API refuses to start outside local development with a weak JWT secret.
- Demo decision: one shared password for all 23 users, from Secrets Manager, shown on the login page
  so graders can switch roles quickly. This is safe because the graded security is server-side
  scoping, which doesn't depend on the password being secret.

**Query scoping (L4, `db/20_rbac.sql`, `app/db/executor.py`)**

The plan was `SET ROLE` plus session GUCs. A probe showed that
`SELECT set_config('role','pharma',true)` inside a model-written query switches back to the owner,
and any GUC can be overwritten the same way. So:
- Two LOGIN roles that belong to no other role, so there is nothing to switch to.
  `nl2sql_scoped_reader` (Directors, RAMs) sees only `scoped.*` views. `nl2sql_exec_reader` (Execs)
  sees the base analytic tables. Neither can read `users` or `app.*`.
- `rbac.set_scope()` is `SECURITY DEFINER` and one-shot per transaction. It stores the scope in a temp
  table owned by the definer, which the reader can't write, drop or pre-create. With no scope, the
  views raise an error (fail closed).
- Scope values are always bound parameters, never interpolated into SQL.
- Per query: `statement_timeout` → seal scope → `transaction_read_only` → run as one prepared
  statement (so stacked queries are rejected) → always `ROLLBACK`.

**WAC restriction:** `scoped.sales` simply **has no `wac` column**. For a Director or RAM, even
`SELECT *` cannot return pricing, whatever SQL the model writes.

**Chat isolation:** every session and message query filters by the owner's `user_id`, and another
user's chat returns 404, never 403. The rate limit is 10 questions per hour per user, counted from
traces, so it survives restarts and chat deletion.

**Evidence:**
- `tests/integration/test_rbac_executor.py` checks all 23 users against independently computed
  ground truth, plus 15 escape attempts per scoped role.
- It is **mutation-tested**: removing either view's row filter, leaking `wac` into a view, or granting
  a base table each fails the suite.
- 322 adversarial guard tests.
- The eval's security category passes 12/12. It covers RAM, Director and Exec totals, other-territory
  and other-region asks, a WAC prompt injection, SQL typed as chat, and "drop the sales table".

---

## 6. Cloud services (AWS, `infra/terraform/`)

| Service | Why |
|---|---|
| ECS Fargate (api 0.5 vCPU/1 GB, web 0.25/0.5) | Containers without servers to patch; the circuit breaker rolls back a bad image automatically |
| RDS PostgreSQL 16 (db.t4g.micro, private subnets, SSL forced) | Managed Postgres with pgvector; the security model depends on Postgres features |
| ALB | Path routing `/api/*` → api, else web; long idle timeout for streamed answers |
| CloudFront (default `*.cloudfront.net` domain) | Free TLS without buying a domain; caches `/_next/static/*`; `/api/*` uncached and uncompressed so SSE flows |
| Secrets Manager | Generated DB, JWT and reader passwords; LLM keys set out of band, never in Terraform state or the repo |
| ECR (immutable tags, scan on push) | Images tagged with the git commit |
| Bedrock | Claude inference billed to the account, authorised by the task role, no API key |
| CloudWatch Logs | 14-day retention; turn traces in Postgres cover LLM observability |

Other choices:
- **Origin protection:** the ALB security group admits only CloudFront's origin-facing prefix list,
  and the listener returns 403 unless CloudFront's secret `X-Origin-Verify` header is present.
- **No NAT gateway:** tasks run in public subnets with public IPs for egress, and inbound traffic is
  locked to the ALB security group. This saves about $32/month.
- **SSE heartbeats:** CloudFront drops an origin that is silent for 60 s, so the API sends an SSE
  heartbeat every 10 s while a SQL step runs.
- **Data load:** runs as a one-off ECS task inside the VPC (`infra/deploy.sh load`), because RDS is
  private.
- **Cost:** about $61/month plus about $0.01–0.02 per question.
- **Tooling:** `infra/deploy.sh` runs `bootstrap | up | load | smoke | down`. Terraform runs from its
  Docker image, so there is nothing to install.
- **CI** (GitHub Actions): ruff, mypy and tests run on the **full 2M-row dataset**, so the RBAC leak
  and round-trip suites run on production-shaped data. It also runs web lint, typecheck and build,
  plus `terraform validate`.

---

## 7. Evaluation and observability

- **Golden set** (`services/api/evals/golden.yaml`, 40 cases): products, market share, accounts,
  territory, security, edge cases and multi-turn chains, asked as Exec, two Directors and a RAM.
- **Scoring is execution accuracy.** Each reference SQL runs *as the same user*, so RBAC scoping is
  part of the expected answer. The result must contain the reference rows (rounding-tolerant, column
  names ignored).
- **Attack cases** assert what must *not* happen instead: allowed outcomes, values that must not
  appear in any cell, and words banned from the executed SQL.
- **Per-model comparison:** `--arm` compares SQL models on identical inputs.
- **Result:** 39/40 on the default chain, with security 12/12. The one miss exposed a contract gap:
  "generic" was undefined, and the model read `brand_flag = 0` as generic. It was fixed with rule P-3
  and re-verified.
- **Eval-driven fixes.** Failures were analysed from traces, and several turned out to be the spec's
  fault rather than the model's:
  - RAM dollar questions were declared unanswerable instead of answered in units;
  - contradictory time defaults (rule T-5);
  - "my region" was ambiguous because understanding lacked the user's scope;
  - Execs got units without dollars.
- **`TESTING.md` is generated** from the latest report plus live pytest counts, never hand-edited.
- **Per-turn traces** (`app.turn_traces`), one row per turn, record:
  - stage timings;
  - every model call (provider, model, fallback, attempts with errors, tokens including cache reads,
    cost);
  - retrieval hits with their dense and lexical ranks;
  - entity hints;
  - every SQL attempt with guard and DB errors and autofixes;
  - SQL before and after the guard;
  - the prompt version.

  Traces are deliberately not cascaded from chats, so deleting a conversation can't erase the audit
  trail.

---

## 8. Trade-offs and what I'd improve

**Trade-offs taken**

- **Latency vs cost.** Free Nemotron matched Claude's accuracy but runs at about 18 s p50. Production
  pays for Bedrock to be responsive, and keeps free Nemotron as the fallback.
- **Market-share formula kept literally**, although this data makes it exceed 100%. Answers explain
  the anomaly instead of silently "fixing" the metric.
- **Three LLM calls per turn, not five.** Routing, rewriting and titling are merged into one
  structured call.
- **Exact vector scan, no ANN index.** About 80 items, so an exact scan is faster and has perfect
  recall.
- **Minimal, single-AZ infrastructure** (one task per service, db.t4g.micro), sized to a demo budget.
- **One shared demo password**, for grader convenience. Security rests on server-side scoping, not
  on password secrecy.

**With more time**

- **Accuracy:** a larger golden set with LLM-as-judge for answer text; run evals on the Bedrock chain
  and in CI nightly; retrieval evals on real user questions taken from traces; add confirmed-good
  traces to the few-shot bank automatically.
- **Latency:** stream the answer model's tokens (today the pipeline stages stream live, but the answer text
  arrives whole);
  run understanding and retrieval concurrently; cache frequent query results per scope.
- **Security hardening:** per-user LLM spend budgets; WAF on CloudFront; Postgres row-level security
  as an additional layer under the views; audit alerts on guard rejections.
- **Production infrastructure:** Multi-AZ RDS with deletion protection; a custom domain with
  end-to-end TLS; private task subnets with NAT or VPC endpoints; autoscaling with 2+ tasks (the
  one-turn-in-flight lock would move to Postgres advisory locks); GitHub OIDC deploys.
- **Observability:** OpenTelemetry or Langfuse export of the turn traces, plus a small dashboard of
  accuracy, latency and cost.
