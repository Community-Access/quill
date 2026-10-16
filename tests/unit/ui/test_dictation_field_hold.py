"""D-15: Resume, Resume in This Field and Discard Held Words, and arming."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app


class _Controller:
    def __init__(self, paused: bool = True) -> None:
        self.paused_for_target = paused
        self.calls: list[tuple[str, bool]] = []

    def resume_held(self, *, here: bool = False) -> None:
        self.calls.append(("resume", here))

    def discard_held(self) -> None:
        self.calls.append(("discard", False))


def _host(controller: Any, *, own_window_in_front: bool) -> Any:
    from quill.ui.dictation_field_hold import FieldHoldMixin

    class Host(FieldHoldMixin):
        def __init__(self) -> None:
            self.frame = wx.Frame(None)
            self.said: list[str] = []
            self.refreshed = 0

        def _held_controller(self) -> Any:
            return controller

        def _hold_refresh(self) -> None:
            self.refreshed += 1

        def _announce(self, text: str) -> None:
            self.said.append(text)

        def _front_is_own_window(self) -> bool:
            return own_window_in_front

    return Host()


def test_nothing_happens_when_dictation_is_not_paused(wx_app) -> None:
    controller = _Controller(paused=False)
    host = _host(controller, own_window_in_front=False)
    try:
        host.resume_dictation()
        host.resume_in_this_field()
        host.discard_held_words()
        assert controller.calls == []
        assert host.said == [
            "Dictation is not paused.",
            "Dictation is not paused.",
            "Dictation is not paused, so nothing is held.",
        ]
    finally:
        host.frame.Destroy()


def test_the_three_commands_reach_the_controller(wx_app) -> None:
    controller = _Controller()
    host = _host(controller, own_window_in_front=False)
    try:
        host.resume_dictation()
        host.resume_in_this_field()
        host.discard_held_words()
        assert controller.calls == [("resume", False), ("resume", True), ("discard", False)]
    finally:
        host.frame.Destroy()


def test_from_its_own_window_resume_in_this_field_arms_and_the_same_command_cancels(
    wx_app,
) -> None:
    controller = _Controller()
    host = _host(controller, own_window_in_front=True)
    try:
        host.resume_in_this_field()
        assert host.dictation_armed()
        assert host.said[-1].startswith("Switch to the field you want. Dictation resumes there.")
        host.resume_in_this_field()
        assert not host.dictation_armed()
        assert host.said[-1] == "Cancelled; dictation is still paused and your words are held."
        assert controller.calls == []
    finally:
        host._arm_timer.Stop()
        host.frame.Destroy()


def test_a_resume_that_times_out_says_dictation_is_still_paused(wx_app, monkeypatch) -> None:
    import quill.core.transcribe.arming as arming

    controller = _Controller()
    host = _host(controller, own_window_in_front=True)
    try:
        host.resume_in_this_field()
        monkeypatch.setattr(arming, "ready_to_start", lambda **_kw: False)
        host._armed_ticks = 1
        host._on_arm_tick(None)  # nothing new came forward
        assert not host.dictation_armed()
        assert host.said[-1] == "No other program came forward; dictation is still paused."
        assert controller.calls == []
    finally:
        host._arm_timer.Stop()
        host.frame.Destroy()


def test_another_program_coming_forward_resumes_there(wx_app, monkeypatch) -> None:
    import quill.core.transcribe.arming as arming

    controller = _Controller()
    host = _host(controller, own_window_in_front=True)
    try:
        host.resume_in_this_field()
        monkeypatch.setattr(arming, "ready_to_start", lambda **_kw: True)
        monkeypatch.setattr(
            "quill.platform.windows.foreground.foreground_window_info",
            lambda: type("W", (), {"hwnd": 1, "process_id": 2, "window_class": "Edit"})(),
            raising=False,
        )
        host._on_arm_tick(None)
        assert controller.calls == [("resume", True)]
        assert not host.dictation_armed()
    finally:
        host._arm_timer.Stop()
        host.frame.Destroy()
