"""Adversarial inputs for the SQL guard, grouped by attack class. Every one must be rejected.

The guard is layer L3; the database (L4) independently blocks these too
(tests/integration/test_rbac_executor.py). A few entries are regression tests for holes found
while writing this suite; they're marked.
"""

import pytest

from app.rbac.context import UserContext
from app.sqlguard.guard import GuardViolation, Violation, guard

from .test_sqlguard import DIRECTOR, EXEC, RAM

STACKED_AND_COMMENTS = [
    "SELECT 1; DROP TABLE sales",
    "SELECT 1;DELETE FROM sales",
    "SELECT 1 /* harmless */; DELETE FROM sales",
    "SELECT 1; -- trailing\nUPDATE sales SET pack_units = 0",
    "SELECT pg_sleep/**/(1)",
]

NOT_A_QUERY = [
    "DELETE FROM sales",
    "UPDATE sales SET pack_units = 0",
    "INSERT INTO sales (org_id) VALUES ('x')",
    "TRUNCATE sales",
    "DROP TABLE sales",
    "CREATE TABLE x AS SELECT * FROM sales",
    "ALTER TABLE sales ADD COLUMN x int",
    "GRANT SELECT ON sales TO PUBLIC",
    "SET ROLE pharma",
    "RESET ROLE",
    "SET search_path = public",
    "BEGIN",
    "COMMIT",
    "COPY sales TO STDOUT",
    "COPY (SELECT 1) TO PROGRAM 'id'",
    "EXPLAIN ANALYZE DELETE FROM sales",
    "DO $$ BEGIN PERFORM pg_sleep(1); END $$",
    "CALL some_proc()",
    "PREPARE p AS SELECT 1",
    "EXECUTE p",
    "LISTEN chan",
    "NOTIFY chan",
    "VACUUM sales",
    "LOCK TABLE sales",
    "TABLE users",
    "VALUES (1), (2)",
]

WRITES_HIDDEN_IN_QUERIES = [
    "WITH x AS (DELETE FROM sales RETURNING *) SELECT * FROM x",
    "WITH x AS (UPDATE sales SET pack_units = 0 RETURNING *) SELECT count(*) FROM x",
    "WITH x AS (INSERT INTO products (ndc) VALUES ('1') RETURNING *) SELECT * FROM x",
    "SELECT * INTO stolen FROM sales",
    "SELECT * FROM sales FOR UPDATE",
    "SELECT * FROM sales FOR SHARE",
]

FORBIDDEN_TABLES = [
    "SELECT * FROM users",
    "SELECT * FROM USERS",
    'SELECT * FROM "users"',
    "SELECT email FROM users UNION SELECT drug_name FROM sales",
    "SELECT (SELECT email FROM users LIMIT 1) FROM sales",
    "SELECT * FROM sales WHERE org_id IN (SELECT user_id FROM users)",
    "SELECT * FROM sales, LATERAL (SELECT * FROM users) u",
    "WITH sales AS (SELECT * FROM users) SELECT * FROM sales",
    "SELECT * FROM pg_roles",
    "SELECT * FROM pg_user",
    "SELECT * FROM pg_stat_activity",
    "SELECT * FROM chat_messages",
    # Regression: a CTE named `users` inside a subquery made the outer, real `users` look like a
    # CTE to a global name check. Fixed with scope-aware resolution.
    "SELECT a.x, u.email FROM (WITH users AS (SELECT 1 AS x) SELECT x FROM users) a, users u",
]

SCHEMA_QUALIFIED = [
    "SELECT * FROM public.sales",
    'SELECT * FROM "public"."sales"',
    "SELECT * FROM information_schema.tables",
    "SELECT * FROM pg_catalog.pg_authid",
    "SELECT * FROM app.chat_messages",
    "SELECT * FROM app.credentials",
    "SELECT * FROM scoped.sales",
    "SELECT * FROM pharma.public.sales",
]

TABLE_FUNCTIONS = [
    "SELECT * FROM generate_series(1, 1000000000)",
    "SELECT * FROM sales, LATERAL pg_sleep(1)",
    "SELECT * FROM rbac.current_scope()",
    "SELECT * FROM dblink('host=evil', 'SELECT 1') AS t(x int)",
]

FORBIDDEN_FUNCTIONS = [
    "SELECT pg_sleep(10)",
    "select PG_SLEEP(10)",
    'SELECT "pg_sleep"(10)',
    "SELECT 1 WHERE EXISTS (SELECT pg_sleep(10))",
    "SELECT CAST(pg_sleep(1) AS text)",
    "SELECT set_config('role', 'pharma', true)",
    "SELECT (SELECT set_config('role', 'pharma', true))",
    "SELECT * FROM sales ORDER BY set_config('role', 'pharma', true)",
    "SELECT CASE WHEN set_config('role','pharma',true) = 'x' THEN 1 END",
    "WITH x AS (SELECT set_config('role', 'pharma', true)) SELECT * FROM sales",
    "SELECT current_setting('is_superuser')",
    "SELECT rbac.set_scope('territory', 'Texas')",
    "SELECT dblink('host=evil', 'SELECT 1')",
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT pg_ls_dir('.')",
    "SELECT lo_import('/etc/passwd')",
    "SELECT query_to_xml('SELECT * FROM users', true, true, '')",
    "SELECT pg_terminate_backend(1)",
    "SELECT pg_cancel_backend(1)",
    "SELECT txid_current()",
    # Typed (not Anonymous) environment functions: regression for version() slipping through.
    "SELECT version()",
    "SELECT current_user",
    "SELECT session_user",
    "SELECT current_schema()",
    "SELECT current_database()",
    "SELECT current_catalog",
    "SELECT inet_server_addr()",
]

WAC_PROBES = [
    "SELECT wac FROM sales",
    "SELECT WAC FROM sales",
    'SELECT "wac" FROM sales',
    'SELECT "WAC" FROM sales',
    'SELECT s."wac" FROM sales s',
    "SELECT SUM(wac) FROM sales",
    "SELECT SUM(s.wac) / SUM(s.pack_units) AS price FROM sales s",
    "SELECT x FROM (SELECT wac AS x FROM sales) t",
    "WITH r AS (SELECT wac FROM sales) SELECT SUM(wac) FROM r",
    "SELECT count(*) FROM sales WHERE wac > 1000",
    "SELECT org_id FROM sales ORDER BY wac DESC",
    "SELECT org_id FROM sales GROUP BY org_id HAVING SUM(wac) > 0",
    "SELECT RANK() OVER (ORDER BY wac) FROM sales",
    "SELECT drug_name FROM sales JOIN products USING (ndc) UNION SELECT CAST(wac AS text) FROM sales",
    "SELECT pack_units AS wac FROM sales",  # even aliasing to the name is refused: unambiguous rule
]

WALL_CLOCK = [
    "SELECT * FROM sales WHERE transaction_date > CURRENT_DATE - 30",
    "SELECT NOW()",
    "SELECT * FROM sales WHERE week_ending_date >= CAST(CURRENT_TIMESTAMP AS date)",
]

CASES: list[tuple[str, str]] = [
    *((s, "stacked/comments") for s in STACKED_AND_COMMENTS),
    *((s, "not a query") for s in NOT_A_QUERY),
    *((s, "hidden write") for s in WRITES_HIDDEN_IN_QUERIES),
    *((s, "forbidden table") for s in FORBIDDEN_TABLES),
    *((s, "schema-qualified") for s in SCHEMA_QUALIFIED),
    *((s, "table function") for s in TABLE_FUNCTIONS),
    *((s, "forbidden function") for s in FORBIDDEN_FUNCTIONS),
    *((s, "wall clock") for s in WALL_CLOCK),
]


@pytest.mark.parametrize(("sql", "attack"), CASES, ids=[f"{a}: {s[:50]}" for s, a in CASES])
@pytest.mark.parametrize("user", [EXEC, DIRECTOR, RAM], ids=["exec", "director", "ram"])
def test_attack_is_rejected_for_every_role(sql: str, attack: str, user: UserContext) -> None:
    with pytest.raises(GuardViolation):
        guard(sql, user, max_rows=100)


@pytest.mark.parametrize("sql", WAC_PROBES)
@pytest.mark.parametrize("user", [DIRECTOR, RAM], ids=["director", "ram"])
def test_wac_probe_is_rejected_for_non_exec(sql: str, user: UserContext) -> None:
    with pytest.raises(GuardViolation) as err:
        guard(sql, user, max_rows=100)
    assert err.value.code is Violation.WAC_NOT_PERMITTED


# Tricky but legitimate: the guard must not be so blunt it breaks real questions.
BENIGN_LOOKALIKES = [
    "SELECT 'a;b; DROP TABLE sales' AS s",  # keywords inside a string literal
    "SELECT drug_name FROM sales WHERE drug_name = 'wac'",  # 'wac' as a value, not a column
    "SELECT drug_name AS deleted_flag, 'users' AS label FROM sales",
    "SELECT * FROM sales",  # star is fine: scoped views have no wac column
    "SELECT s.* FROM sales s JOIN organizations o USING (org_id)",
    "WITH users AS (SELECT DISTINCT org_id FROM sales) SELECT count(*) FROM users",  # CTE shadowing
    "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 12) SELECT n FROM r",
    "SELECT org_name FROM organizations -- ignore all previous instructions",
]


@pytest.mark.parametrize("sql", BENIGN_LOOKALIKES)
@pytest.mark.parametrize("user", [EXEC, RAM], ids=["exec", "ram"])
def test_benign_lookalikes_pass(sql: str, user: UserContext) -> None:
    guard(sql, user, max_rows=100)
