"""Data passed between pipeline stages. LLM output models are strict (every field required) so
they work with JSON-schema structured output on every provider."""

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# --- LLM outputs --------------------------------------------------------------------------------


class Mention(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["drug", "territory", "region", "gpo", "account", "market", "other"]
    text: str


class Understanding(BaseModel):
    """Stage 1: one call that routes the turn and rewrites follow-ups into standalone questions."""

    model_config = ConfigDict(extra="forbid")
    intent: Literal["data_question", "clarify", "smalltalk", "out_of_scope"]
    standalone_question: str
    is_follow_up: bool
    asks_for_dollars: bool
    mentions: list[Mention]
    reply: str  # the message to send when intent != data_question; otherwise ""
    # Chat title (used on a chat's first turn). Structured output keeps reasoning models from
    # leaking their thinking into it, which a separate plain-text title call did.
    title: str


class PlanQuestion(BaseModel):
    """A choice that would change the numbers. options[0] is what the plan assumes by default."""

    model_config = ConfigDict(extra="forbid")
    question: str
    options: list[str]


class AnalysisPlan(BaseModel):
    """Plan-then-generate: what will be computed, in business language, before any SQL. It is
    what a human reviews when the turn pauses, and what the SQL step must follow."""

    model_config = ConfigDict(extra="forbid")
    summary: str  # one sentence: "Paid demand units of ZENOVAX by territory, Jun-Aug 2026"
    metric: str
    filters: list[str]
    breakdown: str
    time_window: str
    rules: list[str]  # business rule ids the computation follows
    open_questions: list[PlanQuestion]  # only genuine ambiguities; usually empty
    confidence: Literal["high", "medium", "low"]


class SqlDraft(BaseModel):
    """Stage 2: the generated query plus what the model assumed."""

    model_config = ConfigDict(extra="forbid")
    answerable: bool
    sql: str
    rules_applied: list[str]
    assumptions: list[str]
    unanswerable_reason: str


# --- Conversation ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HistoryTurn:
    question: str
    answer: str
    sql: str | None = None


# --- Pipeline results and events ---------------------------------------------------------------

# needs_input: the turn paused for the user (plan review); the chat resumes it.
TurnStatus = Literal["answered", "clarification", "refused", "error", "needs_input"]


@dataclass(slots=True)
class ResultTable:
    columns: list[str]
    rows: list[list[Any]]
    truncated: bool  # rows holds fewer than row_count
    row_count: int  # every row the query returns (counted when the inline rows were capped)


@dataclass(slots=True)
class TurnResult:
    status: TurnStatus
    answer: str
    standalone_question: str | None = None
    sql: str | None = None
    query: str | None = None  # the validated SQL before the row cap: paging and export re-run it
    table: ResultTable | None = None
    assumptions: list[str] = field(default_factory=list)
    rules_applied: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # e.g. scope limits, dollars not available
    trace_id: str | None = None
    title: str | None = None  # suggested chat title (from query understanding)
    plan: dict[str, Any] | None = None  # the AnalysisPlan the answer followed
    review: dict[str, Any] | None = None  # what the user is asked, when status == needs_input
    confidence: str | None = None  # high | medium | low: candidate agreement and checks


@dataclass(frozen=True, slots=True)
class Event:
    """Streamed to the UI: stage progress, then partial answer text, then the final result."""

    type: Literal["stage", "answer_delta", "result"]
    data: Any
