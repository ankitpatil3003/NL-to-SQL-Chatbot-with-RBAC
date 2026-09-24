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

TurnStatus = Literal["answered", "clarification", "refused", "error"]


@dataclass(slots=True)
class ResultTable:
    columns: list[str]
    rows: list[list[Any]]
    truncated: bool
    row_count: int


@dataclass(slots=True)
class TurnResult:
    status: TurnStatus
    answer: str
    standalone_question: str | None = None
    sql: str | None = None
    table: ResultTable | None = None
    assumptions: list[str] = field(default_factory=list)
    rules_applied: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # e.g. scope limits, dollars not available
    trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class Event:
    """Streamed to the UI: stage progress, then partial answer text, then the final result."""

    type: Literal["stage", "answer_delta", "result"]
    data: Any
