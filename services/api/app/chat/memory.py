"""Cross-session memory: one short markdown profile per user (what they ask about, how they like
answers), updated by the assistant after answered turns and given to every chat's understanding
and planning steps. Users can read, edit and clear it. Preferences only: it never grants access,
which is always resolved from public.users and enforced by the database."""

from app.llm.base import LLMRequest, Message, SystemBlock
from app.llm.router import LLMRouter
from app.nl2sql.prompts import prompt
from app.nl2sql.types import TurnResult

MAX_CHARS = 2000


async def updated_memory(llm: LLMRouter, current: str, question: str, result: TurnResult) -> str:
    plan = (result.plan or {}).get("summary", "")
    turn = [f"Latest question: {question}"]
    if result.standalone_question and result.standalone_question != question:
        turn.append(f"Understood as: {result.standalone_question}")
    if plan:
        turn.append(f"Computed: {plan}")
    if result.assumptions:
        turn.append("Assumptions: " + "; ".join(result.assumptions))
    routed = await llm.complete(
        LLMRequest(
            task="memory",
            system=[SystemBlock(prompt("memory"), cache=True)],
            messages=[
                Message(
                    "user",
                    f"Current profile:\n{current or '(empty)'}\n\n" + "\n".join(turn),
                )
            ],
            max_tokens=800,
            temperature=0.0,
        )
    )
    return routed.response.text.strip()[:MAX_CHARS]
