"""Long chats: the conversation goes to the model verbatim while it fits; past COMPACT_AT of the
history budget, the older turns are folded into a rolling summary kept on the chat (the newest
KEEP_RECENT turns stay verbatim), so the same chat can go on indefinitely. The structured state a
follow-up needs most (the previous question's SQL and plan) always travels with the newest turn."""

from app.llm.base import LLMRequest, Message, SystemBlock
from app.llm.router import LLMRouter
from app.nl2sql.prompts import prompt
from app.nl2sql.types import HistoryTurn
from app.nl2sql.understand import render_history

HISTORY_BUDGET_TOKENS = 6000  # what the understanding step may spend on the conversation
COMPACT_AT = 0.7
KEEP_RECENT = 4


def estimate_tokens(text: str) -> int:
    return len(text) // 4  # ~4 chars per token for English; a budget check, not a meter


def needs_compaction(summary: str, recent: list[HistoryTurn]) -> bool:
    size = estimate_tokens(summary) + estimate_tokens(render_history(recent))
    return len(recent) > KEEP_RECENT and size > COMPACT_AT * HISTORY_BUDGET_TOKENS


async def fold(llm: LLMRouter, summary: str, turns: list[HistoryTurn]) -> str:
    routed = await llm.complete(
        LLMRequest(
            task="compact",
            system=[SystemBlock(prompt("compact"), cache=True)],
            messages=[
                Message(
                    "user",
                    f"Existing summary:\n{summary or '(none)'}\n\n"
                    f"Older turns to fold in:\n{render_history(turns)}",
                )
            ],
            max_tokens=700,
            temperature=0.0,
        )
    )
    return routed.response.text.strip()
