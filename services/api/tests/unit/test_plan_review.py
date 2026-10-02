from app.nl2sql.plan import read_response
from app.nl2sql.types import AnalysisPlan, PlanQuestion

PLAN = AnalysisPlan(
    summary="s", metric="m", filters=[], breakdown="b", time_window="t", rules=[],
    open_questions=[
        PlanQuestion(question="Growth as?", options=["Absolute", "Percent"]),
        PlanQuestion(question="Compared to?", options=["Prior quarter", "Prior year"]),
    ],
    confidence="medium",
)  # fmt: skip


def test_approving_as_proposed_changes_nothing() -> None:
    review = read_response(PLAN, {})
    assert not review.changed and not review.corrected
    assert review.feedback == [
        "Growth as? -> Absolute (decided; don't ask again)",
        "Compared to? -> Prior quarter (decided; don't ask again)",
    ]


def test_a_changed_choice_settles_every_question() -> None:
    review = read_response(PLAN, {"answers": {"Growth as?": "Percent"}})
    assert review.changed and not review.corrected
    assert review.feedback[0].startswith("Growth as? -> Percent")
    assert review.feedback[1].startswith("Compared to? -> Prior quarter")  # default, settled


def test_typed_correction_is_kept_and_flagged() -> None:
    review = read_response(PLAN, {"answers": {"Unknown?": "x"}, "feedback": " use equivalents "})
    assert review.changed and review.corrected and review.feedback[-1] == "use equivalents"
    assert not any("Unknown?" in f for f in review.feedback)  # only the plan's own questions


def test_default_annotations_are_stripped_from_options() -> None:
    from app.nl2sql.plan import _ANNOTATION

    for raw in [f"Q2 vs Q1 (2026) {chr(0x2013)} used in this plan", "Absolute (used in this plan)"]:
        assert "plan" not in _ANNOTATION.sub("", raw)
    assert _ANNOTATION.sub("", "Plan B") == "Plan B"  # ordinary text untouched


def test_more_annotation_styles() -> None:
    from app.nl2sql.plan import _ANNOTATION

    for raw in [
        "QoQ (this vs last) [used in this plan]",
        "Units (default)",
        "Units - assumed by the plan",
    ]:
        assert _ANNOTATION.sub("", raw).strip() in {"QoQ (this vs last)", "Units"}
    assert _ANNOTATION.sub("", "Prior year (same quarter)") == "Prior year (same quarter)"
