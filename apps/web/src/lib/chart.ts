// Deterministic chart choice from the shape of a query result (no extra LLM call).
//
//   one numeric cell                      -> stat tile (it's a number, not a chart)
//   period column + 1..4 numeric columns  -> line (change over time; one line per measure)
//   period + category + 1 numeric, <= 4 categories -> one line per category (pivoted)
//   one label column + one numeric column -> horizontal bar (ranking / comparison), <= 25 rows
//   anything else                         -> table only
//
// Measures with different units (e.g. units and dollars) are never put on one axis: a
// multi-line chart only plots columns whose names share a unit family.

import type { ResultTable } from "./api";

export type ChartSpec =
  | { kind: "stat"; label: string; value: number }
  | { kind: "line"; x: string; series: string[] }
  // Long format (period, category, value): one line per category, pivoted client-side.
  | { kind: "pivot-line"; x: string; category: string; value: string; categories: string[] }
  | { kind: "bar"; label: string; value: string }
  | { kind: "none" };

const PERIOD = /^(period_(mo|qtr|wk)|month|quarter|week|year|period)$/i;
const PERIOD_VALUE = /^\d{4}-(\d{2}|Q[1-4]|W\d{2})$/;
const MAX_BARS = 25;
const MAX_LINES = 4;

const isNumber = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

function numericColumns(t: ResultTable): number[] {
  return t.columns
    .map((_, i) => i)
    .filter((i) => t.rows.length > 0 && t.rows.every((r) => r[i] === null || isNumber(r[i])) && t.rows.some((r) => isNumber(r[i])));
}

function unitFamily(name: string): string {
  const n = name.toLowerCase();
  if (/(revenue|wac|dollar|price|cost|sales_usd)/.test(n)) return "dollars";
  if (/(pct|percent|share|growth|rate)/.test(n)) return "percent";
  return "count";
}

export function chooseChart(t: ResultTable | null): ChartSpec {
  if (!t || t.rows.length === 0) return { kind: "none" };
  const numeric = numericColumns(t);
  const text = t.columns.map((_, i) => i).filter((i) => !numeric.includes(i));

  if (t.rows.length === 1 && numeric.length === 1 && t.columns.length <= 3) {
    const v = t.rows[0][numeric[0]];
    if (isNumber(v)) return { kind: "stat", label: t.columns[numeric[0]], value: v };
  }

  const periodIdx = t.columns.findIndex(
    (c, i) => PERIOD.test(c) || (!numeric.includes(i) && t.rows.every((r) => PERIOD_VALUE.test(String(r[i])))),
  );
  if (periodIdx !== -1 && t.rows.length >= 3 && numeric.length >= 1 && text.length === 1) {
    const family = unitFamily(t.columns[numeric[0]]);
    const series = numeric.filter((i) => unitFamily(t.columns[i]) === family).slice(0, MAX_LINES);
    return { kind: "line", x: t.columns[periodIdx], series: series.map((i) => t.columns[i]) };
  }

  if (periodIdx !== -1 && text.length === 2 && numeric.length === 1) {
    const catIdx = text.find((i) => i !== periodIdx)!;
    const categories = [...new Set(t.rows.map((r) => String(r[catIdx])))];
    if (categories.length <= MAX_LINES && t.rows.length / categories.length >= 3) {
      return {
        kind: "pivot-line",
        x: t.columns[periodIdx],
        category: t.columns[catIdx],
        value: t.columns[numeric[0]],
        categories,
      };
    }
  }

  if (text.length === 1 && numeric.length === 1 && t.rows.length >= 2 && t.rows.length <= MAX_BARS) {
    return { kind: "bar", label: t.columns[text[0]], value: t.columns[numeric[0]] };
  }
  return { kind: "none" };
}

// --- formatting ------------------------------------------------------------------------------

export function humanize(column: string): string {
  const words = column.replace(/_/g, " ").replace(/\bpct\b/i, "%").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function formatValue(v: unknown, column = ""): string {
  if (v === null || v === undefined) return "—";
  if (!isNumber(v)) return String(v);
  const family = unitFamily(column);
  if (family === "dollars") return v.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  if (family === "percent") return `${v.toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
  return v.toLocaleString(undefined, { maximumFractionDigits: Number.isInteger(v) ? 0 : 1 });
}

/** Axis ticks: compact (12.9K, 4.2M). */
export function compact(v: number, column = ""): string {
  const s = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(v);
  const family = unitFamily(column);
  return family === "dollars" ? `$${s}` : family === "percent" ? `${s}%` : s;
}

/** Clean axis ticks from 0: steps of 1, 2, 2.5 or 5 x 10^n (0 / 100K / 200K..., never 95K). */
export function niceTicks(max: number, target = 4): number[] {
  if (!(max > 0)) return [0, 1];
  const raw = max / target;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= raw)!;
  const ticks: number[] = [];
  for (let t = 0; t < max + step; t += step) ticks.push(Number(t.toPrecision(12)));
  return ticks;
}
