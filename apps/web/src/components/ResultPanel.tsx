"use client";

import { useMemo, useState } from "react";

import type { ResultTable } from "@/lib/api";
import { chooseChart, formatValue, humanize } from "@/lib/chart";

import { DownloadIcon } from "./icons";
import ResultChart from "./ResultChart";

type Tab = "chart" | "table" | "sql";

function toCsv(table: ResultTable): string {
  const cell = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [table.columns, ...table.rows].map((r) => r.map(cell).join(",")).join("\n");
}

function download(table: ResultTable) {
  const url = URL.createObjectURL(new Blob([toCsv(table)], { type: "text/csv" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: "result.csv" });
  a.click();
  URL.revokeObjectURL(url);
}

export default function ResultPanel({ table, sql }: { table: ResultTable; sql: string | null }) {
  const spec = useMemo(() => chooseChart(table), [table]);
  const hasChart = spec.kind !== "none";
  const [tab, setTab] = useState<Tab>(hasChart ? "chart" : "table");
  const tabs: Tab[] = [...(hasChart ? (["chart"] as Tab[]) : []), "table", ...(sql ? (["sql"] as Tab[]) : [])];

  if (table.rows.length === 0) return null;
  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-border bg-bg-elevated">
      <div className="flex items-center gap-1 border-b border-border px-2 py-1.5 text-sm">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-md px-2.5 py-1 capitalize transition-colors ${
              tab === t ? "bg-bg-muted text-fg" : "text-fg-secondary hover:text-fg"
            }`}
          >
            {t === "sql" ? "SQL" : t}
          </button>
        ))}
        <span className="ml-auto pr-1 text-xs text-fg-muted">
          {table.row_count.toLocaleString()} row{table.row_count === 1 ? "" : "s"}
          {table.truncated ? " (truncated)" : ""}
        </span>
        <button
          onClick={() => download(table)}
          title="Download CSV"
          className="rounded-md p-1 text-fg-muted hover:bg-bg-muted hover:text-fg"
        >
          <DownloadIcon width={16} height={16} />
        </button>
      </div>

      <div className="p-3">
        {tab === "chart" && <ResultChart table={table} spec={spec} />}
        {tab === "table" && (
          <div className="max-h-96 overflow-auto">
            <table className="w-full border-collapse text-sm tabular-nums">
              <thead className="sticky top-0 bg-bg-elevated">
                <tr>
                  {table.columns.map((c) => (
                    <th key={c} className="border-b border-border px-3 py-2 text-left font-medium text-fg-secondary whitespace-nowrap">
                      {humanize(c)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, i) => (
                  <tr key={i} className="hover:bg-bg-muted/60">
                    {row.map((v, j) => (
                      <td
                        key={j}
                        className={`border-b border-border px-3 py-1.5 whitespace-nowrap ${typeof v === "number" ? "text-right" : ""}`}
                      >
                        {formatValue(v, table.columns[j])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {tab === "sql" && sql && (
          <pre className="max-h-96 overflow-auto rounded-lg bg-bg-muted p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap">
            {sql}
          </pre>
        )}
      </div>
    </div>
  );
}
