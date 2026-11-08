"""Dial tuning in Quill Radio: the thin glue between the lists and the player.

The idea comes from BlindRadio by serrebidev (MIT), doc/readme.md "Dial tuning";
no BlindRadio code is copied. Every decision -- which rows tune, how long to
wait, which neighbours to keep, the recording pause, the dead-station timer --
is :mod:`quill.core.radio.dial_tuning`'s. This module only tells it what the
lists and the player are doing, and carries out what it answers:

* a list surface reports the row focus settled on (:meth:`DialTuningUI.focus`)
  and when focus leaves it (:meth:`DialTuningUI.left_list`);
* the player reports every state change (:meth:`DialTuningUI.on_state_changed`);
* ``Tune`` plays through the shared controller -- promoting a warm neighbour when
  one is ready (:mod:`quill.ui.radio.dial_warm_pool`) -- ``Warm`` keeps the
  neighbours, ``Say`` speaks, and the hiss follows ``hiss_wanted``.

**Nothing is spoken that the screen reader already says (GATE-13).** Moving to
a row is announced by the reader reading the row; this module adds nothing to
it. It speaks only three things the reader cannot know: that tuning is paused
while recording, that a station is not answering, and the new state after the
on/off command.

The list hooks are small functions (:func:`attach_tree`, :func:`attach_list`)
so a surface pays one line for them, and the controller carries the instance
(``controller._dial_tuning``) so a surface that only holds the controller can
still find it.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from quill.core.radio import dial_tuning as dial
from quill.ui.radio.dial_hiss_player import HissPlayer
from quill.ui.radio.dial_warm_pool import WarmPool, promote

_log = logging.getLogger(__name__)

__all__ = [
    "DialTuningUI",
    "attach_list",
    "attach_tree",
    "browse_row",
    "commit",
    "for_app",
    "for_controller",
    "passing_through",
    "quiet",
    "station_key",
    "tuned_volume",
]

#: How many rows to look past a folder for a station neighbour.
_NEIGHBOUR_REACH = 8
#: How long a metered answer is trusted: asking WinRT on every step is waste.
_METERED_CACHE_S = 30.0


def station_key(station: Any) -> str:
    """The key the player and Recently Played use for *station*."""
    if station is None:
        return ""
    return str(getattr(station, "station_uuid", "") or getattr(station, "stream_url", "") or "")


def _metered_probe(clock: Callable[[], float]) -> Callable[[], bool]:
    cache: dict[str, float | bool] = {}

    def probe() -> bool:
        now = clock()
        stamp = cache.get("at")
        if isinstance(stamp, float) and now - stamp < _METERED_CACHE_S:
            return bool(cache.get("metered", False))
        from quill.core import net_metered

        metered = net_metered.connection_cost() == net_metered.METERED
        cache["at"] = now
        cache["metered"] = metered
        return metered

    return probe


class DialTuningUI:
    """One per app, living as long as the player does."""

    def __init__(
        self,
        app: Any,
        wx: Any,
        *,
        clock: Callable[[], float] = time.monotonic,
        pool: WarmPool | None = None,
        hiss: HissPlayer | None = None,
        is_metered: Callable[[], bool] | None = None,
    ) -> None:
        self._app = app
        self._wx = wx
        self.tuner = dial.DialTuner(
            dial.DialSettings.from_history(app._radio_history),
            clock=clock,
            is_metered=is_metered or _metered_probe(clock),
        )
        self.pool = pool if pool is not None else WarmPool(app.frame)
        self.hiss = hiss if hiss is not None else HissPlayer()
        self._timer: Any = None
        app._radio_controller._dial_tuning = self

    # -- settings and the command --------------------------------------------

    @property
    def enabled(self) -> bool:
        return self.tuner.settings.enabled

    def reload_settings(self) -> None:
        """Preferences or the command changed a ``dial_*`` setting."""
        settings = dial.DialSettings.from_history(self._app._radio_history)
        self._run(self.tuner.update_settings(settings))
        if not settings.enabled:
            self._quiet(False)
        self._arm()

    def toggle(self) -> None:
        """Switch dial tuning on or off, and say which: the reader cannot know."""
        history = self._app._radio_history
        history.dial_tuning = not bool(getattr(history, "dial_tuning", False))
        from quill.ui.radio.history_save import save_history_async

        save_history_async(self._app, history)
        self.reload_settings()
        self._app._announce(dial.state_word(history.dial_tuning))

    # -- what the lists report ------------------------------------------------

    def focus(
        self,
        row: dial.DialRow | None,
        before: dial.DialRow | None = None,
        after: dial.DialRow | None = None,
    ) -> None:
        if not self.enabled:
            return
        if row is not None and self._already_playing(row.key):
            row = None  # the station you are hearing: nothing to tune, nothing to restart
        self._run(self.tuner.focus(row, before, after, recording=self._recording()))
        self._arm()

    def _already_playing(self, key: str) -> bool:
        """Whether *key* is what the player holds now, tuned by the dial or not."""
        from quill.ui.radio.playback_state import ACTIVE_STATES

        state = self._app._radio_controller.state
        if key != station_key(state.station) or key == self.tuner.current_key:
            return False
        return state.state in ACTIVE_STATES

    def left_list(self) -> None:
        if not self.enabled:
            return
        self._run(self.tuner.left_list())
        self._arm()

    # -- what the player reports ----------------------------------------------

    def on_state_changed(self, state: Any) -> None:
        """Every playback state change. Cheap when the dial is idle."""
        current = self.tuner.current_key
        if not current:
            return
        key = station_key(getattr(state, "station", None))
        name = str(getattr(getattr(state, "state", None), "name", ""))
        if key != current or name == "STOPPED":
            # Playback moved on outside the dial: a menu, a hotkey, Stop.
            self.tuner.forget()
            self.pool.clear()
            self._quiet(False)
            self._sync_hiss()
            self._arm()
            return
        if name == "PLAYING":
            self._run(self.tuner.connected(key))
        elif name == "ERROR":
            self._run(self.tuner.failed(key))
        else:
            self._sync_hiss()
        self._arm()

    def passing_through(self, station: Any) -> bool:
        return self.enabled and self.tuner.passing_through(station_key(station))

    def commit(self, station: Any) -> bool:
        """Enter on the tuned station: play it for real. True when it did."""
        key = station_key(station)
        if not self.enabled or not self.tuner.commit(key):
            return False
        app = self._app
        self._quiet(False)
        # Recently Played, Song History and the rest start here: the history
        # key and the title are cleared so the reload is recorded as new.
        app._radio_history_key = ""
        app._radio_track_title = ""
        # A fresh connection is a fresh time-shift buffer, and the station's
        # own buffer length applies from this load.
        app._radio_controller.play_station(station)
        self._sync_hiss()
        self._arm()
        return True

    def shutdown(self) -> None:
        self._stop_timer()
        self.hiss.stop()
        self.pool.shutdown()

    # -- carrying out the policy ----------------------------------------------

    def _run(self, actions: list[Any]) -> None:
        for action in actions:
            try:
                if isinstance(action, dial.Tune):
                    self._tune(action.row)
                elif isinstance(action, dial.Warm):
                    controller = self._app._radio_controller
                    self.pool.keep(action.rows, device=controller.output_device)
                elif isinstance(action, dial.Say):
                    self._app._announce(action.text)
            except Exception:  # noqa: BLE001 - the dial must never take playback down
                _log.exception("dial tuning action failed")
        self._sync_hiss()

    def _tune(self, row: dial.DialRow) -> None:
        controller = self._app._radio_controller
        old_key = station_key(controller.state.station)
        self._quiet(True)
        if not promote(controller, self.pool, row.key, row.station, old_key=old_key):
            controller.play_station(row.station)

    def _quiet(self, on: bool) -> None:
        """While a station is only passed through, its earcons stay quiet:
        the hiss is the dial's sound, and a cue per row would be a cue per
        arrow press."""
        self._app._radio_controller.dial_quiet = on

    def _sync_hiss(self) -> None:
        controller = self._app._radio_controller
        self.hiss.apply(
            self.tuner.hiss_wanted,
            level=self.tuner.settings.hiss_level,
            muted=bool(getattr(controller.state, "muted", False)),
        )

    def _recording(self) -> bool:
        recorder = getattr(self._app, "_radio_recorder", None)
        try:
            return int(getattr(recorder, "active_count", 0) or 0) > 0
        except (TypeError, ValueError):
            return False

    def _arm(self) -> None:
        due = self.tuner.next_due()
        self._stop_timer()
        if due is None:
            return
        self._timer = self._wx.CallLater(max(1, int(due * 1000) + 1), self._tick)

    def _stop_timer(self) -> None:
        timer, self._timer = self._timer, None
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - an expired timer has nothing to stop
                pass

    def _tick(self) -> None:
        self._timer = None
        self._run(self.tuner.poll())
        self._arm()


# -- finding the instance -------------------------------------------------------


def for_app(app: Any) -> DialTuningUI | None:
    """The app's dial, made the first time it is asked for."""
    controller = getattr(app, "_radio_controller", None)
    if controller is None:
        return None
    existing = getattr(controller, "_dial_tuning", None)
    if isinstance(existing, DialTuningUI):
        return existing
    try:
        return DialTuningUI(app, getattr(app, "_wx", None) or _wx())
    except Exception:  # noqa: BLE001 - no dial is the old behaviour, never a failure
        _log.exception("dial tuning unavailable")
        return None


def for_controller(controller: Any) -> DialTuningUI | None:
    existing = getattr(controller, "_dial_tuning", None)
    return existing if isinstance(existing, DialTuningUI) else None


def _wx() -> Any:
    import wx

    return wx


def on_state_changed(app: Any, state: Any) -> None:
    """The player's state changed; the dial follows it when there is one."""
    dial_ui = for_controller(getattr(app, "_radio_controller", None))
    if dial_ui is not None:
        try:
            dial_ui.on_state_changed(state)
        except Exception:  # noqa: BLE001 - never on the playback path
            _log.exception("dial tuning could not follow playback")


def attach_favorites(app: Any) -> None:
    """Make the app's dial and hook the main window's Favorites tree to it."""
    dial_ui = for_app(app)
    tree = getattr(app, "_favorites_tree", None)
    if dial_ui is None or tree is None:
        return
    attach_tree(
        app._radio_controller, tree, lambda item: favorite_row(app, tree, item), dial_ui._wx
    )


def attach_browse(surface: Any) -> None:
    """Hook a Browse Stations tree (window or main view) to the app's dial."""
    tree = getattr(surface, "_tree", None)
    controller = getattr(surface, "_controller", None)
    if tree is not None and for_controller(controller) is not None:
        attach_tree(controller, tree, lambda item: browse_row(tree, item), surface._wx)


def attach_search(surface: Any) -> None:
    """Hook Search Stations' results list to the app's dial."""
    results = getattr(surface, "_results", None)
    controller = getattr(surface, "_controller", None)
    if results is None or for_controller(controller) is None:
        return
    import wx

    attach_list(
        controller,
        results,
        lambda: search_rows(list(getattr(surface, "_current_results", []))),
        wx,
    )


def passing_through(app: Any, station: Any) -> bool:
    """For the bookkeeping hooks: is *station* only being tuned past?"""
    dial_ui = for_controller(getattr(app, "_radio_controller", None))
    return dial_ui is not None and dial_ui.passing_through(station)


def quiet(app: Any, state: Any) -> bool:
    """Whether a failure announcement belongs to the dial instead of the player."""
    return passing_through(app, getattr(state, "station", None))


def tuned_volume(app: Any, station: Any) -> bool:
    """True when *station* should keep the current volume rather than its own.

    The dial tuned it and Remember each station's volume is off: a level that
    jumps on every arrow press is worse than one that stays where it is.
    """
    dial_ui = for_controller(getattr(app, "_radio_controller", None))
    if dial_ui is None or not dial_ui.enabled or dial_ui.tuner.settings.remember_volume:
        return False
    return station_key(station) == dial_ui.tuner.current_key != ""


def commit(controller: Any, station: Any, announce: Callable[[str], None] | None = None) -> bool:
    """Enter on a list row: commit it when the dial tuned it. One line per surface.

    Says "Playing <station>." as every other Play in the app does, when the
    surface hands over its announcer.
    """
    dial_ui = for_controller(controller)
    if dial_ui is None or station is None or not dial_ui.commit(station):
        return False
    if announce is not None:
        name = str(getattr(station, "display_name", "") or getattr(station, "name", "") or "")
        announce(f"Playing {name}.")
    return True


# -- list hooks -------------------------------------------------------------------


def _focused(window: Any, wx: Any) -> bool:
    try:
        return wx.Window.FindFocus() is window
    except Exception:  # noqa: BLE001
        return False


def attach_tree(
    controller: Any, tree: Any, describe: Callable[[Any], dial.DialRow | None], wx: Any
) -> None:
    """Report a tree's settled focus to the dial. Leaves the tree's own handlers be."""

    def neighbour(item: Any, step: Callable[[Any], Any]) -> dial.DialRow | None:
        for _ in range(_NEIGHBOUR_REACH):
            item = step(item)
            if item is None or not item.IsOk():
                return None
            row = describe(item)
            if dial.row_tunes(row):
                return row
        return None

    def on_selection(event: Any) -> None:
        event.Skip()
        dial_ui = for_controller(controller)
        if dial_ui is None or not dial_ui.enabled or not _focused(tree, wx):
            return
        try:
            item = tree.GetSelection()
            if not item.IsOk():
                return
            dial_ui.focus(
                describe(item),
                neighbour(item, tree.GetPrevVisible),
                neighbour(item, tree.GetNextVisible),
            )
        except RuntimeError:  # the tree is being torn down
            return

    def on_leave(event: Any) -> None:
        event.Skip()
        dial_ui = for_controller(controller)
        if dial_ui is not None:
            dial_ui.left_list()

    tree.Bind(wx.EVT_TREE_SEL_CHANGED, on_selection)
    tree.Bind(wx.EVT_KILL_FOCUS, on_leave)


def attach_list(
    controller: Any, list_ctrl: Any, rows: Callable[[], list[dial.DialRow]], wx: Any
) -> None:
    """The same for a report list whose rows are all stations (Search results)."""

    def on_focus(event: Any) -> None:
        event.Skip()
        dial_ui = for_controller(controller)
        if dial_ui is None or not dial_ui.enabled or not _focused(list_ctrl, wx):
            return
        index = event.GetIndex()
        current = rows()
        if not 0 <= index < len(current):
            return
        before = current[index - 1] if index > 0 else None
        after = current[index + 1] if index + 1 < len(current) else None
        dial_ui.focus(current[index], before, after)

    def on_leave(event: Any) -> None:
        event.Skip()
        dial_ui = for_controller(controller)
        if dial_ui is not None:
            dial_ui.left_list()

    list_ctrl.Bind(wx.EVT_LIST_ITEM_FOCUSED, on_focus)
    list_ctrl.Bind(wx.EVT_KILL_FOCUS, on_leave)


def favorite_row(app: Any, tree: Any, item: Any) -> dial.DialRow | None:
    """A Favorites tree row, as the dial sees it."""
    data = tree.GetItemData(item)
    if not (isinstance(data, tuple) and len(data) == 2 and data[0] == "station"):
        return None
    favorite = app._radio_favorites.find(data[1])
    station = getattr(favorite, "station", None)
    if station is None:
        return None
    return dial.DialRow(key=station_key(station), station=station, list_kind=dial.FAVORITES)


def browse_row(tree: Any, item: Any) -> dial.DialRow | None:
    """A Browse Stations tree row, with the source it sits under."""
    data = tree.GetItemData(item)
    if not isinstance(data, dict):
        return None
    station = data.get("station")
    root = tree.GetRootItem()
    top = item
    parent = tree.GetItemParent(top)
    while parent.IsOk() and parent != root:
        top, parent = parent, tree.GetItemParent(parent)
    top_data = tree.GetItemData(top)
    source = str(top_data.get("node_id", "")) if isinstance(top_data, dict) else ""
    kind = {"networks": dial.NETWORKS, "favorites": dial.FAVORITES}.get(source, dial.BROWSE)
    return dial.DialRow(
        key=station_key(station),
        station=station,
        list_kind=kind,
        source=source,
        needs_resolve=bool(data.get("resolve_lazily")),
    )


def search_rows(stations: list[Any]) -> list[dial.DialRow]:
    return [dial.DialRow(key=station_key(s), station=s, list_kind=dial.SEARCH) for s in stations]
