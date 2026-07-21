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
        _move_selected_favorite=lambda delta: calls.append(f"move:{delta}"),
    )
    return frame, calls


def test_alt_shift_up_down_reorder_via_char_hook_when_tree_focused(monkeypatch) -> None:
    # Handled in the frame char hook (Windows steals Alt+arrow from the tree's
    # own key handler), and only when the favorites tree has focus.
    calls: list[str] = []
    tree = object()
    frame = SimpleNamespace(
        _favorites_tree=tree,
        _move_selected_favorite=lambda delta: calls.append(f"move:{delta}"),
        _radio_history=SimpleNamespace(alt_f4_to_tray=False),
        _send_to_tray=lambda: calls.append("tray"),
    )
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: tree))
    up, _sk = _key_event(wx.WXK_UP, alt=True, shift=True)
    RadioAppFrame._on_radio_char_hook(frame, up)  # type: ignore[arg-type]
    down, _sk2 = _key_event(wx.WXK_DOWN, alt=True, shift=True)
    RadioAppFrame._on_radio_char_hook(frame, down)  # type: ignore[arg-type]
    assert calls == ["move:-1", "move:1"]


def test_alt_shift_ignored_when_tree_not_focused(monkeypatch) -> None:
    calls: list[str] = []
    frame = SimpleNamespace(
        _favorites_tree=object(),
        _move_selected_favorite=lambda delta: calls.append(f"move:{delta}"),
        _radio_history=SimpleNamespace(alt_f4_to_tray=False),
        _send_to_tray=lambda: None,
    )
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: object()))  # something else
    up, skipped = _key_event(wx.WXK_UP, alt=True, shift=True)
    RadioAppFrame._on_radio_char_hook(frame, up)  # type: ignore[arg-type]
    assert calls == [] and skipped == [True]  # passes through untouched


def _move_frame(*, folder_sort: str, moved: bool = True):
    calls: list[str] = []
    favorite = SimpleNamespace(key="k1", folder="")
    store = SimpleNamespace(
        move=lambda key, *, delta: calls.append(f"store.move({delta})") or moved,
    )
    frame = SimpleNamespace(
        _selected_favorite=lambda: favorite,
        _radio_history=SimpleNamespace(folder_sort_orders={}, favorites_sort=folder_sort),
        _radio_favorites=store,
        _announce=lambda m: calls.append(f"say:{m}"),
        _save_radio_favorites=lambda: calls.append("save"),
        _reload_favorites_tree=lambda keep_key=None: calls.append(f"reload:{keep_key}"),
        _force_favorites_manual_order=lambda: calls.append("force-manual"),
    )
    return frame, calls


def test_move_favorite_manual_order_reorders_and_announces(monkeypatch) -> None:
    # move_announcement is imported inside the method; stub it to a known phrase.
    import quill.ui.radio.favorites_manager_dialog as fm

    monkeypatch.setattr(
        fm, "move_announcement", lambda store, key, delta: "Moved down, now above X"
    )
    frame, calls = _move_frame(folder_sort="manual")
    RadioAppFrame._move_selected_favorite(frame, 1)  # type: ignore[arg-type]
    assert "store.move(1)" in calls
    assert any("Moved down, now above X" in c for c in calls)
    assert "save" in calls and "reload:k1" in calls


def test_move_favorite_non_manual_forces_manual_then_moves(monkeypatch) -> None:
    # "Force the point": pressing the reorder key while sorted A-Z switches to
    # manual order and performs the move, rather than refusing.
    import quill.ui.radio.favorites_manager_dialog as fm

    monkeypatch.setattr(fm, "move_announcement", lambda store, key, delta: "Moved up, now below Y")
    frame, calls = _move_frame(folder_sort="az")
    RadioAppFrame._move_selected_favorite(frame, -1)  # type: ignore[arg-type]
    assert "force-manual" in calls  # switched to manual first
    assert "store.move(-1)" in calls  # then actually moved
    assert any("Switched to manual order" in c for c in calls)


def test_force_favorites_manual_order_switches_without_rewriting_the_list(monkeypatch) -> None:
    # #1186: switching to manual order must NOT bake the sorted display view into
    # the stored list (that overwrote the listener's real hand-arranged order on
    # the first reorder from an A-Z view). It only flips the sort mode to manual,
    # clears the per-folder sort overrides, and persists -- the stored order is
    # left exactly as-is because it already IS the manual order.
    from quill.core.radio import history as rh

    monkeypatch.setattr(paths_module, "app_data_dir", lambda: "FAKE_APP_DATA_DIR")
    saved: dict = {}
    monkeypatch.setattr(
        rh, "save_history", lambda data_dir, history: saved.setdefault("h", history)
    )
    original = ["c", "a", "b"]  # the listener's real manual order
    store = SimpleNamespace(
        favorites_in_display_order=lambda sort, folder_sorts: ["a", "b", "c"],  # A-Z view
        favorites=list(original),
    )
    hist = SimpleNamespace(favorites_sort="az", folder_sort_orders={"News": "az"})
    frame = SimpleNamespace(_radio_favorites=store, _radio_history=hist)
    RadioAppFrame._force_favorites_manual_order(frame)  # type: ignore[arg-type]
    assert store.favorites == original, "stored order preserved, not baked from the view"
    assert hist.favorites_sort == "manual"
    assert hist.folder_sort_orders == {}
    assert saved["h"] is hist


def test_move_favorite_at_edge_announces_and_does_not_reload() -> None:
    frame, calls = _move_frame(folder_sort="manual", moved=False)
    RadioAppFrame._move_selected_favorite(frame, -1)  # type: ignore[arg-type]
    assert any("edge" in c.lower() for c in calls)
    assert not any(c.startswith("reload") for c in calls)


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
# NFB Radio on the Station menu, alongside ACB Media
# ---------------------------------------------------------------------------


def test_nfb_radio_appears_on_station_menu_and_plays_nfbrn() -> None:
    from quill.ui.main_frame_radio import RadioMixin

    played: list[str] = []
    binds: list = []

    class _FakeMenu:
        def __init__(self) -> None:
            self.items: list = []

        def Append(self, item_id, label):  # noqa: N802 - wx shape
            self.items.append((item_id, label))

        def Bind(self, _evt, handler, id=None):  # noqa: N802, A002
            binds.append((id, handler))

        def AppendSubMenu(self, submenu, label):  # noqa: N802
            self.items.append((None, label))

    frame = SimpleNamespace(
        _wx=SimpleNamespace(NewIdRef=lambda: object(), EVT_MENU="evt", Menu=_FakeMenu),
        _radio_controller=SimpleNamespace(play_station=lambda s: played.append(s.name)),
        _retain_radio_menu_ids=lambda *a: None,
    )
    menu = _FakeMenu()
    RadioMixin._append_nfb_media_submenu(frame, menu)  # type: ignore[arg-type]

    assert any("NFB" in label for _id, label in menu.items), "NFB item added to Station menu"
    binds[-1][1](None)  # invoke the menu handler
    assert any("NFBRN" in name for name in played), "playing it starts the NFBRN stream"


# ---------------------------------------------------------------------------
# Volume changes persist a favorite's level WITHOUT reloading the tree (#1154)
# ---------------------------------------------------------------------------


def test_volume_persist_does_not_reload_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    # #1154: adjusting the volume of a playing favorite persists the new level
    # to disk, but must NOT go through _save_radio_favorites -- whose standalone
    # override rebuilds the favorites tree and makes the screen reader
    # re-announce the station on every Volume Up/Down keystroke. It uses the
    # disk-only _persist_radio_favorites instead.
    from quill.ui.main_frame_radio import RadioMixin

    calls: list[str] = []
    favorite = SimpleNamespace(volume_percent=50)
    frame = SimpleNamespace(
        _radio_history_key="uuid-1",
        _radio_favorites=SimpleNamespace(
            find=lambda _key: favorite,
            set_volume=lambda _key, vol: calls.append(f"set_volume={vol}"),
        ),
        _save_radio_favorites=lambda: calls.append("save_radio_favorites(RELOADS TREE)"),
        _persist_radio_favorites=lambda: calls.append("persist_radio_favorites(disk only)"),
    )
    state = SimpleNamespace(
        station=SimpleNamespace(station_uuid="uuid-1", stream_url="s"),
        muted=False,
        volume_percent=60,
    )

    RadioMixin._radio_track_history_and_volume(frame, state)  # type: ignore[arg-type]

    assert "set_volume=60" in calls
    assert "persist_radio_favorites(disk only)" in calls
    assert "save_radio_favorites(RELOADS TREE)" not in calls


# ---------------------------------------------------------------------------
# Alt+F4 / Exit close path (_on_radio_app_close)
# ---------------------------------------------------------------------------


class _FakeCloseConfirmDialog:
    """Records construction args; ``show()`` returns whatever the test wants."""

    instances: list[_FakeCloseConfirmDialog] = []

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
    monkeypatch.setattr(radio_history_module, "save_history", lambda d, h: saved.append((d, h)))

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


def test_exit_after_recording_completes_the_close(monkeypatch: pytest.MonkeyPatch) -> None:
    # #1153: after making a recording, choosing Exit must actually exit -- run
    # every shutdown step and skip the close event -- not hang the app. The
    # shutdowns are all non-blocking (recorder stops on daemon threads, the mpv
    # engine soft-stops, the enhancement relay is a threading server), so the
    # close path returns and the frame is destroyed.
    frame, calls = _close_frame(
        monkeypatch, recording_active=True, player_state=RadioPlayerState.PLAYING
    )

    orig_init = _FakeCloseConfirmDialog.__init__

    def _init_with_exit(self: _FakeCloseConfirmDialog, *a: object, **k: object) -> None:
        orig_init(self, *a, **k)
        self.result = ("exit", False)

    monkeypatch.setattr(_FakeCloseConfirmDialog, "__init__", _init_with_exit)
    event, skipped, vetoed = _close_event()

    frame._on_radio_app_close(event)

    assert skipped == [True], "Exit after recording must proceed to a real exit"
    assert vetoed == []
    assert "controller.shutdown" in calls
    assert "recorder.shutdown" in calls
    assert "scheduler.shutdown" in calls
    assert "task_manager.shutdown(wait=False)" in calls
    assert frame._closing_in_progress is False


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


def test_explicit_exit_bypasses_minimize_on_close(monkeypatch: pytest.MonkeyPatch) -> None:
    # #1193: with close_action == "minimize", a normal close minimizes to tray --
    # but an explicit menu/tray Exit (which sets _exit_requested) must quit for
    # real, or Exit just bounces back into the tray and the app can never close.
    frame, calls = _close_frame(
        monkeypatch, close_action="minimize", player_state=RadioPlayerState.PLAYING
    )
    frame._exit_requested = True
    event, skipped, vetoed = _close_event()

    frame._on_radio_app_close(event)

    assert vetoed == [], "an explicit Exit must not veto/minimize"
    assert "send_to_tray" not in calls
    assert skipped == [True], "Exit proceeds to a real close"
    assert "controller.shutdown" in calls and "recorder.shutdown" in calls
    assert frame._exit_requested is False, "the one-shot flag is cleared"
    assert _FakeCloseConfirmDialog.instances == [], "explicit Exit skips the confirm prompt"


def test_explicit_exit_skips_confirm_even_while_recording(monkeypatch: pytest.MonkeyPatch) -> None:
    # A deliberate Exit does not re-prompt even mid-recording; the recorder's
    # shutdown finalizes the file, so nothing is silently lost.
    frame, calls = _close_frame(
        monkeypatch, close_action="ask", recording_active=True,
        player_state=RadioPlayerState.PLAYING,
    )
    frame._exit_requested = True
    event, skipped, vetoed = _close_event()

    frame._on_radio_app_close(event)

    assert _FakeCloseConfirmDialog.instances == []
    assert skipped == [True]
    assert vetoed == []
    assert "recorder.shutdown" in calls
