from __future__ import annotations

from roboqc_agent.policy import FrictionPolicyEngine
from roboqc_agent.schemas import DefectClass
from roboqc_agent.taxonomy import TAXONOMY, taxonomy_table


def test_taxonomy_covers_all_ten_classes() -> None:
    assert set(TAXONOMY) == set(DefectClass)


def test_taxonomy_always_escalate_matches_policy() -> None:
    escalating = {cls for cls, entry in TAXONOMY.items() if entry.always_escalate}
    assert escalating == set(FrictionPolicyEngine.always_escalate_defects)


def test_taxonomy_table_lists_every_class() -> None:
    table = taxonomy_table()
    for cls in DefectClass:
        assert cls.value in table
