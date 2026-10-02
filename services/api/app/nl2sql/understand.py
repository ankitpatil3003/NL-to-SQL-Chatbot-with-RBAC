"""Stage 1, query understanding: one LLM call that routes the turn (data question, clarification,
small talk, out of scope) and rewrites follow-ups into standalone questions. Merging routing and
rewriting saves a round trip on every turn, which matters with free-tier rate limits."""

from app.llm.base import LLMRequest, Message, SystemBlock
from app.llm.router import LLMRouter, RoutedResponse
from app.nl2sql.prompts import prompt
from app.nl2sql.types import HistoryTurn, Understanding
from app.rbac.context import UserContext

ANSWER_CHARS = 1200  # earlier answers are context, not content: truncate very long ones


def render_history(history: list[HistoryTurn]) -> str:
    """The turns given, verbatim. How many fit is decided upstream (chat/compaction.py)."""
    if not history:
        return "(no earlier messages)"
    lines = []
    for turn in history:
        lines.append(f"User: {turn.question}")
        answer = (
            turn.answer if len(turn.answer) <= ANSWER_CHARS else turn.answer[:ANSWER_CHARS] + "..."
        )
        lines.append(f"Assistant: {answer}")
    return "\n".join(lines)


def render_background(summary: str, memory: str) -> str:
    """Context from beyond the visible turns: this chat's compacted start, and the user's
    cross-session memory. Both inform interpretation only; access is enforced elsewhere."""
    parts = []
    if memory:
        parts.append(
            "What you know about this user from earlier chats (preferences, not permissions):\n"
            + memory
        )
    if summary:
        parts.append(f"Summary of the earlier part of this chat:\n{summary}")
    return "\n\n".join(parts)


async def understand(
    llm: LLMRouter,
    question: str,
    history: list[HistoryTurn],
    user: UserContext,
    *,
    summary: str = "",
    memory: str = "",
) -> tuple[Understanding, RoutedResponse]:
    # Who is asking resolves "my region", "my territory", "my accounts". Without it, the eval
    # showed "Rank the territories in my region" from a Director being sent back as a
    # clarification (eval 20260924-175138).
    who = f"{user.role.value}; data scope: {user.scope_label}"
    background = render_background(summary, memory)
    background = f"{background}\n\n" if background else ""
    request = LLMRequest(
        task="router",
        system=[SystemBlock(prompt("understand"), cache=True)],
        messages=[
            Message(
                "user",
                f"User: {who}\n\n{background}"
                f"Conversation so far:\n{render_history(history)}\n\n"
                f"Latest message:\n{question}",
            )
        ],
        max_tokens=1200,
        output=Understanding,
    )
    routed = await llm.complete(request)
    assert isinstance(routed.response.data, Understanding)
    return routed.response.data, routed
