"""Tests for the post-transcription Transcript Actions helper (wx-free parts)."""

from __future__ import annotations

import quill.ui.transcript_actions_ui as ta_ui
from quill.core.ai.transcript_actions import find_action, recommend_actions
from quill.ui.transcript_actions_ui import (
    build_action_labels,
    generate_action_text,
    offer_transcript_actions,
    run_transcript_actions_on_document,
)


class _Editor:
    def __init__(self, value: str = "", selection: str = "") -> None:
        self._value = value
        self._selection = selection

    def GetValue(self) -> str:
        return self._value

    def GetStringSelection(self) -> str:
        return self._selection


class _Backend:
    def __init__(self, *, reply: str = "", boom: str = "") -> None:
        self._reply = reply
        self._boom = boom

    def respond(self, prompt: str) -> str:
        if self._boom:
            raise RuntimeError(self._boom)
        return self._reply


class _Controller:
    def __init__(self) -> None:
        self.frame = object()
        self.new_buffers: list[tuple[str, str]] = []
        self.statuses: list[str] = []
        self.announcements: list[str] = []

    def _power_tools_open_text_in_new_buffer(self, text: str, status: str) -> None:
        self.new_buffers.append((text, status))

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def _announce(self, message: str) -> None:
        self.announcements.append(message)


def test_labels_list_actions_then_opt_out() -> None:
    actions = recommend_actions("Speaker 0: hi\nSpeaker 1: hey")
    labels = build_action_labels(actions)
    assert len(labels) == len(actions) + 1
    assert labels[-1] == "Just keep the transcript"
    assert any("Meeting Minutes" in label for label in labels)


def test_generate_action_text_success_and_error() -> None:
    action = find_action("clean-draft")
    assert action is not None
    text, error = generate_action_text(action, "um so yeah", _Backend(reply="Clean draft."))
    assert text == "Clean draft." and error is None
    text, error = generate_action_text(action, "x", _Backend(boom="no key"))
    assert text is None and "no key" in (error or "")


def test_finish_opens_new_buffer_on_success() -> None:
    ctrl = _Controller()
    action = find_action("meeting-minutes")
    ta_ui._finish(ctrl, action, "call.mp3", "## Minutes", None, _NoopProgress())
    assert ctrl.new_buffers and ctrl.new_buffers[0][0] == "## Minutes"
    assert "Meeting Minutes" in ctrl.new_buffers[0][1]


def test_finish_reports_error_and_empty() -> None:
    ctrl = _Controller()
    action = find_action("meeting-minutes")
    ta_ui._finish(ctrl, action, "call.mp3", None, "boom", _NoopProgress())
    assert ctrl.statuses and "boom" in ctrl.statuses[0]
    ta_ui._finish(ctrl, action, "call.mp3", "   ", None, _NoopProgress())
    assert any("no output" in s for s in ctrl.statuses)
    assert not ctrl.new_buffers


def test_offer_falls_back_when_empty_or_no_ai(monkeypatch) -> None:
    ctrl = _Controller()
    # Empty transcript: opt out, never touches AI.
    assert offer_transcript_actions(ctrl, "   ", "x.mp3") is False
    # AI off / no provider: the backend is None. The on-ramp is offered; when the
    # user declines (or AI stays off), it falls back to the plain result.
    monkeypatch.setattr(ta_ui, "_action_backend", lambda: None)
    monkeypatch.setattr("quill.ui.ai_setup_wizard.maybe_offer_ai_setup", lambda *a, **k: False)
    assert offer_transcript_actions(ctrl, "real transcript text", "x.mp3") is False


def test_run_on_document_hints_when_empty() -> None:
    ctrl = _Controller()
    ctrl.editor = _Editor(value="   ")
    run_transcript_actions_on_document(ctrl)
    assert ctrl.statuses and "transcript" in ctrl.statuses[0].lower()


def test_run_on_document_hints_to_enable_ai(monkeypatch) -> None:
    ctrl = _Controller()
    ctrl.editor = _Editor(value="Speaker 0: hello\nSpeaker 1: hi")
    monkeypatch.setattr(ta_ui, "_action_backend", lambda: None)  # AI off / unreachable
    monkeypatch.setattr("quill.core.ai.model_manager.load_ai_enabled", lambda: False)
    monkeypatch.setattr("quill.ui.ai_setup_wizard.maybe_offer_ai_setup", lambda *a, **k: False)
    run_transcript_actions_on_document(ctrl)
    assert any("Turn on AI" in s for s in ctrl.statuses)


class _NoopProgress:
    def close(self) -> None: ...
