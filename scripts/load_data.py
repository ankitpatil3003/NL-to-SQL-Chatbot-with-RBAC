# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Apply db/*.sql migrations and load the pharma dataset into Postgres.

    uv run scripts/load_data.py --seed          # schema/seed_data.sql (fast, ~300 sales rows)
    uv run scripts/load_data.py --full          # schema/generated/*.csv (2M sales rows)
    uv run scripts/load_data.py --full --generate   # run schema/generate_data.py first
    uv run scripts/load_data.py --schema-only   # migrations only, no data

Reloading replaces the 5 base tables only. The app schema (chat history, credentials) is never
touched, so a data refresh doesn't wipe users' conversations.

Connection: DATABASE_URL (the API's asyncpg URL is accepted), default local compose database.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "db"
SEED_SQL = ROOT / "schema" / "seed_data.sql"
GENERATOR = ROOT / "schema" / "generate_data.py"
CSV_DIR = ROOT / "schema" / "generated"

BASE_TABLES = ["sales", "organizations", "products", "zip_territory", "users"]

# Column lists come from the CSV headers written by schema/generate_data.py. sales.csv has no
# sale_id; the identity column assigns it on load.
CSV_TABLES = ["products", "organizations", "zip_territory", "sales"]  # FK-safe order

# Row counts the generator is specified to produce (README "The Data").
FULL_EXPECTED = {"organizations": 40_000, "products": 40, "sales": 2_000_000}


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql://pharma:pharma_dev_pw@localhost:5433/pharma")
    return url.replace("postgresql+asyncpg://", "postgresql://")


def log(msg: str) -> None:
    print(msg, flush=True)


def apply_migrations(conn: psycopg.Connection) -> None:
    for path in sorted(DB_DIR.glob("*.sql")):
        conn.execute(path.read_text(encoding="utf-8"))
        log(f"  applied {path.relative_to(ROOT)}")


# Least-privilege logins created by db/20_rbac.sql. Passwords come from env, never from SQL files;
# the API reads the same variables. Dev defaults match services/api/app/core/config.py.
READER_LOGINS = {
    "nl2sql_scoped_reader": ("DB_SCOPED_READER_PASSWORD", "scoped_reader_dev_pw"),
    "nl2sql_exec_reader": ("DB_EXEC_READER_PASSWORD", "exec_reader_dev_pw"),
}


def set_reader_passwords(conn: psycopg.Connection) -> None:
    for role, (env, default) in READER_LOGINS.items():
        password = os.environ.get(env, default)
        conn.execute(sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
        log(f"  login enabled for {role}" + (" (dev default password)" if env not in os.environ else ""))


def users_insert_from_seed() -> str:
    """The users table exists only in seed_data.sql; the generator never produces it."""
    match = re.search(r"^INSERT INTO users\b.*?;\s*$", SEED_SQL.read_text(encoding="utf-8"), re.S | re.M)
    if not match:
        sys.exit("users INSERT not found in schema/seed_data.sql")
    return match.group(0)


def copy_csv(conn: psycopg.Connection, table: str) -> None:
    path = CSV_DIR / f"{table}.csv"
    with path.open(encoding="utf-8", newline="") as f:
        columns = f.readline().strip()
        # The generator writes None as an empty unquoted field; NULL '' turns those back into
        # real NULLs (otherwise COALESCE(grandparent_org_name, org_name) yields '' for every
        # standalone facility).
        sql = f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT csv, NULL '')"
        with conn.cursor().copy(sql) as copy:
            while chunk := f.read(1 << 20):
                copy.write(chunk)


def load(conn: psycopg.Connection, mode: str) -> None:
    conn.execute(f"TRUNCATE {', '.join(BASE_TABLES)} RESTART IDENTITY")
    if mode == "seed":
        conn.execute(SEED_SQL.read_text(encoding="utf-8"))
        return
    missing = [t for t in CSV_TABLES if not (CSV_DIR / f"{t}.csv").exists()]
    if missing:
        sys.exit(f"missing CSVs for {missing}; run with --generate or python3 {GENERATOR.relative_to(ROOT)}")
    for table in CSV_TABLES:
        t0 = time.perf_counter()
        copy_csv(conn, table)
        log(f"  copied {table} ({time.perf_counter() - t0:.1f}s)")
    conn.execute(users_insert_from_seed())


# --------------------------------------------------------------------------------------------
# Invariants: fail on anything that would break RBAC or correctness; report data findings.
# --------------------------------------------------------------------------------------------


@dataclass
class Check:
    name: str
    sql: str  # returns a single number
    expect: str  # "zero" | "positive" | exact integer as string
    severity: str = "error"  # "error" fails the load; "info" is a documented data finding


NULLABLE_ORG_TEXT = [
    "org_archetype", "specialty", "address_line1", "city", "state", "zip", "parent_org_id",
    "parent_org_name", "grandparent_org_id", "grandparent_org_name", "gpo_name",
]  # fmt: skip


def checks(mode: str) -> list[Check]:
    # seed_data.sql's zip_territory uses a coarser 9-territory naming ("Great Lakes", "Pacific",
    # ...) than users and the generator (15 territories), so 10 of 15 RAMs have no seed data and
    # 2 seed facilities have unmapped zips. Coverage is therefore enforced on full data only.
    coverage = "error" if mode == "full" else "info"
    out = [Check(f"{t} has rows", f"SELECT count(*) FROM {t}", "positive") for t in BASE_TABLES]
    if mode == "full":
        out += [Check(f"{t} row count", f"SELECT count(*) FROM {t}", str(n)) for t, n in FULL_EXPECTED.items()]
    out += [
        Check(
            "no empty-string hierarchy/text values in organizations (NULLs loaded as NULL)",
            "SELECT count(*) FROM organizations WHERE " + " OR ".join(f"{c} = ''" for c in NULLABLE_ORG_TEXT),
            "zero",
        ),
        # RBAC backbone: sales -> organizations.zip -> zip_territory. A sale whose facility zip
        # has no territory would silently vanish from every scoped view.
        Check(
            "every sale's facility zip maps to a territory",
            "SELECT count(*) FROM sales s JOIN organizations o USING (org_id) "
            "LEFT JOIN zip_territory z ON z.zip = o.zip WHERE z.zip IS NULL",
            "zero",
            coverage,
        ),
        Check(
            "every RAM's territory exists in zip_territory",
            "SELECT count(*) FROM users u WHERE u.role = 'ram' AND NOT EXISTS "
            "(SELECT 1 FROM zip_territory z WHERE z.territory_name = u.territory_name)",
            "zero",
            coverage,
        ),
        Check(
            "every director/RAM region exists in zip_territory",
            "SELECT count(*) FROM users u WHERE u.role IN ('director','ram') AND NOT EXISTS "
            "(SELECT 1 FROM zip_territory z WHERE z.region_name = u.region_name)",
            "zero",
        ),
        Check(
            "every RAM's region matches their territory's region",
            "SELECT count(*) FROM users u WHERE u.role = 'ram' AND EXISTS (SELECT 1 FROM "
            "zip_territory z WHERE z.territory_name = u.territory_name AND z.region_name <> u.region_name)",
            "zero",
        ),
        Check("current month present (mo_offset = 0)", "SELECT count(*) FROM sales WHERE mo_offset = 0", "positive"),
        # Informational: facts about the data worth knowing when writing prompts / DESIGN.md.
        Check(
            "orgs whose zip has no territory (no sales impact if 0 above)",
            "SELECT count(*) FROM organizations o LEFT JOIN zip_territory z ON z.zip = o.zip WHERE z.zip IS NULL",
            "zero",
            "info",
        ),
        Check(
            "hub_dispense rows with non-zero wac",
            "SELECT count(*) FROM sales WHERE data_source = 'hub_dispense' AND wac <> 0",
            "zero",
            "info",
        ),
        Check(
            "distributor rows with brand_flag = 0",
            "SELECT count(*) FROM sales WHERE data_source = 'distributor' AND brand_flag = 0",
            "zero",
            "info",
        ),
        Check(
            "market_data rows with brand_flag = 1 (docs say market data includes Nova)",
            "SELECT count(*) FROM sales WHERE data_source = 'market_data' AND brand_flag = 1",
            "positive",
            "info",
        ),
    ]
    return out


def verify(conn: psycopg.Connection, mode: str) -> bool:
    ok = True
    for c in checks(mode):
        value = conn.execute(c.sql).fetchone()[0]
        passed = {"zero": value == 0, "positive": value > 0}.get(c.expect, str(value) == c.expect)
        mark = "PASS" if passed else ("FAIL" if c.severity == "error" else "NOTE")
        log(f"  [{mark}] {c.name}: {value:,}")
        ok &= passed or c.severity != "error"
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--seed", action="store_const", const="seed", dest="mode")
    mode.add_argument("--full", action="store_const", const="full", dest="mode")
    mode.add_argument("--schema-only", action="store_const", const="schema", dest="mode")
    parser.add_argument("--generate", action="store_true", help="run the data generator first (--full)")
    args = parser.parse_args()

    if args.generate:
        log("generating CSVs ...")
        subprocess.run([sys.executable, str(GENERATOR)], check=True, cwd=ROOT)

    t0 = time.perf_counter()
    with psycopg.connect(database_url()) as conn:  # one transaction: all or nothing
        log("migrations:")
        apply_migrations(conn)
        set_reader_passwords(conn)
        if args.mode == "schema":
            return
        log(f"loading ({args.mode}):")
        load(conn, args.mode)
        log("verifying:")
        if not verify(conn, args.mode):
            conn.rollback()
            sys.exit("invariant check failed; load rolled back")
    with psycopg.connect(database_url(), autocommit=True) as conn:
        # VACUUM as well as ANALYZE: sets hint bits and the visibility map on freshly COPYed rows,
        # so the first user queries don't pay for that work (and index-only scans become possible).
        conn.execute(f"VACUUM (ANALYZE) {', '.join(BASE_TABLES)}")
    log(f"done in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
