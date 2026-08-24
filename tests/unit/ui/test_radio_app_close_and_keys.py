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
from quill.ui.radio.playback_state import RadioPlayerState

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


def test_ctrl_shift_e_opens_new_folder_app_wide(monkeypatch) -> None:
    # #1211: Ctrl+Shift+E must add a folder even from the favorites tree, where
    # the menu accelerator can be swallowed. Handled in the char hook, consumed
    # (not skipped) so it fires regardless of focus.
    calls: list[str] = []
    frame = SimpleNamespace(
        _radio_history=SimpleNamespace(alt_f4_to_tray=False),
        _on_new_folder=lambda: calls.append("new_folder"),
    )
    event, skipped = _key_event(ord("E"), ctrl=True, shift=True)
    RadioAppFrame._on_radio_char_hook(frame, event)  # type: ignore[arg-type]
    assert calls == ["new_folder"]
    assert skipped == []  # consumed, not passed through


def test_ctrl_e_without_shift_does_not_open_new_folder() -> None:
    calls: list[str] = []
    frame = SimpleNamespace(
        _radio_history=SimpleNamespace(alt_f4_to_tray=False),
        _on_new_folder=lambda: calls.append("new_folder"),
    )
    event, skipped = _key_event(ord("E"), ctrl=True, shift=False)
    RadioAppFrame._on_radio_char_hook(frame, event)  # type: ignore[arg-type]
    assert calls == []
    assert skipped == [True]  # passed through untouched


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


def test_force_favorites_manual_order_preserves_stored_order(monkeypatch) -> None:
    # #1186: switching from a sorted view (A-Z/Z-A) to manual must NOT bake the
    # visible order over the stored list -- doing so silently destroyed a
    # listener's hand-arranged order (a real scenario: the #1178 upgrade bug left
    # a manual order stored while the sort was flipped to A-Z), with no way to
    # recover it. Only the sort setting flips; the stored order is left untouched
    # (the caller reloads the tree to reveal it and announces "Switched to manual
    # order"), so no data is lost.
    from quill.core.radio import history as rh

    monkeypatch.setattr(paths_module, "app_data_dir", lambda: "FAKE_APP_DATA_DIR")
    saved: dict = {}
    monkeypatch.setattr(
        rh, "save_history", lambda data_dir, history: saved.setdefault("h", history)
    )
    calls: list[str] = []
    store = SimpleNamespace(
        favorites=["c", "a", "b"],  # the stored, hand-arranged order
    )
    hist = SimpleNamespace(favorites_sort="az", folder_sort_orders={"News": "az"})
    frame = SimpleNamespace(
        _radio_favorites=store,
        _radio_history=hist,
        _save_radio_favorites=lambda: calls.append("save"),
    )
    RadioAppFrame._force_favorites_manual_order(frame)  # type: ignore[arg-type]
    assert store.favorites == ["c", "a", "b"], "the stored order is preserved, not baked"
    assert hist.favorites_sort == "manual"
    assert hist.folder_sort_orders == {}
    assert saved["h"] is hist
    assert "save" in calls


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


# ---------------------------------------------------------------------------
# Recently Played stays current: rebuilt just-in-time on Station-menu open,
# newest first, cleared-then-refilled (never duplicated). ACB Media / NFB Radio
# were removed from the Station menu -- they live in Browse Stations now.
# ---------------------------------------------------------------------------


class _FakeMenuItem:
    def __init__(self, item_id: object, label: str) -> None:
        self.id = item_id
        self.label = label
        self.enabled = True

    def Enable(self, on: bool) -> None:  # noqa: N802 - wx shape
        self.enabled = on


class _FakeSubMenu:
    def __init__(self) -> None:
        self.items: list[_FakeMenuItem] = []
        self.binds: list[tuple[object, Any]] = []

    def GetMenuItems(self):  # noqa: N802 - wx shape
        return list(self.items)

    def Delete(self, item: _FakeMenuItem) -> None:  # noqa: N802 - wx shape
        self.items.remove(item)

    def Append(self, item_id: object, label: str) -> _FakeMenuItem:  # noqa: N802 - wx shape
        mi = _FakeMenuItem(item_id, label)
        self.items.append(mi)
        return mi

    def Bind(self, _evt: object, handler: Any, id: object = None) -> None:  # noqa: N802, A002
        self.binds.append((id, handler))


def _recent_frame(sub: _FakeSubMenu) -> tuple[Any, list[str]]:
    played: list[str] = []
    counter = [0]

    def new_id() -> int:
        counter[0] += 1
        return counter[0]

    frame = SimpleNamespace(
        _wx=SimpleNamespace(NewIdRef=new_id, ID_ANY=-1, EVT_MENU="evt"),
        _recent_submenu=sub,
        _radio_history=SimpleNamespace(stations=[]),
        _radio_favorites=SimpleNamespace(find=lambda _key: None),
        _radio_controller=SimpleNamespace(play_station=lambda s: played.append(s.display_name)),
        _retain_radio_menu_ids=lambda *a: None,
    )
    return frame, played


def test_recently_played_empty_shows_disabled_placeholder() -> None:
    from quill.ui.main_frame_radio import RadioMixin

    sub = _FakeSubMenu()
    frame, _played = _recent_frame(sub)

    RadioMixin._rebuild_recent_submenu(frame)  # type: ignore[arg-type]

    assert [i.label for i in sub.items] == ["(none yet)"]
    assert sub.items[0].enabled is False, "the placeholder is not selectable"


def test_recently_played_rebuild_reflects_history_newest_first_without_duplicating() -> None:
    from quill.ui.main_frame_radio import RadioMixin

    sub = _FakeSubMenu()
    frame, played = _recent_frame(sub)
    jazz = SimpleNamespace(display_name="Jazz FM", station_uuid="u1", stream_url="j")
    news = SimpleNamespace(display_name="News 24", station_uuid="u2", stream_url="n")
    # History is newest-first already (the store moves replays to the front).
    frame._radio_history.stations = [news, jazz]

    # Each row carries a positional accelerator (the newest is always
    # Alt+Shift+1), so the names are compared without it.
    def _names() -> list[str]:
        return [i.label.split(chr(9))[0] for i in sub.items]

    RadioMixin._rebuild_recent_submenu(frame)  # type: ignore[arg-type]
    assert _names() == ["News 24", "Jazz FM"]
    assert [i.label.split(chr(9))[1] for i in sub.items] == ["Alt+Shift+1", "Alt+Shift+2"]

    # A second rebuild replaces the items -- it never appends a stale second copy.
    RadioMixin._rebuild_recent_submenu(frame)  # type: ignore[arg-type]
    assert _names() == ["News 24", "Jazz FM"]

    # The bound handler plays that station.
    sub.binds[-1][1](None)
    assert played == ["Jazz FM"]


def test_station_menu_open_rebuilds_recent_and_always_skips() -> None:
    rebuilt: list[bool] = []
    skipped: list[bool] = []
    station_menu = object()
    frame = SimpleNamespace(
        _station_menu=station_menu,
        _rebuild_recent_submenu=lambda: rebuilt.append(True),
    )

    # Opening the Station menu rebuilds Recently Played, then skips so the Window
    # menu's own EVT_MENU_OPEN handler still runs.
    event = SimpleNamespace(GetMenu=lambda: station_menu, Skip=lambda: skipped.append(True))
    RadioAppFrame._on_station_menu_open(frame, event)  # type: ignore[arg-type]
    assert rebuilt == [True]
    assert skipped == [True]

    # Opening any other menu does not rebuild, but still skips.
    rebuilt.clear()
    skipped.clear()
    other = SimpleNamespace(GetMenu=lambda: object(), Skip=lambda: skipped.append(True))
    RadioAppFrame._on_station_menu_open(frame, other)  # type: ignore[arg-type]
    assert rebuilt == []
    assert skipped == [True]


# ---------------------------------------------------------------------------
# Volume changes persist a favorite's level WITHOUT reloading the tree (#1154)
# ---------------------------------------------------------------------------


def test_volume_persist_does_not_reload_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    # #1154: adjusting the volume of a playing favorite persists the new level
    # to disk, but must NOT go through _save_radio_favorites -- whose standalone
    # override rebuilds the favorites tree and makes the screen reader
    # re-announce the station on every Volume Up/Down keystroke. It uses the
    # disk-only _persist_radio_favorites instead.
    from quill.ui import main_frame_radio
    from quill.ui.main_frame_radio import RadioMixin

    calls: list[str] = []
    monkeypatch.setattr(main_frame_radio, "app_data_dir", lambda: "unused")
    monkeypatch.setattr(
        main_frame_radio.radio_history,
        "save_history",
        lambda _dir, _hist: calls.append("save_history(disk only)"),
    )
    favorite = SimpleNamespace(volume_percent=50)
    frame = SimpleNamespace(
        _radio_history_key="uuid-1",
        _radio_history=SimpleNamespace(volume_percent=-1),
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
    # #1263: the level is also remembered globally (disk-only history save) so a
    # non-favorite station doesn't come back at full volume next launch.
    assert frame._radio_history.volume_percent == 60
    assert "save_history(disk only)" in calls


def test_resolve_volume_falls_back_to_last_global_level() -> None:
    # #1263: a non-favorite station plays at the last global volume the listener
    # set, not the controller's 100% default. A favorite still wins with its own.
    from quill.ui.main_frame_radio import RadioMixin

    frame = SimpleNamespace(
        _radio_history=SimpleNamespace(volume_percent=40),
        _radio_favorites=SimpleNamespace(find=lambda _key: None),
    )
    station = SimpleNamespace(station_uuid="uuid-x", stream_url="s")
    assert RadioMixin._radio_resolve_volume(frame, station) == 40  # type: ignore[arg-type]

    # A favorite with its own remembered level takes precedence.
    frame._radio_favorites = SimpleNamespace(find=lambda _key: SimpleNamespace(volume_percent=75))
    assert RadioMixin._radio_resolve_volume(frame, station) == 75  # type: ignore[arg-type]

    # Nothing ever set globally -> -1 tells the controller to leave volume alone.
    frame._radio_history = SimpleNamespace(volume_percent=-1)
    frame._radio_favorites = SimpleNamespace(find=lambda _key: None)
    assert RadioMixin._radio_resolve_volume(frame, station) == -1  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Volume slider: arrowing the focused slider must not double-speak (#1214)
# ---------------------------------------------------------------------------


def test_volume_slider_arrow_sets_volume_without_a_redundant_announce() -> None:
    # The slider has keyboard focus while it is arrowed, so the screen reader
    # already speaks the new value; an extra _announce made every keystroke
    # double-speak ("55" then "Radio volume 55"). The handler now only sets the
    # volume and refreshes state -- it must not announce.
    calls: list[str] = []
    frame = SimpleNamespace(
        _radio_controller=SimpleNamespace(set_volume=lambda p: calls.append(f"set:{p}")),
        _volume_slider=SimpleNamespace(GetValue=lambda: 55),
        _status_bar=SimpleNamespace(refresh=lambda: calls.append("refresh")),
        _announce=lambda m: calls.append(f"say:{m}"),
    )

    RadioAppFrame._on_volume_slider(frame, None)  # type: ignore[arg-type]

    assert "set:55" in calls, "the slider still drives the real volume"
    assert "refresh" in calls, "live status stays in sync"
    assert not any(c.startswith("say:") for c in calls), (
        "the focused slider already speaks its value -- no extra announcement"
    )


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
    deferred: list[tuple[Any, tuple[Any, ...]]] = []
    closed: list[bool] = []
    frame = RadioAppFrame.__new__(RadioAppFrame)
    frame.frame = SimpleNamespace(Close=lambda: closed.append(True))
    # _on_radio_app_close no longer ShowModals from inside EVT_CLOSE; it defers
    # the confirm dialog via self._wx.CallAfter. Capture the scheduled call so a
    # test can drive _ask_close_action itself (see _run_deferred).
    frame._wx = SimpleNamespace(CallAfter=lambda fn, *a: deferred.append((fn, a)))
    frame._deferred = deferred  # type: ignore[attr-defined]
    frame._closed = closed  # type: ignore[attr-defined]
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
    event = SimpleNamespace(
        Skip=lambda: skipped.append(True),
        Veto=lambda: vetoed.append(True),
        # A normal user-initiated close is vetoable; the P1-8 guard only
        # short-circuits when CanVeto() is False (OS log-off/shutdown).
        CanVeto=lambda: True,
    )
    return event, skipped, vetoed


def _run_deferred(frame: Any) -> None:
    """Invoke the _ask_close_action that _on_radio_app_close scheduled via
    CallAfter -- i.e. simulate the deferred confirm dialog actually running."""
    assert frame._deferred, "expected a deferred _ask_close_action to have been scheduled"
    fn, args = frame._deferred.pop(0)
    fn(*args)


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
    "player_state",
    [RadioPlayerState.STOPPED, RadioPlayerState.PLAYING],
)
def test_close_defers_prompt_only_while_recording(
    monkeypatch: pytest.MonkeyPatch, player_state: RadioPlayerState
) -> None:
    # Closing while a recording runs must NOT ShowModal from inside the
    # EVT_CLOSE handler (unreliable on wxMSW -- Alt+F4 did nothing while a
    # station played). It vetoes the close and schedules the confirm dialog via
    # CallAfter; nothing is shown or shut down synchronously.
    frame, calls = _close_frame(monkeypatch, recording_active=True, player_state=player_state)
    event, skipped, vetoed = _close_event()

    frame._on_radio_app_close(event)

    assert vetoed == [True], "the close is vetoed; the deferred prompt decides what happens"
    assert skipped == []
    assert frame._closing_in_progress is True, "guard is held until the deferred dialog finishes"
    assert _FakeCloseConfirmDialog.instances == [], "no modal is shown from inside EVT_CLOSE"
    assert calls == [], "no shutdown until the user actually chooses Exit"
    assert len(frame._deferred) == 1, "exactly one confirm dialog is scheduled"
    fn, args = frame._deferred[0]
    # The shared close flow schedules _run_close_confirm carrying the app's own
    # confirm dialog callable (_radio_close_confirm).
    assert fn == frame._run_close_confirm
    assert args == (frame._radio_close_confirm,)


@pytest.mark.parametrize(
    "player_state",
    [RadioPlayerState.PLAYING, RadioPlayerState.CONNECTING, RadioPlayerState.BUFFERING],
)
def test_close_while_only_playing_exits_without_a_prompt(
    monkeypatch: pytest.MonkeyPatch, player_state: RadioPlayerState
) -> None:
    # 2026-08-23: "I still can not alt+f4 out of the app when things are
    # playing." A live stream is not work that can be lost, so playback alone
    # must never gate the close behind a dialog: Alt+F4 while listening closes
    # the app like any other window. Only an active recording defers a prompt.
    frame, calls = _close_frame(monkeypatch, recording_active=False, player_state=player_state)
    event, skipped, vetoed = _close_event()

    frame._on_radio_app_close(event)

    assert _FakeCloseConfirmDialog.instances == [], "playing-only close must not prompt"
    assert skipped == [True], "the close proceeds to a real exit"
    assert vetoed == []
    assert "controller.shutdown" in calls, "shutdown stops the stream on the way out"


def test_deferred_cancel_keeps_window_open_and_resets_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The confirm dialog's default result is None (Cancel): the window stays open,
    # nothing shuts down, and the guard resets so a later close still works.
    # recording_active: only a recording defers the prompt now.
    frame, calls = _close_frame(
        monkeypatch, recording_active=True, player_state=RadioPlayerState.PLAYING
    )
    event, _skipped, _vetoed = _close_event()
    frame._on_radio_app_close(event)

    _run_deferred(frame)

    assert len(_FakeCloseConfirmDialog.instances) == 1
    assert _FakeCloseConfirmDialog.instances[0].recording_active is True
    assert calls == [], "cancel leaves everything as-is"
    assert frame._closed == [], "cancel does not close the frame"
    assert frame._closing_in_progress is False, "guard resets so a later close works"


def test_deferred_exit_triggers_a_real_close(monkeypatch: pytest.MonkeyPatch) -> None:
    # #1153: after making a recording, choosing Exit must actually exit. The
    # deferred handler re-enters the close path deliberately (sets _exit_requested
    # and calls frame.Close()), where the real shutdown + Skip run (covered by the
    # explicit-exit tests below).
    frame, _calls = _close_frame(
        monkeypatch, recording_active=True, player_state=RadioPlayerState.PLAYING
    )

    orig_init = _FakeCloseConfirmDialog.__init__

    def _init_with_exit(self: _FakeCloseConfirmDialog, *a: object, **k: object) -> None:
        orig_init(self, *a, **k)
        self.result = ("exit", False)

    monkeypatch.setattr(_FakeCloseConfirmDialog, "__init__", _init_with_exit)
    event, _skipped, _vetoed = _close_event()
    frame._on_radio_app_close(event)

    _run_deferred(frame)

    assert frame._exit_requested is True, "Exit re-enters the close path deliberately"
    assert frame._closed == [True], "frame.Close() runs the real shutdown"
    assert frame._closing_in_progress is False, "guard resets before re-entering close"


def test_deferred_minimize_with_dont_ask_persists_and_goes_to_tray(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame, calls = _close_frame(
        monkeypatch, recording_active=True, player_state=RadioPlayerState.PLAYING
    )

    orig_init = _FakeCloseConfirmDialog.__init__

    def _init_with_minimize(self: _FakeCloseConfirmDialog, *a: object, **k: object) -> None:
        orig_init(self, *a, **k)
        self.result = ("minimize", True)

    monkeypatch.setattr(_FakeCloseConfirmDialog, "__init__", _init_with_minimize)
    event, _skipped, _vetoed = _close_event()
    frame._on_radio_app_close(event)

    _run_deferred(frame)

    assert frame._radio_history.close_action == "minimize"
    assert frame._saved_history == [("FAKE_APP_DATA_DIR", frame._radio_history)]
    assert calls == ["send_to_tray"], "minimize tucks to the tray"
    assert frame._closed == [], "minimize does not close the frame"
    assert frame._closing_in_progress is False


def test_run_close_confirm_resets_guard_even_if_dialog_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame, _calls = _close_frame(monkeypatch, player_state=RadioPlayerState.PLAYING)
    frame._closing_in_progress = True  # as handle_app_close set it before deferring

    class _RaisingDialog(_FakeCloseConfirmDialog):
        def show(self) -> tuple[str, bool] | None:
            raise RuntimeError("boom")

    monkeypatch.setattr(close_confirm_dialog_module, "RadioCloseConfirmDialog", _RaisingDialog)

    with pytest.raises(RuntimeError):
        frame._run_close_confirm(frame._radio_close_confirm)

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
        monkeypatch,
        close_action="ask",
        recording_active=True,
        player_state=RadioPlayerState.PLAYING,
    )
    frame._exit_requested = True
    event, skipped, vetoed = _close_event()

    frame._on_radio_app_close(event)

    assert _FakeCloseConfirmDialog.instances == []
    assert skipped == [True]
    assert vetoed == []
    assert "recorder.shutdown" in calls


# -- the close gesture's default answer must be the one the gesture asked for --


def test_the_close_confirm_defaults_to_exit_not_minimize() -> None:
    """Alt+F4 then Enter must exit, because that is what Alt+F4 means.

    Reported 2026-08-21: "alt+f4 is not closing ... the Exit command works."
    Both halves were true and neither was a broken close path. While a station
    plays the close is protected, so Alt+F4 raises this dialog -- and the
    dialog's default button was Minimize to Tray. So the whole keyboard
    interaction (Alt+F4, Enter) tucked the window into the tray, and the only
    thing that genuinely exited was the Exit menu item, which bypasses the
    dialog. Minimize is the interesting alternative here; it is not the
    expected answer to "close this window".

    Pinned as source rather than by building the dialog: it assigns its ids
    with ``int(wx.NewIdRef())``, which drops the IdRef, and wx recycles the id
    out from under a second construction in the same process.
    """
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "radio" / "close_confirm_dialog.py"
    ).read_text(encoding="utf-8")

    assert "affirmative_id=self._exit_id" in source, "Enter must answer a close gesture with Exit"
    assert 'affirmative_label="Exit"' in source
    # Exit leads the row: the first button is the one a listener meets first.
    assert source.index('self._exit_id, "E&xit"') < source.index(
        'self._minimize_id, "&Minimize to Tray"'
    ), "Exit must be created, and added, before Minimize"
    assert source.index("buttons.Add(exit_btn") < source.index("buttons.Add(minimize_btn")


def test_the_main_window_answers_go_to_player_like_every_other_window() -> None:
    """Ctrl+Shift+G worked in eight windows and not in the one people try first.

    ``transport_keys.install()`` carries the transport table into the browse
    tree, the managers and the player panel. The main window never installs it,
    and APP_KEYMAPS carries no entry either, so Go to Player -- the key whose
    entire job is "take me back to the player" -- was the one key that did
    nothing on the main window. Pinned as source, because the binding is a menu
    item on a frame this test cannot cheaply build.
    """
    from pathlib import Path

    from quill.core.radio import transport_commands

    source = (Path(__file__).resolve().parents[3] / "quill" / "apps" / "radio.py").read_text(
        encoding="utf-8"
    )
    command = transport_commands.command(transport_commands.GO_TO_PLAYER)
    assert command is not None
    assert f"Go to Player\t{command.key}" in source, (
        "the main window must advertise Go to Player on its own accelerator, "
        "and with the same key every other window answers to"
    )
    assert "transport_keys.perform(self, transport_commands.GO_TO_PLAYER)" in source, (
        "it must run the shared dispatcher, not a private copy"
    )
