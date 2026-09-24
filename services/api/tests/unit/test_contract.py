from app.knowledge.contract import Catalog, contract_blocks, load_contract, render_contract

from .test_sqlguard import EXEC, RAM

CATALOG = Catalog(
    products=[
        ("ZENOVAX", 1, "Oncology", "Taxanes", "Docetaxel"),
        ("TAXOTERE", 0, "Oncology", "Taxanes", "Docetaxel"),
    ],
    territories=[("New York Metro", "Northeast"), ("New England", "Northeast")],
    gpos=["ION", "Onmark"],
    archetypes=["Hospital"],
)


def test_contract_loads_with_unique_ids_and_stable_hash() -> None:
    contract = load_contract()
    ids = [r.id for r in contract.rules]
    assert len(ids) == len(set(ids)) and len(ids) >= 20
    assert len(contract.content_hash) == 12
    assert set(contract.tables) == {"sales", "organizations", "products", "zip_territory"}
    assert "users" not in contract.tables  # never described to the model


def test_rendered_contract_contains_every_rule_and_the_catalogue() -> None:
    contract = load_contract()
    rendered = render_contract(contract, CATALOG)
    for rule in contract.rules:
        assert f"[{rule.id}]" in rendered
    assert contract.content_hash in rendered
    assert "ZENOVAX (Docetaxel, Taxanes, Oncology)" in rendered
    assert "Northeast: New York Metro, New England" in rendered


def test_scope_block_is_per_user_and_not_cached() -> None:
    contract = load_contract()
    shared_ram, scope_ram = contract_blocks(contract, CATALOG, RAM)
    shared_exec, scope_exec = contract_blocks(contract, CATALOG, EXEC)
    assert shared_ram == shared_exec and shared_ram.cache  # one cache entry for everyone
    assert not scope_ram.cache
    assert "may NOT see WAC" in scope_ram.text and "New York Metro" in scope_ram.text
    assert "MAY see WAC" in scope_exec.text
