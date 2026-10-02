from app.nl2sql.types import HistoryTurn, Mention, Understanding
from app.nl2sql.understand import ANSWER_CHARS, render_history, understand

from ..fakes import scripted_router
from .test_sqlguard import RAM


def test_history_renders_every_turn_given_and_truncates_long_answers() -> None:
    history = [HistoryTurn(f"q{i}", "x" * (ANSWER_CHARS + 50)) for i in range(7)]
    rendered = render_history(history)  # how many turns fit is compaction's job, upstream
    assert "q0" in rendered and "q6" in rendered
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


async def test_memory_and_summary_reach_the_prompt() -> None:
    llm, fake = scripted_router()
    fake.add("router", Understanding(intent="smalltalk", standalone_question="hi", is_follow_up=False,
                                     asks_for_dollars=False, mentions=[], reply="Hi", title="Hi"))  # fmt: skip
    await understand(llm, "hi", [], RAM, summary="Earlier: ZENOVAX share by territory.",
                     memory="## Preferences\n- prefers equivalents")  # fmt: skip
    sent = fake.last("router").messages[0].content
    assert "prefers equivalents" in sent and "preferences, not permissions" in sent
    assert "Earlier: ZENOVAX share by territory." in sent
