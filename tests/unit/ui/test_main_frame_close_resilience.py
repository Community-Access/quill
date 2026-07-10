"""The main window must always close, even if a shutdown step fails (#210)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import quill.stability.shutdown_watchdog as watchdog
import quill.ui.main_frame as mf
from quill.ui.main_frame import MainFrame


class _FakeWx:
    @staticmethod
    def GetTopLevelWindows() -> list[Any]:
        return []

    @staticmethod
    def GetApp() -> Any:
        return None

    @staticmethod
    def CallAfter(*_a: object, **_k: object) -> None:
        pass


def _raise() -> None:
    raise RuntimeError("boom")


def _frame_for_close(monkeypatch: pytest.MonkeyPatch) -> MainFrame:
    # Avoid real disk/lock side effects from the guarded shutdown steps.
    monkeypatch.setattr(mf, "save_settings", lambda *_a, **_k: None)
    monkeypatch.setattr(mf, "mark_clean_exit", lambda *_a, **_k: None)

    frame = MainFrame.__new__(MainFrame)
    frame.settings = SimpleNamespace(tray_enabled=False)
    frame._is_exiting = True
    frame._can_close_all_documents = lambda: True  # type: ignore[method-assign]
    frame._watch_queue_monitor = None
    # Several steps deliberately raise to prove they cannot block the close.
    frame._watch_service = SimpleNamespace(stop=_raise)
    frame._unregister_global_hotkeys = _raise  # type: ignore[method-assign]
    frame._remove_tray_icon = lambda: None  # type: ignore[method-assign]
    frame.close_ssh_connections = _raise  # type: ignore[method-assign]
    frame.flush_persistent_undo = _raise  # type: ignore[method-assign]
    frame.session_id = "test-session"
    frame._wx = _FakeWx()
    frame.frame = object()
    return frame


def test_on_close_always_skips_even_when_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _frame_for_close(monkeypatch)
    skipped: list[bool] = []
    vetoed: list[bool] = []
    event = SimpleNamespace(
        Skip=lambda: skipped.append(True),
        Veto=lambda: vetoed.append(True),
    )

    frame._on_close(event)

    assert skipped == [True], "the window must close (event.Skip) despite failing steps"
    assert vetoed == []


def test_on_close_vetoes_when_documents_cannot_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _frame_for_close(monkeypatch)
    frame._can_close_all_documents = lambda: False  # type: ignore[method-assign]
    skipped: list[bool] = []
    vetoed: list[bool] = []
    event = SimpleNamespace(
        Skip=lambda: skipped.append(True),
        Veto=lambda: vetoed.append(True),
    )

    frame._on_close(event)

    assert vetoed == [True]
    assert skipped == []


def test_on_close_closes_even_if_save_prompt_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A raising save-on-close prompt is a bug, not a Cancel; the window must
    # still close (#210) rather than being trapped open with nothing to force it.
    frame = _frame_for_close(monkeypatch)
    frame._can_close_all_documents = _raise  # type: ignore[method-assign]
    skipped: list[bool] = []
    vetoed: list[bool] = []
    event = SimpleNamespace(
        Skip=lambda: skipped.append(True),
        Veto=lambda: vetoed.append(True),
    )

    frame._on_close(event)

    assert skipped == [True]
    assert vetoed == []


class _FakeTimer:
    """Records that a hard-exit watchdog timer was started, without arming it."""

    instances: list[_FakeTimer] = []

    def __init__(self, interval: float, function: Any) -> None:
        self.interval = interval
        self.function = function
        self.daemon = False
        self.started = False
        _FakeTimer.instances.append(self)

    def start(self) -> None:
        self.started = True


def _arm_capable_frame(monkeypatch: pytest.MonkeyPatch) -> MainFrame:
    frame = _frame_for_close(monkeypatch)
    # A real frame enables the hard-exit watchdog; __new__ frames do not, which
    # is why the resilience tests above never arm a real os._exit timer.
    frame._hard_exit_enabled = True
    _FakeTimer.instances = []
    monkeypatch.setattr(watchdog.threading, "Timer", _FakeTimer)
    return frame


def test_committed_close_arms_hard_exit_watchdog(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _arm_capable_frame(monkeypatch)
    event = SimpleNamespace(Skip=lambda: None, Veto=lambda: None)

    frame._on_close(event)

    assert len(_FakeTimer.instances) == 1, "a committed close must arm the watchdog (#210)"
    timer = _FakeTimer.instances[0]
    assert timer.started is True
    assert timer.daemon is True
    assert timer.interval > 0


def test_vetoed_close_does_not_arm_watchdog(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _arm_capable_frame(monkeypatch)
    frame._can_close_all_documents = lambda: False  # type: ignore[method-assign]
    event = SimpleNamespace(Skip=lambda: None, Veto=lambda: None)

    frame._on_close(event)

    assert _FakeTimer.instances == [], "a vetoed close must not force-exit the process"


def test_force_exit_callback_calls_os_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _arm_capable_frame(monkeypatch)
    event = SimpleNamespace(Skip=lambda: None, Veto=lambda: None)
    frame._on_close(event)

    exits: list[int] = []
    monkeypatch.setattr(watchdog.os, "_exit", lambda code: exits.append(code))

    _FakeTimer.instances[0].function()

    assert exits == [0], "the watchdog must force the process to exit when it fires"


# ---------------------------------------------------------------------------
# #619: closing a dirty document must not crash on "Don't Save".
# ---------------------------------------------------------------------------


class _RecordingWx:
    """Minimal wx stub that records every CallAfter so we can assert the
    close-path save prompt never queues an editor.SetFocus that fires
    after DeletePage has destroyed the editor (#619)."""

    def __init__(self) -> None:
        self.call_after_calls: list[tuple[object, ...]] = []

    @staticmethod
    def GetTopLevelWindows() -> list[Any]:
        return []

    @staticmethod
    def GetApp() -> Any:
        return None

    def CallAfter(self, *args: object) -> None:
        self.call_after_calls.append(args)

    @property
    def YES_NO(self) -> int:
        return 0x00040002  # not exercised

    @property
    def CANCEL(self) -> int:
        return 0x80000000

    @property
    def ICON_WARNING(self) -> int:
        return 0x00000020

    @property
    def ID_YES(self) -> int:
        return 5103

    @property
    def ID_NO(self) -> int:
        return 5104

    @property
    def ID_CANCEL(self) -> int:
        return 5105


def _close_frame(monkeypatch: pytest.MonkeyPatch) -> tuple[MainFrame, _RecordingWx]:
    monkeypatch.setattr(mf, "save_settings", lambda *_a, **_k: None)
    monkeypatch.setattr(mf, "mark_clean_exit", lambda *_a, **_k: None)
    recording = _RecordingWx()
    frame = MainFrame.__new__(MainFrame)
    frame.settings = SimpleNamespace(tray_enabled=False)
    frame._is_exiting = True
    frame._can_close_all_documents = lambda: True  # type: ignore[method-assign]
    frame._watch_queue_monitor = None
    frame._watch_service = SimpleNamespace(stop=lambda: None)
    frame._unregister_global_hotkeys = lambda: None  # type: ignore[method-assign]
    frame._remove_tray_icon = lambda: None  # type: ignore[method-assign]
    frame.close_ssh_connections = lambda: None  # type: ignore[method-assign]
    frame.flush_persistent_undo = lambda: None  # type: ignore[method-assign]
    frame.session_id = "test-session"
    frame._wx = recording  # type: ignore[assignment]
    frame.frame = object()
    return frame, recording


def test_close_path_save_prompt_passes_restore_focus_false() -> None:
    """#619: _prompt_to_save_active_document must call the underlying
    helper with restore_focus=False so the editor SetFocus CallAfter
    does not fire after DeletePage destroys the TextCtrl."""

    frame, recording = _close_frame_no_patch()

    captured: dict[str, object] = {}

    def fake_prompt(
        title: str,
        message: str,
        *,
        restore_focus: bool = True,
    ) -> int:
        captured["title"] = title
        captured["restore_focus"] = restore_focus
        return recording.ID_NO

    frame._prompt_unsaved_changes_action = fake_prompt  # type: ignore[method-assign]

    # Make the document look dirty and close it.
    frame.document = SimpleNamespace(modified=True, name="untitled", path=None)
    frame._current_tab_index = lambda: 0  # type: ignore[method-assign]
    frame._close_tab = lambda _index: None  # type: ignore[method-assign]
    frame._set_status = lambda _msg: None  # type: ignore[method-assign]

    frame.close_current_document()

    assert captured["title"] == "Unsaved changes"
    assert captured["restore_focus"] is False, (
        "#619: close-path save prompt must pass restore_focus=False "
        "so the queued SetFocus does not fire on a destroyed TextCtrl"
    )


def test_show_modal_dialog_safe_set_focus_swallows_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#619: the defensive guard in _show_modal_dialog must swallow the
    RuntimeError raised by SetFocus when the underlying C++ widget has
    already been destroyed (e.g. by a close that followed the dialog)."""

    frame = MainFrame.__new__(MainFrame)
    # Stub editor whose SetFocus raises the exact RuntimeError from the
    # user's crash log so the test mirrors the production failure mode.
    frame.editor = SimpleNamespace(
        SetFocus=lambda: (_ for _ in ()).throw(
            RuntimeError("wrapped C/C++ object of type TextCtrl has been deleted")
        )
    )

    delivered: list[object] = []

    class _CallAfterOnly:
        @staticmethod
        def GetTopLevelWindows() -> list[Any]:
            return []

        @staticmethod
        def GetApp() -> Any:
            return None

        def CallAfter(self, fn: object) -> None:
            delivered.append(fn)

    frame._wx = _CallAfterOnly()  # type: ignore[assignment]
    frame._region_tracker = SimpleNamespace(
        enter=lambda *_a, **_k: None, exit=lambda *_a, **_k: None
    )

    # Bypass show_modal_dialog so we drive _show_modal_dialog directly.
    monkeypatch.setattr(mf, "show_modal_dialog", lambda *_a, **_k: 0)

    class _MsgStub:
        pass

    frame._show_modal_dialog(_MsgStub(), "label")

    # Exactly one CallAfter was queued (the safe-set-focus wrapper).
    assert len(delivered) == 1, "helper must queue a safe SetFocus wrapper"
    # Running it must not raise, even though editor.SetFocus does.
    delivered[0]()  # type: ignore[arg-type]


def _close_frame_no_patch() -> tuple[MainFrame, _RecordingWx]:
    """Build a close-resilience test frame without monkeypatch side effects
    (the close-prompt test does not need save_settings / mark_clean_exit)."""
    recording = _RecordingWx()
    frame = MainFrame.__new__(MainFrame)
    frame.settings = SimpleNamespace(tray_enabled=False)
    frame._is_exiting = True
    frame._can_close_all_documents = lambda: True  # type: ignore[method-assign]
    frame._watch_queue_monitor = None
    frame._watch_service = SimpleNamespace(stop=lambda: None)
    frame._unregister_global_hotkeys = lambda: None  # type: ignore[method-assign]
    frame._remove_tray_icon = lambda: None  # type: ignore[method-assign]
    frame.close_ssh_connections = lambda: None  # type: ignore[method-assign]
    frame.flush_persistent_undo = lambda: None  # type: ignore[method-assign]
    frame.session_id = "test-session"
    frame._wx = recording  # type: ignore[assignment]
    frame.frame = object()
    return frame, recording


# ---------------------------------------------------------------------------
# #603: closing the last document must not crash the caret handler.
# ---------------------------------------------------------------------------


class _DeadEditor:
    """A minimal editor stub whose reads raise the exact RuntimeError a
    destroyed C++ TextCtrl would raise (#603).

    The test asserts that ``_maybe_play_indent_tone`` and the editor
    caret-activity dispatch swallow that error cleanly, so the close
    path completes without surfacing a "QUILL encountered an
    unexpected error" dialog.
    """

    def GetValue(self) -> str:
        raise RuntimeError("wrapped C/C++ object of type TextCtrl has been deleted")

    def GetInsertionPoint(self) -> int:
        raise RuntimeError("wrapped C/C++ object of type TextCtrl has been deleted")


def test_maybe_play_indent_tone_swallows_runtime_error_from_dead_editor() -> None:
    """#603: when the editor's C++ TextCtrl is gone, _maybe_play_indent_tone
    must return silently instead of propagating a RuntimeError that would
    surface as a "QUILL encountered an unexpected error" dialog."""

    from quill.ui.main_frame_power_tools import PowerToolsActionsMixin

    frame = MainFrame.__new__(MainFrame)
    frame.settings = SimpleNamespace(indent_tone_scale="pentatonic")
    frame.editor = _DeadEditor()  # type: ignore[assignment]

    # Drive the mixin method directly. It must return None and not raise.
    result = PowerToolsActionsMixin._maybe_play_indent_tone(frame)

    assert result is None, "#603: dead-editor reads must be swallowed, not raised"


def test_on_editor_caret_activity_swallows_runtime_error() -> None:
    """#603: _on_editor_caret_activity must not surface a RuntimeError raised
    by the underlying C++ widget, even when the dead editor fires the
    indent-tone path. The outer try/except guarantees the close path
    completes cleanly and the next caret movement still gets its tone."""

    frame = MainFrame.__new__(MainFrame)
    frame.settings = SimpleNamespace(indent_tone_scale="pentatonic")
    frame.editor = _DeadEditor()  # type: ignore[assignment]
    frame._refresh_statusbar = lambda: None  # type: ignore[method-assign]
    frame._maybe_announce_indent = lambda: None  # type: ignore[method-assign]

    event = SimpleNamespace(Skip=lambda: None)
    # Drive the caret handler directly. It must return without raising,
    # even though the dead editor raises from _maybe_play_indent_tone.
    MainFrame._on_editor_caret_activity(frame, event)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# #920: an OS-initiated session end (Windows shutdown/restart/logoff) must be
# recorded as a clean exit, not a crash. The crash-recovery clean-exit marker
# is only ever set inside _on_close; an OS session end can end the process
# without _on_close running, so _on_session_end marks it clean best-effort.
# ---------------------------------------------------------------------------


def test_on_session_end_marks_clean_exit_and_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    """#920: an OS session end is a clean exit -- mark the session clean so the
    next launch does not falsely offer crash recovery, then Skip() so the
    process can end."""
    marked: list[str] = []
    monkeypatch.setattr(mf, "mark_clean_exit", lambda sid: marked.append(sid))
    frame = MainFrame.__new__(MainFrame)
    frame.session_id = "os-shutdown-session"
    skipped: list[bool] = []
    event = SimpleNamespace(Skip=lambda: skipped.append(True))

    frame._on_session_end(event)

    assert marked == ["os-shutdown-session"], "the session must be marked clean"
    assert skipped == [True], "the OS session end must be allowed to proceed"


def test_on_session_end_swallows_marker_failure_and_still_skips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#920: if the marker write itself raises (a transient FS error during
    shutdown), the handler must still Skip() so the OS shutdown is never
    blocked by a recovery-marker write."""

    def _raise(*_a: object, **_k: object) -> None:
        raise OSError("disk unavailable during shutdown")

    monkeypatch.setattr(mf, "mark_clean_exit", _raise)
    frame = MainFrame.__new__(MainFrame)
    frame.session_id = "os-shutdown-session"
    skipped: list[bool] = []
    event = SimpleNamespace(Skip=lambda: skipped.append(True))

    frame._on_session_end(event)  # must not raise

    assert skipped == [True], "a failed marker write must not block the session end"


def test_main_frame_binds_os_session_end_events() -> None:
    """#920 source-contract guard: the OS session-end events must be bound to
    the clean-exit marker handler, so an OS shutdown is never misreported as a
    crash. Reads main_frame.py as text (the UI test bar; no real wx needed)."""
    import pathlib

    src = pathlib.Path(mf.__file__).read_text("utf-8")
    assert "EVT_QUERY_END_SESSION" in src, "must bind EVT_QUERY_END_SESSION (#920)"
    assert "EVT_END_SESSION" in src, "must bind EVT_END_SESSION (#920)"
    assert "_on_session_end" in src, "must wire the session-end handler (#920)"
