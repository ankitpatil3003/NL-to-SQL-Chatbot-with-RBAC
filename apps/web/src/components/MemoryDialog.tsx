"use client";

import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";

/** What the assistant remembers about the user across chats: theirs to read, edit and clear. */
export default function MemoryDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [content, setContent] = useState("");
  const [status, setStatus] = useState<"loading" | "ready" | "saving" | "error">("loading");

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (!open) {
      dialog.close();
      return;
    }
    dialog.showModal();
    api
      .memory()
      .then((m) => {
        setContent(m.content);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, [open]);

  const save = async (value: string) => {
    setStatus("saving");
    try {
      await (value.trim() ? api.saveMemory(value) : api.clearMemory());
      setContent(value.trim());
      onClose();
    } catch {
      setStatus("error");
    }
  };

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      className="m-auto w-[min(36rem,calc(100vw-2rem))] rounded-2xl border border-border bg-bg-elevated p-0 text-fg shadow-xl backdrop:bg-black/40"
    >
      <div className="p-5">
        <h2 className="text-lg font-semibold">Memory</h2>
        <p className="mt-1 text-sm text-fg-secondary">
          What the assistant has learned from your questions, used in every chat to understand you faster. It never
          changes what data you can see.
        </p>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          maxLength={2000}
          rows={10}
          disabled={status === "loading"}
          placeholder={status === "loading" ? "Loading…" : "Nothing yet. It fills in as you ask questions."}
          aria-label="Memory"
          className="mt-4 w-full resize-y rounded-lg border border-border bg-transparent p-3 font-mono text-sm outline-none focus:border-fg-muted"
        />
        {status === "error" && <p className="mt-2 text-sm text-danger">Couldn&apos;t load or save your memory.</p>}
        <div className="mt-4 flex items-center gap-2">
          <button
            onClick={() => save("")}
            disabled={status !== "ready" || !content}
            className="rounded-lg px-3 py-1.5 text-sm text-danger hover:bg-bg-muted disabled:opacity-40"
          >
            Clear memory
          </button>
          <span className="flex-1" />
          <button onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-fg-secondary hover:bg-bg-muted">
            Cancel
          </button>
          <button
            onClick={() => save(content)}
            disabled={status !== "ready"}
            className="rounded-lg bg-accent px-4 py-1.5 text-sm font-medium text-accent-fg hover:opacity-90 disabled:opacity-40"
          >
            Save
          </button>
        </div>
      </div>
    </dialog>
  );
}
