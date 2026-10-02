"use client";

import { useEffect, useMemo, useState } from "react";

import { api, type ResultTable, type Row } from "@/lib/api";
import { chooseChart, formatValue, humanize } from "@/lib/chart";

import { DownloadIcon, ExpandIcon } from "./icons";
import ResultChart from "./ResultChart";

type Tab = "chart" | "table" | "sql";

function toCsv(table: ResultTable): string {
  const cell = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [table.columns, ...table.rows].map((r) => r.map(cell).join(",")).join("\n");
}

function download(table: ResultTable, messageId: string) {
  // A capped result is exported server-side (all rows, streamed); a complete one is already here.
  const href = table.truncated
    ? api.exportUrl(messageId)
    : URL.createObjectURL(new Blob([toCsv(table)], { type: "text/csv" }));
  Object.assign(document.createElement("a"), {
    href,
    download: "result.csv",
  }).click();
  if (!table.truncated) URL.revokeObjectURL(href);
}

const PAGE = 100;

/** Rows to show: everything inline for a complete result; for a capped one, pages fetched from
 * the server (page 1 too, so every page comes from the same stable ordering). */
function usePagedRows(table: ResultTable, messageId: string, page: number) {
  const [rows, setRows] = useState<Row[]>(table.truncated ? table.rows.slice(0, PAGE) : table.rows);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!table.truncated) return;
    let live = true;
    api
      .rows(messageId, page * PAGE, PAGE)
      .then((r) => live && (setRows(r.rows), setError(false)))
      .catch(() => live && setError(true));
    return () => {
      live = false;
    };
  }, [table.truncated, messageId, page]);
  return { rows, error };
}

export default function ResultPanel({
  table,
  sql,
  messageId,
  expanded = false,
  onOpen,
}: {
  table: ResultTable;
  sql: string | null;
  messageId: string;
  expanded?: boolean; // full size, in the artifact panel
  onOpen?: () => void; // open this result in the artifact panel
}) {
  const [page, setPage] = useState(0);
  const { rows, error } = usePagedRows(table, messageId, page);
  const pages = Math.ceil(table.row_count / PAGE);
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
          {table.row_count.toLocaleString()} row
          {table.row_count === 1 ? "" : "s"}
        </span>
        <button
          onClick={() => download(table, messageId)}
          title={table.truncated ? `Download all ${table.row_count.toLocaleString()} rows (CSV)` : "Download CSV"}
          className="rounded-md p-1 text-fg-muted hover:bg-bg-muted hover:text-fg"
        >
          <DownloadIcon width={16} height={16} />
        </button>
        {onOpen && (
          <button
            onClick={onOpen}
            title="Open in the results panel"
            className="rounded-md p-1 text-fg-muted hover:bg-bg-muted hover:text-fg"
          >
            <ExpandIcon width={16} height={16} />
          </button>
        )}
      </div>

      <div className="p-3">
        {tab === "chart" && <ResultChart table={table} spec={spec} />}
        {tab === "table" && (
          <>
            <div className={`${expanded ? "max-h-[65vh]" : "max-h-96"} overflow-auto`}>
              <table className="w-full border-collapse text-sm tabular-nums">
                <thead className="sticky top-0 bg-bg-elevated">
                  <tr>
                    {table.columns.map((c) => (
                      <th
                        key={c}
                        className="border-b border-border px-3 py-2 text-left font-medium text-fg-secondary whitespace-nowrap"
                      >
                        {humanize(c)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
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
            {table.truncated && (
              <div className="flex items-center justify-end gap-2 pt-2 text-xs text-fg-muted">
                {error && (
                  <span className="mr-auto text-red-600 dark:text-red-400">Couldn&apos;t load these rows.</span>
                )}
                <span>
                  {(page * PAGE + 1).toLocaleString()}–{Math.min((page + 1) * PAGE, table.row_count).toLocaleString()}{" "}
                  of {table.row_count.toLocaleString()}
                </span>
                <button
                  onClick={() => setPage((p) => p - 1)}
                  disabled={page === 0}
                  aria-label="Previous rows"
                  className="rounded-md px-2 py-0.5 hover:bg-bg-muted disabled:opacity-40"
                >
                  ‹
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page + 1 >= pages}
                  aria-label="Next rows"
                  className="rounded-md px-2 py-0.5 hover:bg-bg-muted disabled:opacity-40"
                >
                  ›
                </button>
              </div>
            )}
          </>
        )}
        {tab === "sql" && sql && (
          <pre
            className={`${expanded ? "max-h-[65vh]" : "max-h-96"} overflow-auto rounded-lg bg-bg-muted p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap`}
          >
            {sql}
          </pre>
        )}
      </div>
    </div>
  );
}
