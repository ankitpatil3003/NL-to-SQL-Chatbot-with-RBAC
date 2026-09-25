"use client";

import { useState } from "react";

import type { Me, SessionSummary } from "@/lib/api";

import { LogoutIcon, PencilIcon, PlusIcon, SidebarIcon, TrashIcon } from "./icons";
import ThemeToggle from "./ThemeToggle";

const ROLE_LABEL = { exec: "Executive", director: "Director", ram: "Account manager" } as const;

function groupByDate(sessions: SessionSummary[]): [string, SessionSummary[]][] {
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const day = 86_400_000;
  const groups: Record<string, SessionSummary[]> = {};
  const order = ["Today", "Yesterday", "Previous 7 days", "Older"];
  for (const s of sessions) {
    const t = new Date(s.updated_at).getTime();
    const label =
      t >= startOfToday.getTime()
        ? "Today"
        : t >= startOfToday.getTime() - day
          ? "Yesterday"
          : t >= startOfToday.getTime() - 7 * day
            ? "Previous 7 days"
            : "Older";
    (groups[label] ??= []).push(s);
  }
  return order.filter((l) => groups[l]).map((l) => [l, groups[l]]);
}

function SessionRow({
  session,
  active,
  onOpen,
  onRename,
  onDelete,
}: {
  session: SessionSummary;
  active: boolean;
  onOpen: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [draft, setDraft] = useState(session.title ?? "");
  const title = session.title || "New chat";

  if (editing) {
    return (
      <input
        autoFocus
        value={draft}
        maxLength={120}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => setEditing(false)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && draft.trim()) {
            onRename(draft.trim());
            setEditing(false);
          }
          if (e.key === "Escape") setEditing(false);
        }}
        className="w-full rounded-lg border border-border bg-bg-elevated px-2 py-1.5 text-sm outline-none"
      />
    );
  }
  if (confirming) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-bg-muted px-2 py-1.5 text-sm">
        <span className="truncate text-fg-secondary">Delete chat?</span>
        <button onClick={onDelete} className="ml-auto font-medium text-danger hover:underline">
          Delete
        </button>
        <button onClick={() => setConfirming(false)} className="text-fg-secondary hover:underline">
          Cancel
        </button>
      </div>
    );
  }
  return (
    <div
      className={`group flex items-center rounded-lg text-sm ${active ? "bg-bg-muted text-fg" : "text-fg-secondary hover:bg-bg-muted/70"}`}
    >
      <button onClick={onOpen} className="min-w-0 flex-1 truncate px-2 py-1.5 text-left" title={title}>
        {title}
      </button>
      <div className="hidden shrink-0 pr-1 group-hover:flex">
        <button
          onClick={() => {
            setDraft(session.title ?? "");
            setEditing(true);
          }}
          title="Rename"
          className="rounded p-1 text-fg-muted hover:text-fg"
        >
          <PencilIcon width={14} height={14} />
        </button>
        <button onClick={() => setConfirming(true)} title="Delete" className="rounded p-1 text-fg-muted hover:text-danger">
          <TrashIcon width={14} height={14} />
        </button>
      </div>
    </div>
  );
}

export default function Sidebar({
  me,
  sessions,
  activeId,
  open,
  onToggle,
  onNewChat,
  onOpen,
  onRename,
  onDelete,
  onLogout,
}: {
  me: Me;
  sessions: SessionSummary[];
  activeId: string | null;
  open: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  onOpen: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onLogout: () => void;
}) {
  return (
    <>
      {open && <div className="fixed inset-0 z-20 bg-black/30 md:hidden" onClick={onToggle} />}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-72 flex-col border-r border-border bg-bg-sidebar transition-transform md:static md:z-auto ${
          open ? "translate-x-0" : "-translate-x-full md:hidden"
        }`}
      >
        <div className="flex items-center justify-between px-3 pt-3 pb-2">
          <span className="font-semibold tracking-tight">NovaPharma Analytics</span>
          <button onClick={onToggle} title="Close sidebar" className="rounded-md p-1.5 text-fg-secondary hover:bg-bg-muted">
            <SidebarIcon />
          </button>
        </div>
        <div className="px-3 pb-2">
          <button
            onClick={onNewChat}
            className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm font-medium hover:bg-bg-muted"
          >
            <PlusIcon /> New chat
          </button>
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          {sessions.length === 0 && <p className="px-2 py-4 text-sm text-fg-muted">Your chats will appear here.</p>}
          {groupByDate(sessions).map(([label, items]) => (
            <div key={label} className="mb-3">
              <div className="px-2 pt-2 pb-1 text-xs font-medium text-fg-muted">{label}</div>
              {items.map((s) => (
                <SessionRow
                  key={s.session_id}
                  session={s}
                  active={s.session_id === activeId}
                  onOpen={() => onOpen(s.session_id)}
                  onRename={(t) => onRename(s.session_id, t)}
                  onDelete={() => onDelete(s.session_id)}
                />
              ))}
            </div>
          ))}
        </nav>

        <div className="flex items-center gap-2 border-t border-border px-3 py-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-fg">
            {me.full_name
              .split(" ")
              .map((w) => w[0])
              .join("")
              .slice(0, 2)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{me.full_name}</div>
            <div className="truncate text-xs text-fg-muted" title={me.scope_label}>
              {ROLE_LABEL[me.role]} · {me.scope_label}
            </div>
          </div>
          <ThemeToggle />
          <button onClick={onLogout} title="Sign out" className="rounded-md p-1.5 text-fg-secondary hover:bg-bg-muted hover:text-fg">
            <LogoutIcon />
          </button>
        </div>
      </aside>
    </>
  );
}
