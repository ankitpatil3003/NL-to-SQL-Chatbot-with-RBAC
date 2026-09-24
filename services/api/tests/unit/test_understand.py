from app.nl2sql.types import HistoryTurn, Mention, Understanding
from app.nl2sql.understand import ANSWER_CHARS, HISTORY_TURNS, render_history, understand

from ..fakes import scripted_router
from .test_sqlguard import RAM


def test_history_is_bounded_and_answers_truncated() -> None:
    history = [HistoryTurn(f"q{i}", "x" * (ANSWER_CHARS + 50)) for i in range(HISTORY_TURNS + 3)]
    rendered = render_history(history)
    assert "q0" not in rendered and f"q{HISTORY_TURNS + 2}" in rendered
    assert "x" * ANSWER_CHARS + "..." in rendered
    assert render_history([]) == "(no earlier messages)"


async def test_understand_sends_history_and_returns_validated_model() -> None:
    llm, fake = scripted_router()
    expected = Understanding(
        intent="data_question", standalone_question="Top 5 accounts this quarter by month",
        is_follow_up=True, asks_for_dollars=False, mentions=[Mention(kind="other", text="month")], reply="", title="Top Accounts by Month",
    )  # fmt: skip
    fake.add("router", expected)
    history = [HistoryTurn("What are my top 5 accounts this quarter?", "Goldcrest leads...")]
    result, routed = await understand(llm, "now by month", history, RAM)
    assert result == expected and routed.response.provider == "fake"
    sent = fake.last("router").messages[0].content
    assert "What are my top 5 accounts this quarter?" in sent and sent.endswith("now by month")
    assert "data scope: New York Metro territory" in sent
