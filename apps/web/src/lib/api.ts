// Typed client for the FastAPI backend. Same origin (/api/*): the ALB routes it in AWS and a
// Next.js rewrite does locally, so the httpOnly session cookie just works.

export type Role = "exec" | "director" | "ram";

export interface Me {
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
  territory: string | null;
  region: string | null;
  scope_label: string;
  can_view_wac: boolean;
}

export interface DemoAccount {
  email: string;
  full_name: string;
  role: Role;
  scope_label: string;
}

export interface SessionSummary {
  session_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export type Row = (string | number | null)[];

export interface ResultTable {
  columns: string[];
  rows: Row[]; // inline rows: all of them unless truncated
  truncated: boolean;
  row_count: number; // every row the query returns
}

// needs_input: the turn paused for the user to review its analysis plan (resume it to continue).
export type TurnStatus = "answered" | "clarification" | "refused" | "error" | "needs_input";

export interface AnalysisPlan {
  summary: string;
  metric: string;
  filters: string[];
  breakdown: string;
  time_window: string;
  rules: string[];
  open_questions: { question: string; options: string[] }[]; // options[0] = the plan's default
  confidence: "high" | "medium" | "low";
}

export interface PlanReview {
  kind: "plan_review";
  reason: "ambiguous" | "requested";
  plan: AnalysisPlan;
}

/** Independent SQL candidates disagreed: each option is one reading of the question. */
export interface DisagreementReview {
  kind: "disagreement";
  options: { label: string; columns: string[]; preview: Row[]; row_count: number }[];
}

/** The user's response to a plan review. Empty = run the plan as proposed. */
export interface ReviewResponse {
  answers?: Record<string, string>;
  feedback?: string;
  choice?: number; // the reading picked, for a disagreement
}

export interface AssistantPayload {
  status: TurnStatus;
  standalone_question: string | null;
  sql: string | null;
  table: ResultTable | null;
  assumptions: string[];
  rules_applied: string[];
  notes: string[];
  trace_id: string | null;
  plan?: AnalysisPlan | null; // what the answer computed
  review?: PlanReview | DisagreementReview | null; // when status is needs_input
  confidence?: "high" | "medium" | "low" | null; // candidate agreement + rule checks
  artifact?: { id: string; version: number; title: string } | null; // see lib/artifacts.ts
}

export interface ChatMessage {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  payload: AssistantPayload | null;
  created_at: string;
}

export interface SessionDetail extends SessionSummary {
  messages: ChatMessage[];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
    credentials: "same-origin",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  me: () => request<Me>("/api/auth/me"),
  login: (email: string, password: string) =>
    request<Me>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  demoAccounts: () =>
    request<{ password: string | null; accounts: DemoAccount[] }>("/api/auth/demo-accounts"),
  sessions: () => request<SessionSummary[]>("/api/chat/sessions"),
  session: (id: string) => request<SessionDetail>(`/api/chat/sessions/${id}`),
  rename: (id: string, title: string) =>
    request<void>(`/api/chat/sessions/${id}`, { method: "PATCH", body: JSON.stringify({ title }) }),
  remove: (id: string) => request<void>(`/api/chat/sessions/${id}`, { method: "DELETE" }),
  /** One page of a result beyond its inline rows (the stored query re-run as this user). */
  rows: (messageId: string, offset: number, limit: number) =>
    request<{ columns: string[]; rows: Row[]; offset: number }>(
      `/api/chat/messages/${messageId}/rows?offset=${offset}&limit=${limit}`,
    ),
  exportUrl: (messageId: string) => `/api/chat/messages/${messageId}/export`,
  memory: () => request<{ content: string; updated_at: string | null }>("/api/chat/memory"),
  saveMemory: (content: string) =>
    request<void>("/api/chat/memory", { method: "PUT", body: JSON.stringify({ content }) }),
  clearMemory: () => request<void>("/api/chat/memory", { method: "DELETE" }),
};

// --- Streaming turn (server-sent events over a POST) --------------------------------------------

export type StreamEvent =
  | { event: "session"; data: { session_id: string } }
  | { event: "stage"; data: { name: string } }
  | { event: "answer_delta"; data: { text: string } }
  | { event: "result"; data: AssistantPayload & { message_id: string; answer: string } }
  | { event: "title"; data: { title: string } }
  | { event: "done"; data: Record<string, never> }
  | { event: "error"; data: { message: string } };

/** POST a question and yield server-sent events as they arrive. (EventSource can't POST.)
 * `review`: pause for the user to approve the analysis plan before it runs. */
export function streamTurn(
  message: string,
  sessionId: string | null,
  signal?: AbortSignal,
  review = false,
): AsyncGenerator<StreamEvent> {
  const body = { message, review, ...(sessionId ? { session_id: sessionId } : {}) };
  return streamPost("/api/chat/stream", body, signal);
}

/** Answer a paused turn's plan review; the turn continues and streams like streamTurn. */
export function streamResume(
  sessionId: string,
  response: ReviewResponse,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  return streamPost(`/api/chat/sessions/${sessionId}/resume`, response, signal);
}

async function* streamPost(path: string, body: object, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : res.statusText);
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      let name = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) name = line.slice(7);
        else if (line.startsWith("data: ")) data.push(line.slice(6));
      }
      if (data.length) yield { event: name, data: JSON.parse(data.join("\n")) } as StreamEvent;
    }
  }
}
