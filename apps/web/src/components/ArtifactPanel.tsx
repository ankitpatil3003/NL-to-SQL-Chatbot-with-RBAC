"use client";

import type { Artifact } from "@/lib/artifacts";

import { CloseIcon } from "./icons";
import ResultPanel from "./ResultPanel";

export type PanelView = { artifactId: string | null; version?: number }; // null id = the list

/** The chat's artifacts (like Claude's artifact panel): the list, or one result full size with
 * its versions, every row (paged), chart, SQL and export. Results also stay inline in the chat. */
export default function ArtifactPanel({
  artifacts,
  view,
  onView,
  onClose,
}: {
  artifacts: Artifact[];
  view: PanelView;
  onView: (view: PanelView) => void;
  onClose: () => void;
}) {
  const artifact = artifacts.find((a) => a.id === view.artifactId);
  const current = artifact && (artifact.versions.find((v) => v.version === view.version) ?? artifact.versions.at(-1));

  return (
    <aside className="fixed inset-0 z-40 flex flex-col bg-bg md:static md:z-auto md:w-[min(48rem,50vw)] md:border-l md:border-border">
      <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-3">
        {artifact ? (
          <button
            onClick={() => onView({ artifactId: null })}
            className="rounded-md px-2 py-1 text-sm text-fg-secondary hover:bg-bg-muted hover:text-fg"
          >
            ← All results ({artifacts.length})
          </button>
        ) : (
          <span className="px-2 text-sm font-medium">Results in this chat</span>
        )}
        <span className="flex-1" />
        <button onClick={onClose} title="Close panel" className="rounded-md p-1.5 text-fg-secondary hover:bg-bg-muted">
          <CloseIcon />
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {artifact && current ? (
          <>
            <h2 className="text-lg font-semibold">{artifact.title}</h2>
            {artifact.versions.length > 1 && (
              <div className="mt-2 flex flex-wrap gap-1" role="tablist" aria-label="Versions">
                {artifact.versions.map((v) => (
                  <button
                    key={v.messageId}
                    role="tab"
                    aria-selected={v.version === current.version}
                    onClick={() => onView({ artifactId: artifact.id, version: v.version })}
                    title={v.payload.standalone_question ?? undefined}
                    className={`rounded-md px-2.5 py-1 text-sm ${
                      v.version === current.version ? "bg-bg-muted text-fg" : "text-fg-secondary hover:text-fg"
                    }`}
                  >
                    v{v.version}
                  </button>
                ))}
              </div>
            )}
            {current.payload.standalone_question && (
              <p className="mt-2 text-sm text-fg-secondary">{current.payload.standalone_question}</p>
            )}
            {current.payload.table && (
              <ResultPanel
                key={current.messageId}
                table={current.payload.table}
                sql={current.payload.sql}
                messageId={current.messageId}
                expanded
              />
            )}
            {current.payload.assumptions.length > 0 && (
              <ul className="mt-3 list-disc pl-5 text-sm text-fg-muted">
                {current.payload.assumptions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            )}
          </>
        ) : artifacts.length === 0 ? (
          <p className="text-sm text-fg-muted">Results you ask for will appear here.</p>
        ) : (
          <ul className="space-y-2">
            {artifacts.map((a) => {
              const latest = a.versions.at(-1)!;
              return (
                <li key={a.id}>
                  <button
                    onClick={() => onView({ artifactId: a.id })}
                    className="w-full rounded-xl border border-border bg-bg-elevated px-4 py-3 text-left hover:border-fg-muted"
                  >
                    <div className="text-sm font-medium">{a.title}</div>
                    <div className="mt-0.5 text-xs text-fg-muted">
                      {latest.payload.table?.row_count.toLocaleString()} rows
                      {a.versions.length > 1 ? ` · ${a.versions.length} versions` : ""}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
