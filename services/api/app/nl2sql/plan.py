"""Plan-then-generate: an AnalysisPlan in business language before any SQL. The SQL step must
follow it, and a human can review it when the turn pauses (human in the loop: nl2sql/graph.py)."""

import re
from dataclasses import dataclass

from app.knowledge.base import KnowledgeBase
from app.knowledge.contract import contract_blocks
from app.llm.base import LLMRequest, Message, SystemBlock
from app.llm.router import LLMRouter, RoutedResponse
from app.nl2sql.prompts import prompt
from app.nl2sql.types import AnalysisPlan
from app.rbac.context import UserContext


async def make_plan(
    llm: LLMRouter,
    kb: KnowledgeBase,
    user: UserContext,
    context: str,
    feedback: list[str],
) -> tuple[AnalysisPlan, RoutedResponse]:
    content = context
    if feedback:
        content += "\n\n## Reviewer feedback (follow it)\n" + "\n".join(f"- {f}" for f in feedback)
    routed = await llm.complete(
        LLMRequest(
            task="plan",
            system=[
                SystemBlock(prompt("plan"), cache=True),
                *contract_blocks(kb.contract, kb.catalog, user),
            ],
            messages=[Message("user", content)],
            max_tokens=2000,
            output=AnalysisPlan,
        )
    )
    plan = routed.response.data
    assert isinstance(plan, AnalysisPlan)
    for q in plan.open_questions:  # models annotate their default despite the prompt
        q.options = [_ANNOTATION.sub("", o).strip() for o in q.options]
    return plan, routed


# A trailing note marking the default: " - used in this plan", "(default)", "[assumed by the plan]"
_ANNOTATION = re.compile(
    r"\s*(?:[-\u2013\u2014]\s*|[(\[])[^()\[\]]*"
    r"\b(?:(?:this|the) plan|default)\b[^()\[\]]*[)\]]?\s*$",
    re.I,
)


def render_plan(plan: AnalysisPlan, *, reviewed: bool) -> str:
    """The plan as context for the SQL step."""
    status = "approved by the user" if reviewed else "proposed; not reviewed"
    lines = [
        f"## Analysis plan ({status}): implement exactly this",
        f"- Summary: {plan.summary}",
        f"- Metric: {plan.metric}",
        f"- Filters: {'; '.join(plan.filters) or 'none'}",
        f"- Breakdown: {plan.breakdown}",
        f"- Time window: {plan.time_window}",
        f"- Rules: {', '.join(plan.rules) or 'none'}",
    ]
    for q in plan.open_questions:  # unresolved: use the plan's default reading
        lines.append(
            f'- Assume for "{q.question}": {q.options[0] if q.options else "the usual reading"}'
        )
    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class Review:
    """A reviewer's response, read against the plan they saw."""

    feedback: list[str]  # every open question settled (choice or default), then any correction
    changed: bool  # anything differs from the plan as proposed: re-plan
    corrected: bool  # the user typed a correction: show them the revised plan


def read_response(plan: AnalysisPlan, response: dict[str, object]) -> Review:
    """Answering the card settles every open question: an unanswered one keeps its default, so
    the re-plan doesn't ask it again."""
    answers = response.get("answers")
    answers = answers if isinstance(answers, dict) else {}
    feedback, changed = [], False
    for q in plan.open_questions:
        default = q.options[0] if q.options else ""
        choice = answers.get(q.question)
        choice = choice.strip() if isinstance(choice, str) and choice.strip() else default
        changed |= choice != default
        feedback.append(f"{q.question} -> {choice} (decided; don't ask again)")
    text = response.get("feedback")
    corrected = isinstance(text, str) and bool(text.strip())
    if corrected:
        feedback.append(str(text).strip())
    return Review(feedback, changed or corrected, corrected)
