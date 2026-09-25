"use client";

// Charts follow the data-viz mark specs: 2px lines, bars <= 24px with 4px rounded data-ends,
// hairline solid grids in recessive grey, compact clean ticks, a legend only for >= 2 series,
// tooltips on every chart, text in text tokens (never series colours). The table view always
// carries every value, so nothing depends on reading colour alone.

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ResultTable } from "@/lib/api";
import { type ChartSpec, compact, formatValue, humanize, niceTicks } from "@/lib/chart";

const SERIES = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)"];
const AXIS_TICK = { fill: "var(--fg-muted)", fontSize: 12 };
const tooltipStyle = {
  contentStyle: {
    background: "var(--bg-elevated)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    color: "var(--fg)",
    fontSize: 13,
  },
  labelStyle: { color: "var(--fg-secondary)", marginBottom: 4 },
  itemStyle: { color: "var(--fg)" },
  cursor: { stroke: "var(--axis)", strokeWidth: 1, fill: "var(--bg-muted)" },
};

function rowsAsObjects(table: ResultTable): Record<string, string | number | null>[] {
  return table.rows.map((r) => Object.fromEntries(table.columns.map((c, i) => [c, r[i]])));
}

export function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-bg-elevated px-5 py-4">
      <div className="text-sm text-fg-secondary">{humanize(label)}</div>
      <div className="mt-1 text-4xl font-semibold tracking-tight">{formatValue(value, label)}</div>
    </div>
  );
}

export default function ResultChart({ table, spec }: { table: ResultTable; spec: ChartSpec }) {
  if (spec.kind === "none") return null;
  if (spec.kind === "stat") return <StatTile label={spec.label} value={spec.value} />;

  if (spec.kind === "bar") {
    const data = rowsAsObjects(table);
    const ticks = niceTicks(Math.max(0, ...data.map((d) => Number(d[spec.value]) || 0)));
    const height = Math.max(160, data.length * 34 + 40);
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid horizontal={false} stroke="var(--grid)" strokeWidth={1} />
          <XAxis
            type="number"
            domain={[0, ticks[ticks.length - 1]]}
            ticks={ticks}
            tick={AXIS_TICK}
            tickFormatter={(v) => compact(v, spec.value)}
            axisLine={{ stroke: "var(--axis)" }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey={spec.label}
            tick={AXIS_TICK}
            width={140}
            axisLine={{ stroke: "var(--axis)" }}
            tickLine={false}
          />
          <Tooltip {...tooltipStyle} formatter={(v) => [formatValue(v, spec.value), humanize(spec.value)]} />
          <Bar dataKey={spec.value} fill={SERIES[0]} maxBarSize={24} radius={[0, 4, 4, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // Lines: wide format (one column per measure) or long format pivoted by category.
  let data: Record<string, string | number | null>[];
  let series: string[];
  let x: string;
  let unitColumn: string;
  if (spec.kind === "pivot-line") {
    const byPeriod = new Map<string, Record<string, string | number | null>>();
    const [xi, ci, vi] = [spec.x, spec.category, spec.value].map((c) => table.columns.indexOf(c));
    for (const r of table.rows) {
      const key = String(r[xi]);
      const point = byPeriod.get(key) ?? { [spec.x]: key };
      point[String(r[ci])] = r[vi];
      byPeriod.set(key, point);
    }
    data = [...byPeriod.values()].sort((a, b) => String(a[spec.x]).localeCompare(String(b[spec.x])));
    series = spec.categories;
    x = spec.x;
    unitColumn = spec.value;
  } else {
    data = rowsAsObjects(table).sort((a, b) => String(a[spec.x]).localeCompare(String(b[spec.x])));
    series = spec.series;
    x = spec.x;
    unitColumn = spec.series[0];
  }
  const lineTicks = niceTicks(Math.max(0, ...data.flatMap((d) => series.map((s) => Number(d[s]) || 0))));
  const label = (s: string) => (spec.kind === "pivot-line" ? s : humanize(s));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 24, bottom: 4, left: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--grid)" strokeWidth={1} />
        <XAxis dataKey={x} tick={AXIS_TICK} axisLine={{ stroke: "var(--axis)" }} tickLine={false} minTickGap={16} />
        <YAxis
          domain={[0, lineTicks[lineTicks.length - 1]]}
          ticks={lineTicks}
          tick={AXIS_TICK}
          tickFormatter={(v) => compact(v, unitColumn)}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip {...tooltipStyle} formatter={(v, name) => [formatValue(v, unitColumn), label(String(name))]} />
        {series.length > 1 && (
          <Legend
            formatter={(value) => <span style={{ color: "var(--fg-secondary)", fontSize: 12 }}>{label(String(value))}</span>}
            iconType="plainline"
          />
        )}
        {series.map((s, i) => (
          <Line
            key={s}
            dataKey={s}
            name={s}
            stroke={SERIES[i]}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            dot={data.length <= 12 ? { r: 4, fill: SERIES[i], stroke: "var(--bg)", strokeWidth: 2 } : false}
            activeDot={{ r: 5, stroke: "var(--bg)", strokeWidth: 2 }}
            isAnimationActive={false}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
