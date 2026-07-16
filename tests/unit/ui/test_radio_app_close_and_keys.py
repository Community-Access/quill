"""Quill Radio: Ctrl+Up/Down volume from the Favorites tree, and the
Alt+F4/Exit close path (re-entrancy guard + skip-prompt-when-idle).

Regression coverage for two related reports:

- Ctrl+Up/Down silently did nothing. The Favorites tree has focus by
  default on launch and, being a native Win32 TreeCtrl, claims arrow keys
  for its own navigation before the Playback menu's Ctrl+Up/Down
  accelerator ever sees them. ``_on_favorites_key`` now handles the volume
  chord directly.
- Alt+F4 / Exit could leave the app completely unresponsive. wx's modal
  loop still pumps events while RadioCloseConfirmDialog.ShowModal() is
  running, so a second close attempt (e.g. a keyboard/screen-reader user
  pressing Alt+F4 again when nothing seems to happen) re-entered
  ``_on_radio_app_close`` and stacked a second confirm dialog on top of
  the first -- corrupting the Windows modal stack so both stayed
  invisible and the app stopped responding to Alt+F4 or Exit at all.
  ``_on_radio_app_close`` now guards against that re-entry, and skips the
  prompt entirely (closing immediately) when nothing is playing or
  recording, since there's nothing left for the prompt to protect.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import wx

import quill.core.paths as paths_module
import quill.ui.radio.close_confirm_dialog as close_confirm_dialog_module
from quill.apps.radio import RadioAppFrame
from quill.core.radio import history as radio_history_module
from quill.ui.radio.player_controller import RadioPlayerState

# ---------------------------------------------------------------------------
# Ctrl+Up/Down volume from the Favorites tree (_on_favorites_key)
# ---------------------------------------------------------------------------


def _key_event(
    code: int, *, ctrl: bool = False, shift: bool = False, alt: bool = False
) -> tuple[SimpleNamespace, list[bool]]:
    skipped: list[bool] = []
    event = SimpleNamespace(
        GetKeyCode=lambda: code,
        ControlDown=lambda: ctrl,
        ShiftDown=lambda: shift,
        AltDown=lambda: alt,
        Skip=lambda: skipped.append(True),
    )
    return event, skipped


def _favorites_key_frame() -> tuple[SimpleNamespace, list[str]]:
    calls: list[str] = []
    frame = SimpleNamespace(
        radio_volume_up=lambda: calls.append("volume_up"),
        radio_volume_down=lambda: calls.append("volume_down"),
        _on_favorites_activated=lambda _e: calls.append("activated"),
        _on_tree_remove=lambda: calls.append("remove"),
        _on_tree_rename=lambda: calls.append("rename"),
    )
    return frame, calls


def test_ctrl_up_triggers_volume_up_without_skipping() -> None:
    frame, calls = _favorites_key_frame()
    event, skipped = _key_event(wx.WXK_UP, ctrl=True)

    RadioAppFrame._on_favorites_key(frame, event)  # type: ignore[arg-type]

    assert calls == ["volume_up"]
    assert skipped == [], "handled here -- must not also fall through to event.Skip()"


def test_ctrl_down_triggers_volume_down_without_skipping() -> None:
    frame, calls = _favorites_key_frame()
    event, skipped = _key_event(wx.WXK_DOWN, ctrl=True)

    RadioAppFrame._on_favorites_key(frame, event)  # type: ignore[arg-type]

    assert calls == ["volume_down"]
    assert skipped == []


def test_plain_up_without_ctrl_still_skips_for_native_tree_navigation() -> None:
    frame, calls = _favorites_key_frame()
    event, skipped = _key_event(wx.WXK_UP, ctrl=False)

    RadioAppFrame._on_favorites_key(frame, event)  # type: ignore[arg-type]

    assert calls == [], "plain Up is tree navigation, not a volume chord"
    assert skipped == [True]


def test_ctrl_shift_up_does_not_trigger_volume() -> None:
    # Matches the literal "Ctrl+Up" menu accelerator: extra modifiers must
    # not also fire the volume handler.
    frame, calls = _favorites_key_frame()
    event, skipped = _key_event(wx.WXK_UP, ctrl=True, shift=True)

    RadioAppFrame._on_favorites_key(frame, event)  # type: ignore[arg-type]

    assert calls == []
    assert skipped == [True]


def test_ctrl_alt_down_does_not_trigger_volume() -> None:
    frame, calls = _favorites_key_frame()
    event, skipped = _key_event(wx.WXK_DOWN, ctrl=True, alt=True)

    RadioAppFrame._on_favorites_key(frame, event)  # type: ignore[arg-type]

    assert calls == []
    assert skipped == [True]


def test_f2_still_renames_alongside_the_new_volume_handling() -> None:
    # Regression guard: the new Ctrl+Up/Down branch sits right before the
    # existing event.Skip() and must not shadow the other handled keys.
    frame, calls = _favorites_key_frame()
    event, skipped = _key_event(wx.WXK_F2)

    RadioAppFrame._on_favorites_key(frame, event)  # type: ignore[arg-type]

    assert calls == ["rename"]
    assert skipped == []


# ---------------------------------------------------------------------------
# Alt+F4 / Exit close path (_on_radio_app_close)
# ---------------------------------------------------------------------------


class _FakeCloseConfirmDialog:
    """Records construction args; ``show()`` returns whatever the test wants."""

    instances: list["_FakeCloseConfirmDialog"] = []

    def __init__(self, parent: object, *, recording_active: bool, announce_cb: Any) -> None:
        self.parent = parent
        self.recording_active = recording_active
        self.announce_cb = announce_cb
        self.result: tuple[str, bool] | None = None
        _FakeCloseConfirmDialog.instances.append(self)

    def show(self) -> tuple[str, bool] | None:
        return self.result


def _close_frame(
    monkeypatch: pytest.MonkeyPatch,
    *,
    close_action: str = "ask",
    recording_active: bool = False,
    player_state: RadioPlayerState = RadioPlayerState.STOPPED,
) -> tuple[Any, list[str]]:
    _FakeCloseConfirmDialog.instances = []
    monkeypatch.setattr(
        close_confirm_dialog_module, "RadioCloseConfirmDialog", _FakeCloseConfirmDialog
    )
    monkeypatch.setattr(paths_module, "app_data_dir", lambda: "FAKE_APP_DATA_DIR")
    saved: list[tuple[object, object]] = []
    monkeypatch.setattr(
        radio_history_module, "save_history", lambda d, h: saved.append((d, h))
    )

    calls: list[str] = []
    frame = RadioAppFrame.__new__(RadioAppFrame)
    frame.frame = object()
    frame._announce = lambda _msg: None
    frame._radio_history = SimpleNamespace(close_action=close_action)
    frame._radio_recorder = SimpleNamespace(
        is_recording=recording_active, shutdown=lambda: calls.append("recorder.shutdown")
    )
    frame._radio_controller = SimpleNamespace(
        state=SimpleNamespace(state=player_state),
        shutdown=lambda: calls.append("controller.shutdown"),
    )
    frame._radio_scheduler = SimpleNamespace(shutdown=lambda: calls.append("scheduler.shutdown"))
    frame._task_manager = SimpleNamespace(
        shutdown=lambda wait=False: calls.append(f"task_manager.shutdown(wait={wait})")
    )
    frame._unregister_media_keys = lambda: calls.append("unregister_media_keys")
    frame._remove_tray_icon = lambda: calls.append("remove_tray_icon")
    frame._send_to_tray = lambda: calls.append("send_to_tray")
    frame._saved_history = saved  # type: ignore[attr-defined]
    return frame, calls


def _close_event() -> tuple[SimpleNamespace, list[bool], list[bool]]:
    skipped: list[bool] = []
    vetoed: list[bool] = []
    event = SimpleNamespace(Skip=lambda: skipped.append(True), Veto=lambda: vetoed.append(True))
    return event, skipped, vetoed


def test_second_close_while_dialog_open_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    frame, calls = _close_frame(monkeypatch)
    frame._closing_in_progress = True
    event, skipped, vetoed = _close_event()

    frame._on_radio_app_close(event)

    assert vetoed == [True]
    assert skipped == []
    assert calls == [], "a re-entrant close must not run any shutdown step"
    assert _FakeCloseConfirmDialog.instances == [], "must not open a second dialog"


def test_close_skips_dialog_and_exits_when_nothing_playing_or_recording(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame, calls = _close_frame(
        monkeypatch, recording_active=False, player_state=RadioPlayerState.STOPPED
    )
    event, skipped, vetoed = _close_event()

    frame._on_radio_app_close(event)

    assert _FakeCloseConfirmDialog.instances == [], "idle close must not prompt at all"
    assert skipped == [True], "idle close must proceed to a real exit"
    assert vetoed == []
    assert "controller.shutdown" in calls
    assert "recorder.shutdown" in calls
    assert "scheduler.shutdown" in calls
    assert getattr(frame, "_closing_in_progress", False) is False, (
        "idle close never opens a dialog, so the guard flag must never be set"
    )


@pytest.mark.parametrize(
    "recording_active,player_state",
    [
        (True, RadioPlayerState.STOPPED),
        (False, RadioPlayerState.PLAYING),
        (False, RadioPlayerState.CONNECTING),
    ],
)
def test_close_prompts_when_recording_or_playback_active(
    monkeypatch: pytest.MonkeyPatch, recording_active: bool, player_state: RadioPlayerState
) -> None:
    frame, calls = _close_frame(
        monkeypatch, recording_active=recording_active, player_state=player_state
    )
    event, skipped, vetoed = _close_event()

    # Cancel: the dialog's show() returns None.
    orig_init = _FakeCloseConfirmDialog.__init__

    def _init_with_cancel(self: _FakeCloseConfirmDialog, *a: object, **k: object) -> None:
        orig_init(self, *a, **k)
        self.result = None

    monkeypatch.setattr(_FakeCloseConfirmDialog, "__init__", _init_with_cancel)

    frame._on_radio_app_close(event)

    assert len(_FakeCloseConfirmDialog.instances) == 1
    dialog = _FakeCloseConfirmDialog.instances[0]
    assert dialog.recording_active is recording_active
    assert vetoed == [True], "cancelling the prompt must veto the close"
    assert skipped == []
    assert calls == [], "a vetoed close must not run shutdown"
    assert frame._closing_in_progress is False, "guard must reset after the dialog closes"


def test_dont_ask_again_persists_close_action_and_minimizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame, calls = _close_frame(monkeypatch, player_state=RadioPlayerState.PLAYING)

    orig_init = _FakeCloseConfirmDialog.__init__

    def _init_with_minimize(self: _FakeCloseConfirmDialog, *a: object, **k: object) -> None:
        orig_init(self, *a, **k)
        self.result = ("minimize", True)

    monkeypatch.setattr(_FakeCloseConfirmDialog, "__init__", _init_with_minimize)
    event, skipped, vetoed = _close_event()

    frame._on_radio_app_close(event)

    assert frame._radio_history.close_action == "minimize"
    assert frame._saved_history == [("FAKE_APP_DATA_DIR", frame._radio_history)]
    assert vetoed == [True], "minimize vetoes the close instead of exiting"
    assert calls == ["send_to_tray"]
    assert skipped == []


def test_closing_in_progress_resets_even_if_dialog_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame, _calls = _close_frame(monkeypatch, player_state=RadioPlayerState.PLAYING)

    class _RaisingDialog(_FakeCloseConfirmDialog):
        def show(self) -> tuple[str, bool] | None:
            raise RuntimeError("boom")

    monkeypatch.setattr(close_confirm_dialog_module, "RadioCloseConfirmDialog", _RaisingDialog)
    event, _skipped, _vetoed = _close_event()

    with pytest.raises(RuntimeError):
        frame._on_radio_app_close(event)

    assert frame._closing_in_progress is False, (
        "the guard must reset even when the dialog itself raises, or every "
        "close attempt after a crash would be silently vetoed forever"
    )
