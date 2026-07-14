"""Tests for the verbosity routing engine (§7-§13, §28)."""

from __future__ import annotations

from quill.core.verbosity.channels import Channel
from quill.core.verbosity.engine import VerbosityEngine, speak_legacy_text
from quill.core.verbosity.profiles import BEGINNER, EXPERT, NORMAL, QUIET
from quill.core.verbosity.verbs import Severity


def test_normal_profile_speaks_navigation() -> None:
    engine = VerbosityEngine(profile=NORMAL)
    result = engine.speak("nav.next_line", {"line": 12})
    assert result.speech == "Line 12"
    assert result.braille == "Line 12"
    assert result.visual == "Line 12"
    assert not result.suppressed


def test_visual_always_present_even_when_quiet() -> None:
    engine = VerbosityEngine(profile=QUIET)
    result = engine.speak("nav.next_line", {"line": 3})
    assert Channel.VISUAL in result.channels
    assert result.visual == "Line 3"
    # Quiet drops speech + sound.
    assert result.speech == ""
    assert Channel.SPEECH not in result.channels


def test_quiet_keeps_braille() -> None:
    engine = VerbosityEngine(profile=QUIET)
    result = engine.speak("doc.save", {"name": "notes.md"})
    assert Channel.BRAILLE in result.channels
    assert result.braille == "Saved notes.md"


def test_expert_suppresses_routine_but_not_errors() -> None:
    engine = VerbosityEngine(profile=EXPERT)
    routine = engine.speak("search.find", {"match_total": 4})
    assert routine.suppressed
    assert routine.speech == ""
    error = engine.speak("system.error", {"message": "Disk full"})
    assert not error.suppressed
    assert error.speech == "Disk full"


def test_beginner_speaks_everything() -> None:
    engine = VerbosityEngine(profile=BEGINNER)
    result = engine.speak("search.find", {"match_total": 4})
    assert result.speech == "Found 4"
    assert not result.suppressed


def test_sound_policy_all_vs_errors_only_vs_off() -> None:
    beginner = VerbosityEngine(profile=BEGINNER).speak("doc.save", {"name": "a"})
    assert beginner.sound_event is not None

    expert_routine = VerbosityEngine(profile=EXPERT).speak("doc.save", {"name": "a"})
    assert expert_routine.sound_event is None  # errors-only

    expert_error = VerbosityEngine(profile=EXPERT).speak("system.error", {"message": "x"})
    assert expert_error.sound_event is not None

    quiet = VerbosityEngine(profile=QUIET).speak("system.error", {"message": "x"})
    assert quiet.sound_event is None  # quiet removes the sound channel


def test_meeting_mutes_sound_keeps_speech() -> None:
    engine = VerbosityEngine(profile=NORMAL)
    result = engine.speak("doc.save", {"name": "a"}, meeting=True)
    assert result.sound_event is None
    assert Channel.SOUND not in result.channels
    assert result.speech == "Saved a"


def test_per_verb_override_template() -> None:
    engine = VerbosityEngine(profile=NORMAL, per_verb_templates={"nav.next_line": "L{line}"})
    result = engine.speak("nav.next_line", {"line": 9})
    assert result.speech == "L9"
    assert result.template_source == "per-verb override"
    assert result.trace.per_verb_override


def test_per_chord_override_wins_over_per_verb() -> None:
    engine = VerbosityEngine(
        profile=NORMAL,
        per_verb_templates={"nav.next_line": "verb{line}"},
        per_chord_templates={"ctrl+down": "chord{line}"},
    )
    result = engine.speak("nav.next_line", {"line": 1}, chord="ctrl+down")
    assert result.speech == "chord1"
    assert result.template_source == "per-chord override"


def test_qvp_template_source_labeled() -> None:
    engine = VerbosityEngine(
        profile=NORMAL,
        qvp_templates={"nav.next_print_page": "p{page}"},
        qvp_name="KellyFord Concise",
    )
    result = engine.speak("nav.next_print_page", {"page": "7"})
    assert result.speech == "p7"
    assert result.template_source == "QVP KellyFord Concise"
    assert result.trace.qvp_source == "KellyFord Concise"


def test_unknown_verb_falls_back_to_legacy() -> None:
    engine = VerbosityEngine(profile=NORMAL)
    result = engine.speak("does.not.exist", {"message": "hello"})
    assert result.verb_id == "_legacy"
    assert result.speech == "hello"
    assert result.severity is Severity.ROUTINE


def test_trace_records_decision_fields() -> None:
    engine = VerbosityEngine(profile=EXPERT)
    result = engine.speak("search.find", {"match_total": 2}, trigger="Ctrl+F")
    trace = result.trace
    assert trace.verb_id == "search.find"
    assert trace.trigger == "Ctrl+F"
    assert trace.profile == "Expert"
    assert trace.routine_hidden
    assert "hidden by Expert profile" in trace.suppressed_reason
    text = trace.to_text()
    assert "Verb: search.find" in text
    assert "Profile: Expert" in text


def test_channel_names_in_trace() -> None:
    result = VerbosityEngine(profile=NORMAL).speak("nav.next_line", {"line": 1})
    assert result.trace.channels == "speech, braille, sound, visual"


def test_set_profile_changes_routing() -> None:
    engine = VerbosityEngine(profile=NORMAL)
    assert engine.speak("search.find", {"match_total": 1}).speech == "Found 1"
    engine.set_profile(EXPERT)
    assert engine.speak("search.find", {"match_total": 1}).speech == ""


def test_legacy_passthrough_is_noop_text() -> None:
    assert speak_legacy_text("Saved document.") == "Saved document."
