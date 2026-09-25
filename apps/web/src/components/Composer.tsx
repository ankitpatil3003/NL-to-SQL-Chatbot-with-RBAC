"use client";

import { useEffect, useRef, useState } from "react";

import { SendIcon, StopIcon } from "./icons";

const MAX_CHARS = 2000;

export default function Composer({
  onSend,
  onStop,
  busy,
  autoFocus,
}: {
  onSend: (text: string) => void;
  onStop: () => void;
  busy: boolean;
  autoFocus?: boolean;
}) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [text]);

  const send = () => {
    const value = text.trim();
    if (!value || busy) return;
    onSend(value);
    setText("");
  };

  return (
    <div className="rounded-2xl border border-border bg-bg-elevated px-3 py-2 shadow-sm focus-within:border-fg-muted">
      <textarea
        ref={ref}
        value={text}
        autoFocus={autoFocus}
        rows={1}
        maxLength={MAX_CHARS}
        placeholder="Ask about sales, market share, accounts, territories…"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            send();
          }
        }}
        className="block w-full resize-none bg-transparent px-1 py-1.5 outline-none placeholder:text-fg-muted"
      />
      <div className="flex items-center justify-between pt-1">
        <span className="text-xs text-fg-muted">
          {text.length > MAX_CHARS * 0.8 ? `${text.length}/${MAX_CHARS}` : "Enter to send · Shift+Enter for a new line"}
        </span>
        {busy ? (
          <button
            onClick={onStop}
            title="Stop streaming (the answer is still saved)"
            className="rounded-lg bg-fg p-2 text-bg hover:opacity-90"
          >
            <StopIcon width={16} height={16} />
          </button>
        ) : (
          <button
            onClick={send}
            disabled={!text.trim()}
            title="Send"
            className="rounded-lg bg-accent p-2 text-accent-fg hover:opacity-90 disabled:opacity-40"
          >
            <SendIcon width={16} height={16} />
          </button>
        )}
      </div>
    </div>
  );
}
