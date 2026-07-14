"""Golden snapshots for verbosity output (§42).

These pin the exact, user-observable output of the engine and the QVP install
flow so an accidental wording or routing change is caught in review. The expected
values are embedded inline (the "golden" record); update them deliberately when
the behavior is meant to change.
"""

from __future__ import annotations

from quill.core.verbosity.engine import VerbosityEngine
from quill.core.verbosity.preview import BUILTIN_SCENARIOS, preview_scenario
from quill.core.verbosity.profiles import EXPERT, NORMAL
from quill.core.verbosity.qvp import KIND, install_pack


def _scenario(scenario_id: str):
    return next(s for s in BUILTIN_SCENARIOS if s.id == scenario_id)


_VALID_PACK = {
    "schema_version": "1",
    "kind": KIND,
    "min_quill_version": "0.7.0",
    "pack": {
        "name": "Concise Nav",
        "author": "Kelly Ford",
        "description": "Tighter navigation announcements.",
        "version": "1.0",
        "license": "MIT",
    },
    "templates": [
        {
            "id": "concise.next_line",
            "name": "Concise next line",
            "applies_to": "nav.next_line",
            "template": "L{line}",
        }
    ],
}


def test_golden_qvp_install_spoken_sequence() -> None:
    result = install_pack(_VALID_PACK, current_version="0.7.0")
    assert result.spoken_sequence == (
        "Validating pack.",
        "Minimum QUILL version 0.7.0, you have 0.7.0. OK.",
        "Pack installed. 1 template added. Author: Kelly Ford.",
    )


def test_golden_save_file_normal() -> None:
    out = preview_scenario(_scenario("save_file"), VerbosityEngine(profile=NORMAL))
    assert (out.speech, out.braille, out.visual) == (
        "Saved report.md",
        "Saved report.md",
        "Saved report.md",
    )
    assert out.sound_event == "verbosity.doc.save"
    assert out.channels == "speech, braille, sound, visual"
    assert out.suppressed == ""


def test_golden_search_results_expert_suppressed() -> None:
    # Expert hides routine confirmations (search.find); errors still speak.
    out = preview_scenario(_scenario("search_results"), VerbosityEngine(profile=EXPERT))
    assert out.speech == ""
    assert out.suppressed == "Found 12"
    assert out.braille == "Found 12"
    assert out.sound_event is None


def test_golden_long_document_navigation_normal() -> None:
    out = preview_scenario(_scenario("long_document_navigation"), VerbosityEngine(profile=NORMAL))
    assert out.speech == "Line 128"
    assert out.visual == "Line 128"


def test_golden_print_page_navigation_normal() -> None:
    out = preview_scenario(_scenario("print_page_navigation"), VerbosityEngine(profile=NORMAL))
    assert out.speech == "Page 7"


def test_golden_error_state_normal_speaks() -> None:
    out = preview_scenario(_scenario("error_state"), VerbosityEngine(profile=NORMAL))
    assert out.speech == "Disk full"
    assert out.sound_event == "verbosity.system.error"
