"""Tests for the verbosity runtime controller (sub-PR 1.5)."""

from __future__ import annotations

from quill.core.verbosity.controller import VerbosityController
from quill.core.verbosity.profiles import EXPERT, QUIET
from quill.core.verbosity.throttle import ThrottleConfig


def test_legacy_announcement_passes_through() -> None:
    ctrl = VerbosityController()
    out = ctrl.process("Saved notes.md")
    assert out.speech == "Saved notes.md"
    assert out.visual == "Saved notes.md"
    assert not out.suppressed


def test_repetition_collapse_drops_repeat_speech_keeps_visual() -> None:
    ctrl = VerbosityController()
    ctrl.throttle.set_config(ThrottleConfig(collapse_repeats=True))
    first = ctrl.process("No more results.")
    second = ctrl.process("No more results.")
    assert first.speech == "No more results."
    # The repeat is silenced for speech but the status-bar floor still shows it.
    assert second.speech == ""
    assert second.visual == "No more results."
    assert second.suppressed


def test_collapse_disabled_speaks_every_time() -> None:
    ctrl = VerbosityController()
    ctrl.throttle.set_config(ThrottleConfig(collapse_repeats=False))
    assert ctrl.process("ping").speech == "ping"
    assert ctrl.process("ping").speech == "ping"


def test_apply_settings_configures_throttle() -> None:
    class _S:
        announcement_verbosity = "normal"
        verbosity_history_enabled = True
        verbosity_collapse_repeats = False
        verbosity_max_announcements_per_window = 9

    ctrl = VerbosityController()
    ctrl.apply_settings(_S())
    assert ctrl.throttle.config.collapse_repeats is False
    assert ctrl.throttle.config.max_per_window == 9


def test_quiet_mode_suppresses_speech_keeps_visual() -> None:
    ctrl = VerbosityController()
    ctrl.toggle_quiet()
    out = ctrl.process("Saved notes.md")
    assert out.speech == ""
    assert out.visual == "Saved notes.md"  # status bar floor remains
    assert out.suppressed


def test_meeting_mode_mutes_sound() -> None:
    ctrl = VerbosityController()
    ctrl.toggle_meeting()
    out = ctrl.process("doc saved", verb_id="doc.save", ctx={"name": "a"})
    assert out.sound_event is None


def test_toggle_quiet_announces_and_undo_restores() -> None:
    ctrl = VerbosityController()
    assert ctrl.toggle_quiet() == "Quiet Mode on"
    assert ctrl.quiet.is_active
    assert ctrl.undo() == "Undid Quiet Mode on"
    assert not ctrl.quiet.is_active


def test_toggle_meeting_undo() -> None:
    ctrl = VerbosityController()
    assert ctrl.toggle_meeting() == "Meeting Mode on"
    assert ctrl.undo() == "Undid Meeting Mode on"
    assert not ctrl.meeting.is_active


def test_undo_empty() -> None:
    assert VerbosityController().undo() == "Nothing to undo"


def test_status_badge() -> None:
    ctrl = VerbosityController()
    assert ctrl.status_badge() == ""
    ctrl.toggle_quiet()
    assert ctrl.status_badge() == "[Q]"
    ctrl.toggle_meeting()
    assert ctrl.status_badge() == "[Q] [M]"


def test_history_records_and_what_changed() -> None:
    ctrl = VerbosityController()
    ctrl.process("First")
    ctrl.process("Second")
    assert ctrl.what_changed() == "Second"
    assert len(ctrl.history) == 2


def test_history_can_be_disabled() -> None:
    ctrl = VerbosityController(history_enabled=False)
    ctrl.process("ignored")
    assert len(ctrl.history) == 0
    assert ctrl.what_changed() == "Nothing recent"


def test_where_am_i() -> None:
    ctrl = VerbosityController()
    assert ctrl.where_am_i(line=12, total=540, column=3) == "Line 12 of 540, column 3"
    assert ctrl.where_am_i() == "Position unknown"


def test_speak_status() -> None:
    ctrl = VerbosityController()
    assert ctrl.speak_status("Ready") == "Ready"
    assert ctrl.speak_status("") == "Status bar empty"


def test_apply_settings_maps_profile() -> None:
    class _S:
        announcement_verbosity = "minimal"
        verbosity_history_enabled = True

    ctrl = VerbosityController()
    ctrl.apply_settings(_S())
    assert ctrl.profile is EXPERT


def test_expert_profile_suppresses_routine_verb() -> None:
    ctrl = VerbosityController(profile=EXPERT)
    out = ctrl.process("Found 3", verb_id="search.find", ctx={"match_total": 3})
    assert out.speech == ""
    assert out.suppressed
    assert out.visual == "Found 3"


def test_quiet_profile_constructor() -> None:
    ctrl = VerbosityController(profile=QUIET)
    assert ctrl.profile is QUIET
