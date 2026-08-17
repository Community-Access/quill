"""The platform scorecard (polish.md P5.4): the roster stays honest.

The tool exists because a gate that is written but not wired in is invisible
(GATE-40 was exactly that for months). These tests keep the scorecard itself
from acquiring the same disease.
"""

from __future__ import annotations

from quill.tools.platform_report import GATES, GateResult, render_markdown


def test_roster_names_are_unique_and_runnable_shapes() -> None:
    names = [g.name for g in GATES]
    assert len(names) == len(set(names))
    for gate in GATES:
        assert gate.protects  # every row explains itself to the reader
        assert len(gate.argv) >= 2


def test_known_gate_modules_are_on_the_roster() -> None:
    """Every quill.tools CI gate module is either rostered or exempt with a
    reason — a new gate module must join the scorecard or be named here."""
    from pathlib import Path

    tools = Path("quill/tools")
    gate_modules = {
        p.stem
        for p in tools.glob("*.py")
        if "audit" in p.stem or "check" in p.stem or p.stem.endswith("_contract")
    }
    rostered = " ".join(" ".join(g.argv) for g in GATES)
    exempt = {
        # Release-time only: needs network (PyPI) and the whole dependency set.
        "check_version_consistency",
        # Data checker for the persistence layer, run by its own tests.
        "persistence_audit",
    }
    missing = {m for m in gate_modules if m not in exempt and m not in rostered}
    assert missing == set(), (
        f"gate modules absent from the platform_report roster: {sorted(missing)} "
        "— add them to GATES or to this test's exempt set with a reason."
    )


def test_render_marks_failures_loudly() -> None:
    ok = GateResult(GATES[0], True, 0.1, "")
    bad = GateResult(GATES[1], False, 0.2, "boom line")
    text = render_markdown([ok, bad])
    assert "1 FAILING" in text
    assert "**FAIL**" in text
    assert "boom line" in text


def test_render_all_green_says_so() -> None:
    text = render_markdown([GateResult(g, True, 0.0, "") for g in GATES])
    assert "All green." in text
    assert "FAIL" not in text
