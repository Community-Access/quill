"""Tests for the explanation trace (§25)."""

from __future__ import annotations

from quill.core.verbosity.engine import VerbosityEngine
from quill.core.verbosity.explain import ExplanationTrace
from quill.core.verbosity.profiles import EXPERT, NORMAL


def test_engine_attaches_full_trace() -> None:
    result = VerbosityEngine(profile=NORMAL).speak(
        "nav.next_print_page", {"page": "7"}, trigger="Ctrl+Page Down"
    )
    trace = result.trace
    assert isinstance(trace, ExplanationTrace)
    assert trace.verb_id == "nav.next_print_page"
    assert trace.trigger == "Ctrl+Page Down"
    assert trace.profile == "Normal"


def test_trace_to_text_includes_documented_fields() -> None:
    result = VerbosityEngine(profile=EXPERT).speak(
        "search.find", {"match_total": 3}, trigger="Ctrl+F"
    )
    text = result.trace.to_text()
    assert "Verb: search.find" in text
    assert "Trigger: Ctrl+F" in text
    assert "Profile: Expert" in text
    assert "Channels:" in text
    assert "Template source:" in text
    assert "Suppressed:" in text  # routine hidden by Expert


def test_qvp_source_appears_in_trace_text() -> None:
    result = VerbosityEngine(
        profile=NORMAL,
        qvp_templates={"doc.save": "saved {name}"},
        qvp_name="MyPack",
    ).speak("doc.save", {"name": "a"})
    assert "Pack: template from MyPack" in result.trace.to_text()


def test_meeting_and_override_flags_render() -> None:
    result = VerbosityEngine(profile=NORMAL, per_verb_templates={"doc.save": "S {name}"}).speak(
        "doc.save", {"name": "a"}, meeting=True
    )
    text = result.trace.to_text()
    assert "Meeting Mode: affected this announcement" in text
    assert "Override: a per-verb template applied" in text
