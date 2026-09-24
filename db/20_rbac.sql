-- Row- and column-level security enforced by the database itself (CLAUDE.md §5, layer L4).
--
-- Threat model: the SQL executed here is written by an LLM and may be adversarial (prompt
-- injection). The database must stay safe even if every earlier layer (prompt, intent guard,
-- sqlglot validator) is bypassed.
--
-- Why not SET ROLE + session GUCs: any SELECT can call set_config('role', ...) or
-- set_config('app.scope', ...) and escape (verified: set_config('role','pharma',true) inside a
-- SELECT switches current_user back to the owner). So:
--   1. Two dedicated LOGIN roles, members of nothing, so there is no role to switch back to:
--        nl2sql_scoped_reader  Directors + RAMs: scoped views only; the views have no wac column.
--        nl2sql_exec_reader    Execs: base analytic tables, including wac.
--      Passwords are set by scripts/load_data.py from env (never in SQL files).
--   2. Scope is SEALED per transaction: rbac.set_scope() (SECURITY DEFINER) writes the scope into
--      a temp table owned by the definer. The reader can read it only through rbac.current_scope()
--      and can't modify it (no privileges), and set_scope() refuses a second call. No valid scope
--      means the views raise an error: fail closed.
-- Idempotent: safe to re-run.

CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- used later for fuzzy entity matching

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nl2sql_scoped_reader') THEN
        CREATE ROLE nl2sql_scoped_reader NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nl2sql_exec_reader') THEN
        CREATE ROLE nl2sql_exec_reader NOLOGIN;
    END IF;
END $$;

-- Readers can't create temp tables of their own (so they can't pre-create or shadow the seal).
DO $$ BEGIN EXECUTE format('REVOKE TEMPORARY ON DATABASE %I FROM PUBLIC', current_database()); END $$;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Session defaults as a backstop to the executor's own settings.
ALTER ROLE nl2sql_scoped_reader SET search_path = scoped, public;
ALTER ROLE nl2sql_exec_reader SET search_path = public;
ALTER ROLE nl2sql_scoped_reader SET statement_timeout = '15s';
ALTER ROLE nl2sql_exec_reader SET statement_timeout = '15s';
ALTER ROLE nl2sql_scoped_reader SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE nl2sql_exec_reader SET idle_in_transaction_session_timeout = '30s';

-- ---------------------------------------------------------------------------------------------
-- Scope seal
-- ---------------------------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS rbac;

CREATE OR REPLACE FUNCTION rbac.set_scope(p_level TEXT, p_value TEXT) RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF p_level NOT IN ('territory', 'region') OR coalesce(p_value, '') = '' THEN
        RAISE EXCEPTION 'rbac: invalid scope (%, %)', p_level, p_value;
    END IF;
    IF to_regclass('pg_temp.rbac_scope') IS NULL THEN
        CREATE TEMP TABLE rbac_scope (level TEXT NOT NULL, value TEXT NOT NULL) ON COMMIT DROP;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_temp.rbac_scope) THEN
        RAISE EXCEPTION 'rbac: scope already set for this transaction';
    END IF;
    INSERT INTO pg_temp.rbac_scope VALUES (p_level, p_value);
END $$;

CREATE OR REPLACE FUNCTION rbac.current_scope(OUT level TEXT, OUT value TEXT)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    BEGIN
        SELECT s.level, s.value INTO STRICT level, value FROM pg_temp.rbac_scope s;
    EXCEPTION WHEN undefined_table OR no_data_found OR too_many_rows THEN
        RAISE EXCEPTION 'rbac: no scope set for this transaction';
    END;
END $$;

REVOKE ALL ON FUNCTION rbac.set_scope(TEXT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION rbac.current_scope() FROM PUBLIC;
GRANT USAGE ON SCHEMA rbac TO nl2sql_scoped_reader;
GRANT EXECUTE ON FUNCTION rbac.set_scope(TEXT, TEXT) TO nl2sql_scoped_reader;
-- Functions inside a view are permission-checked against the caller, so the reader must be able
-- to execute current_scope(). It only ever returns the caller's own sealed scope.
GRANT EXECUTE ON FUNCTION rbac.current_scope() TO nl2sql_scoped_reader;

-- ---------------------------------------------------------------------------------------------
-- Scoped views. Views run with their owner's privileges, so the reader needs no access to the
-- base tables. The scope subquery is evaluated once per query (an InitPlan), not per row.
-- ---------------------------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS scoped;

CREATE OR REPLACE VIEW scoped.organizations AS
SELECT o.*
FROM public.organizations o
WHERE o.zip IN (
    SELECT z.zip
    FROM public.zip_territory z, rbac.current_scope() s
    WHERE (s.level = 'territory' AND z.territory_name = s.value)
       OR (s.level = 'region' AND z.region_name = s.value)
);

-- Every sales column except wac: for non-Execs the column does not exist.
CREATE OR REPLACE VIEW scoped.sales AS
SELECT s.sale_id, s.org_id, s.ndc, s.drug_name, s.data_source, s.brand_flag, s.pack_units,
       s.total_mg, s.transaction_date, s.week_ending_date, s.state, s.specialty, s.period_wk,
       s.period_mo, s.period_qtr, s.wk_offset, s.mo_offset
FROM public.sales s
WHERE s.org_id IN (SELECT o.org_id FROM scoped.organizations o);

-- ---------------------------------------------------------------------------------------------
-- Grants: reference tables are unrestricted (docs/security_model.md); users and app.* never.
-- ---------------------------------------------------------------------------------------------
GRANT USAGE ON SCHEMA scoped TO nl2sql_scoped_reader;
GRANT SELECT ON scoped.organizations, scoped.sales TO nl2sql_scoped_reader;
GRANT USAGE ON SCHEMA public TO nl2sql_scoped_reader, nl2sql_exec_reader;
GRANT SELECT ON public.products, public.zip_territory TO nl2sql_scoped_reader;
GRANT SELECT ON public.organizations, public.sales, public.products, public.zip_territory
    TO nl2sql_exec_reader;
