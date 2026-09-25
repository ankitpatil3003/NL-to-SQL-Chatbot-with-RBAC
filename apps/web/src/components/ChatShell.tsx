"use client";

// The whole chat app. It lives in the (chat) route-group layout, which Next.js keeps mounted
// across navigation between "/" and "/chat/[id]", so a new chat can move to its own URL
// mid-stream without losing the stream.

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

import { ApiError, api, type Me, type SessionSummary, streamTurn } from "@/lib/api";

import Composer from "./Composer";
import { SidebarIcon } from "./icons";
import Message, { type UiMessage } from "./Message";

import Sidebar from "./Sidebar";

const SUGGESTIONS: Record<Me["role"], string[]> = {
  exec: [
    "What are our total sales?",
    "Show me Zenovax market share by territory",
    "Top 10 accounts by revenue last quarter",
    "Show me monthly Gemtara volume for the past year",
  ],
  director: [
    "Compare territories in my region by total volume",
    "What is our market share for Zenovax?",
    "Which accounts declined more than 20% vs prior quarter?",
    "What percentage of our volume comes from 340B accounts?",
  ],
  ram: [
    "What are my top 10 accounts by pack units this quarter?",
    "Show me market share for Zenovax",
    "How much free drug did we provide last month?",
    "Is Zenovax volume growing month over month?",
  ],
};

const DESKTOP = "(min-width: 768px)";
const subscribeDesktop = (onChange: () => void) => {
  const mq = window.matchMedia(DESKTOP);
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
};
const isDesktopNow = () => window.matchMedia(DESKTOP).matches;

const sessionIdFrom = (path: string) => path.match(/^\/chat\/([0-9a-f-]{36})/)?.[1] ?? null;
let keySeq = 0;
const newKey = () => `m${++keySeq}`;

export default function ChatShell() {
  const router = useRouter();
  const pathname = usePathname();
  const urlSessionId = sessionIdFrom(pathname);

  const [me, setMe] = useState<Me | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  // Messages are tagged with the chat they belong to, and only shown for the chat in the URL,
  // so navigating (including browser Back) never shows another chat's messages.
  const [thread, setThread] = useState<{ id: string | null; messages: UiMessage[] }>({ id: null, messages: [] });
  const activeId = urlSessionId;
  const messages = thread.id === activeId ? thread.messages : [];
  const [busy, setBusy] = useState(false);
  const isDesktop = useSyncExternalStore(subscribeDesktop, isDesktopNow, () => true);
  const [sidebarPref, setSidebarPref] = useState<boolean | null>(null); // null = follow screen size
  const sidebarOpen = sidebarPref ?? isDesktop;
  const [loadError, setLoadError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamingSessionRef = useRef<string | null>(null); // the chat being streamed into
  const bottomRef = useRef<HTMLDivElement>(null);

  const refreshSessions = useCallback(() => api.sessions().then(setSessions).catch(() => {}), []);

  // Who's signed in (or bounce to /login).
  useEffect(() => {
    api
      .me()
      .then((m) => {
        setMe(m);
        refreshSessions();
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) router.replace("/login");
        else setLoadError("Can't reach the server. Please refresh.");
      });
  }, [router, refreshSessions]);

  // Load the chat named in the URL (unless it's the one we're streaming into right now).
  useEffect(() => {
    if (!urlSessionId || urlSessionId === streamingSessionRef.current) return;
    let cancelled = false;
    api
      .session(urlSessionId)
      .then((s) => {
        if (cancelled) return;
        setThread({
          id: urlSessionId,
          messages: s.messages.map((m) => ({ key: m.message_id, role: m.role, content: m.content, payload: m.payload })),
        });
      })
      .catch((e) => {
        if (!cancelled && e instanceof ApiError && e.status === 404) router.replace("/");
      });
    return () => {
      cancelled = true;
    };
  }, [urlSessionId, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [thread]);

  const patchLast = (patch: Partial<UiMessage>) =>
    setThread((t) => ({ ...t, messages: t.messages.map((m, i) => (i === t.messages.length - 1 ? { ...m, ...patch } : m)) }));

  const send = async (text: string) => {
    if (busy) return;
    setBusy(true);
    const controller = new AbortController();
    abortRef.current = controller;
    streamingSessionRef.current = activeId;
    setThread((t) => ({
      id: activeId,
      messages: [
        ...(t.id === activeId ? t.messages : []),
        { key: newKey(), role: "user", content: text },
        { key: newKey(), role: "assistant", content: "", stage: "understanding" },
      ],
    }));
    try {
      for await (const ev of streamTurn(text, activeId, controller.signal)) {
        if (ev.event === "session") {
          if (!activeId) {
            streamingSessionRef.current = ev.data.session_id;
            setThread((t) => ({ ...t, id: ev.data.session_id }));
            window.history.replaceState(null, "", `/chat/${ev.data.session_id}`);
            refreshSessions();
          }
        } else if (ev.event === "stage") patchLast({ stage: ev.data.name });
        else if (ev.event === "answer_delta") patchLast({ content: ev.data.text });
        else if (ev.event === "result") {
          const { message_id, answer, ...payload } = ev.data;
          patchLast({ key: message_id, content: answer, payload, stage: null });
        } else if (ev.event === "title") refreshSessions();
        else if (ev.event === "error") patchLast({ stage: null, error: ev.data.message });
      }
    } catch (e) {
      if (controller.signal.aborted) {
        patchLast({ stage: null, error: "Stopped. The answer is still being saved — reopen the chat to see it." });
      } else {
        const msg =
          e instanceof ApiError && e.status === 429
            ? e.message // "A question is already being answered" or the hourly limit
            : e instanceof ApiError && e.status === 503
              ? "The assistant isn't configured on the server."
              : e instanceof ApiError && e.status === 401
                ? "Your session has expired. Please sign in again."
                : "Couldn't reach the assistant. Please try again.";
        patchLast({ stage: null, error: msg });
        if (e instanceof ApiError && e.status === 401) router.replace("/login");
      }
    } finally {
      patchLast({ stage: null });
      setBusy(false);
      abortRef.current = null;
      streamingSessionRef.current = null;
      refreshSessions();
    }
  };

  const newChat = () => {
    if (busy) abortRef.current?.abort();
    setThread({ id: null, messages: [] });
    router.push("/");
    if (!isDesktopNow()) setSidebarPref(false);
  };

  const openChat = (id: string) => {
    router.push(`/chat/${id}`);
    if (!isDesktopNow()) setSidebarPref(false);
  };

  if (loadError) return <div className="m-auto p-6 text-fg-secondary">{loadError}</div>;
  if (!me) return <div className="m-auto p-6 text-fg-muted">Loading…</div>;

  const empty = messages.length === 0;
  return (
    <div className="flex h-dvh w-full overflow-hidden">
      <Sidebar
        me={me}
        sessions={sessions}
        activeId={activeId}
        open={sidebarOpen}
        onToggle={() => setSidebarPref(!sidebarOpen)}
        onNewChat={newChat}
        onOpen={openChat}
        onRename={async (id, title) => {
          await api.rename(id, title);
          refreshSessions();
        }}
        onDelete={async (id) => {
          await api.remove(id);
          if (id === activeId) newChat();
          refreshSessions();
        }}
        onLogout={async () => {
          await api.logout().catch(() => {});
          router.replace("/login");
        }}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-2 px-3">
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarPref(true)}
              title="Open sidebar"
              className="rounded-md p-1.5 text-fg-secondary hover:bg-bg-muted"
            >
              <SidebarIcon />
            </button>
          )}
          <span className="truncate text-sm text-fg-secondary">
            {sessions.find((s) => s.session_id === activeId)?.title ?? (activeId ? "" : "New chat")}
          </span>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-3xl px-4 pb-6">
            {empty ? (
              <div className="pt-[18vh] text-center">
                <h1 className="text-3xl font-semibold tracking-tight">
                  {greeting()}, {me.full_name.split(" ")[0]}
                </h1>
                <p className="mt-2 text-fg-secondary">
                  Ask about NovaPharma sales, market share, accounts and territories. You&apos;re seeing{" "}
                  <span className="font-medium text-fg">{me.scope_label}</span>
                  {me.can_view_wac ? ", including pricing." : "; pricing (WAC) isn't available at your access level."}
                </p>
                <div className="mx-auto mt-8 grid max-w-2xl gap-2 sm:grid-cols-2">
                  {SUGGESTIONS[me.role].map((q) => (
                    <button
                      key={q}
                      onClick={() => send(q)}
                      className="rounded-xl border border-border bg-bg-elevated px-4 py-3 text-left text-sm text-fg-secondary hover:border-fg-muted hover:text-fg"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-6 pt-4">
                {messages.map((m) => (
                  <Message key={m.key} message={m} />
                ))}
                <div ref={bottomRef} />
              </div>
            )}
          </div>
        </div>

        <div className="mx-auto w-full max-w-3xl shrink-0 px-4 pb-4">
          <Composer onSend={send} onStop={() => abortRef.current?.abort()} busy={busy} autoFocus />
          <p className="mt-2 text-center text-xs text-fg-muted">
            Answers are generated from NovaPharma data and can contain mistakes. Check the SQL for important decisions.
          </p>
        </div>
      </main>
    </div>
  );
}

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}
