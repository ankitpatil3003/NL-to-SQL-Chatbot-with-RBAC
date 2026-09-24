import re

from app.knowledge.contract import load_contract
from app.knowledge.fewshots import load_examples


def test_examples_are_consistent_with_the_contract_and_wac_policy() -> None:
    examples = load_examples()
    rule_ids = {r.id for r in load_contract().rules}
    assert len(examples) >= 30
    assert len({e.question.lower() for e in examples}) == len(examples)
    for e in examples:
        assert set(e.rules) <= rule_ids, (e.id, set(e.rules) - rule_ids)
        uses_wac = re.search(r"\bwac\b", e.sql, re.IGNORECASE) is not None
        assert uses_wac == e.exec_only, f"{e.id}: exec_only must be set iff the SQL uses wac"
