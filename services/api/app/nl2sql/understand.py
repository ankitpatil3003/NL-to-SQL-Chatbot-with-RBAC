"""Stage 1, query understanding: one LLM call that routes the turn (data question, clarification,
small talk, out of scope) and rewrites follow-ups into standalone questions. Merging routing and
rewriting saves a round trip on every turn, which matters with free-tier rate limits."""

from app.llm.base import LLMRequest, Message, SystemBlock
from app.llm.router import LLMRouter, RoutedResponse
from app.nl2sql.prompts import prompt
from app.nl2sql.types import HistoryTurn, Understanding

HISTORY_TURNS = 4
ANSWER_CHARS = 500  # earlier answers are context, not content: truncate


def render_history(history: list[HistoryTurn]) -> str:
    if not history:
        return "(no earlier messages)"
    lines = []
    for turn in history[-HISTORY_TURNS:]:
        lines.append(f"User: {turn.question}")
        answer = (
            turn.answer if len(turn.answer) <= ANSWER_CHARS else turn.answer[:ANSWER_CHARS] + "..."
        )
        lines.append(f"Assistant: {answer}")
    return "\n".join(lines)


async def understand(
    llm: LLMRouter, question: str, history: list[HistoryTurn]
) -> tuple[Understanding, RoutedResponse]:
    request = LLMRequest(
        task="router",
        system=[SystemBlock(prompt("understand"), cache=True)],
        messages=[
            Message(
                "user",
                f"Conversation so far:\n{render_history(history)}\n\nLatest message:\n{question}",
            )
        ],
        max_tokens=1200,
        output=Understanding,
    )
    routed = await llm.complete(request)
    assert isinstance(routed.response.data, Understanding)
    return routed.response.data, routed
