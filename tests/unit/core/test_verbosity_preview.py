"""Tests for the scenario-based preview renderer (§23)."""

from __future__ import annotations

from quill.core.verbosity.engine import VerbosityEngine
from quill.core.verbosity.preview import (
    BUILTIN_SCENARIOS,
    preview_all,
    preview_scenario,
)
from quill.core.verbosity.profiles import EXPERT, NORMAL


def test_fourteen_builtin_scenarios() -> None:
    assert len(BUILTIN_SCENARIOS) == 14
    ids = [s.id for s in BUILTIN_SCENARIOS]
    assert len(ids) == len(set(ids))


def test_every_scenario_uses_a_real_verb() -> None:
    from quill.core.verbosity.registry import default_registry

    registry = default_registry()
    for scenario in BUILTIN_SCENARIOS:
        assert registry.get(scenario.verb_id) is not None, scenario.id


def test_preview_all_returns_one_output_per_scenario() -> None:
    outputs = preview_all(VerbosityEngine(profile=NORMAL))
    assert len(outputs) == len(BUILTIN_SCENARIOS)


def test_preview_surfaces_per_channel_output() -> None:
    engine = VerbosityEngine(profile=NORMAL)
    save = next(s for s in BUILTIN_SCENARIOS if s.id == "save_file")
    out = preview_scenario(save, engine)
    assert out.speech == "Saved report.md"
    assert out.braille == "Saved report.md"
    assert out.visual == "Saved report.md"
    assert out.profile == "Normal"
    assert out.channels == "speech, braille, sound, visual"


def test_preview_shows_suppression_under_expert() -> None:
    engine = VerbosityEngine(profile=EXPERT)
    # search.find is a ROUTINE confirmation, which Expert suppresses.
    search = next(s for s in BUILTIN_SCENARIOS if s.id == "search_results")
    out = preview_scenario(search, engine)
    assert out.speech == ""
    assert out.suppressed == "Found 12"
    assert out.visual == "Found 12"  # floor remains


def test_error_scenario_always_speaks() -> None:
    out = preview_scenario(
        next(s for s in BUILTIN_SCENARIOS if s.id == "error_state"),
        VerbosityEngine(profile=EXPERT),
    )
    assert out.speech == "Disk full"
    assert out.suppressed == ""
