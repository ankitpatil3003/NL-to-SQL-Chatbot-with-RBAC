"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { AssistantPayload, PlanReview, ReviewResponse } from "@/lib/api";

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
  planning: "Planning the analysis",
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

/** A paused turn's analysis plan: the user picks answers to its open questions and/or corrects
 * it, then runs it. Only the latest message can be answered. */
function PlanCard({
  review,
  onRespond,
}: {
  review: PlanReview;
  onRespond?: (response: ReviewResponse, label: string) => void;
}) {
  const { plan } = review;
  const [choices, setChoices] = useState<Record<string, string>>(() =>
    Object.fromEntries(plan.open_questions.map((q) => [q.question, q.options[0] ?? ""])),
  );
  const [feedback, setFeedback] = useState("");
  const run = () => {
    // Only choices that differ from the plan's default need a re-plan.
    const answers = Object.fromEntries(
      plan.open_questions
        .filter((q) => choices[q.question] !== q.options[0])
        .map((q) => [q.question, choices[q.question]]),
    );
    const label = [...Object.entries(answers).map(([q, a]) => `${q}: ${a}`), feedback.trim()]
      .filter(Boolean)
      .join("; ");
    onRespond?.({ answers, feedback: feedback.trim() }, label || "Run this plan");
  };
  const row = (label: string, value: string) => (
    <div className="grid grid-cols-[7.5rem_1fr] gap-2">
      <dt className="text-fg-muted">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
  return (
    <div className="mt-3 rounded-xl border border-border bg-bg-elevated p-4 text-sm">
      <dl className="space-y-1.5">
        {row("Measure", plan.metric)}
        {row("Filters", plan.filters.join("; ") || "None")}
        {row("Breakdown", plan.breakdown)}
        {row("Period", plan.time_window)}
      </dl>
      {plan.open_questions.map((q) => (
        <fieldset key={q.question} className="mt-4" disabled={!onRespond}>
          <legend className="font-medium">{q.question}</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {q.options.map((o) => (
              <button
                key={o}
                type="button"
                aria-pressed={choices[q.question] === o}
                onClick={() => setChoices((c) => ({ ...c, [q.question]: o }))}
                className={`rounded-full border px-3 py-1 transition-colors ${
                  choices[q.question] === o
                    ? "border-accent bg-accent/10 text-fg"
                    : "border-border text-fg-secondary hover:border-fg-muted"
                }`}
              >
                {o}
              </button>
            ))}
          </div>
        </fieldset>
      ))}
      {onRespond && (
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input
            value={feedback}
            maxLength={2000}
            onChange={(e) => setFeedback(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="Change something (optional), e.g. use equivalents, not units"
            aria-label="Change the plan"
            className="min-w-0 flex-1 rounded-lg border border-border bg-transparent px-3 py-1.5 outline-none placeholder:text-fg-muted focus:border-fg-muted"
          />
          <button onClick={run} className="rounded-lg bg-accent px-4 py-1.5 font-medium text-accent-fg hover:opacity-90">
            {feedback.trim() ? "Revise plan" : "Run this plan"}
          </button>
        </div>
      )}
    </div>
  );
}

export default function Message({
  message,
  onRespond,
}: {
  message: UiMessage;
  onRespond?: (response: ReviewResponse, label: string) => void;
}) {
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
      {p?.status === "needs_input" && p.review && <PlanCard review={p.review} onRespond={onRespond} />}
      {p?.table && <ResultPanel table={p.table} sql={p.sql} messageId={message.key} />}
      {p && (p.assumptions.length > 0 || p.plan) && (
        <details className="mt-2 text-sm text-fg-muted">
          <summary className="cursor-pointer select-none hover:text-fg-secondary">Approach and assumptions</summary>
          {p.plan && <p className="mt-1">{p.plan.summary}</p>}
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
