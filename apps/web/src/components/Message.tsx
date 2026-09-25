"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { AssistantPayload } from "@/lib/api";

import { CheckIcon, CopyIcon } from "./icons";
import ResultPanel from "./ResultPanel";

export interface UiMessage {
  key: string;
  role: "user" | "assistant";
  content: string;
  payload?: AssistantPayload | null;
  stage?: string | null; // while streaming
  error?: string | null;
}

const STAGE_LABEL: Record<string, string> = {
  understanding: "Understanding your question",
  retrieving: "Looking up definitions and similar questions",
  writing_sql: "Writing and checking the query",
  answering: "Writing the answer",
};

function Thinking({ stage }: { stage: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-fg-secondary" role="status" aria-live="polite">
      <span className="relative flex h-2.5 w-2.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent" />
      </span>
      {STAGE_LABEL[stage] ?? "Thinking"}…
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      title="Copy answer"
      className="rounded-md p-1 text-fg-muted hover:bg-bg-muted hover:text-fg"
    >
      {copied ? <CheckIcon width={15} height={15} /> : <CopyIcon width={15} height={15} />}
    </button>
  );
}

export default function Message({ message }: { message: UiMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-bg-muted px-4 py-2.5 whitespace-pre-wrap">{message.content}</div>
      </div>
    );
  }

  const p = message.payload;
  const streaming = message.stage != null;
  return (
    <div className="group">
      {streaming && !message.content && <Thinking stage={message.stage!} />}
      {message.content && (
        <div className="prose-answer">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      )}
      {message.error && (
        <div className="mt-2 rounded-lg border border-danger/40 px-3 py-2 text-sm text-danger">{message.error}</div>
      )}
      {p?.notes && p.notes.length > 0 && (
        <div className="mt-3 space-y-1 rounded-lg border border-border bg-bg-sidebar px-3 py-2 text-sm text-fg-secondary">
          {p.notes.map((n) => (
            <p key={n}>ⓘ {n}</p>
          ))}
        </div>
      )}
      {p?.table && <ResultPanel table={p.table} sql={p.sql} />}
      {p && p.assumptions.length > 0 && (
        <details className="mt-2 text-sm text-fg-muted">
          <summary className="cursor-pointer select-none hover:text-fg-secondary">Assumptions</summary>
          <ul className="mt-1 list-disc pl-5">
            {p.assumptions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </details>
      )}
      {!streaming && message.content && (
        <div className="mt-1 flex opacity-0 transition-opacity group-hover:opacity-100">
          <CopyButton text={message.content} />
        </div>
      )}
    </div>
  );
}
