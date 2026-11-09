"""Dial tuning from the app's side: the lists, the player, the neighbours, the hiss.

The policy has its own tests (tests/unit/core/radio/test_radio_dial_tuning_policy.py);
these drive the glue with the real ``RadioPlayerController``, a fake mpv engine
pool, a fake hiss backend and a fake clock. No real mpv, no network, no sound.
Dial tuning is an idea from BlindRadio by serrebidev (MIT).
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.apps import radio_preferences_dial as prefs
from quill.core.radio import dial_tuning as dial
from quill.core.radio.history import RadioHistory
from quill.core.radio.models import RadioStation
from quill.ui.radio import (
    dial_tuning_commands,
    dial_tuning_ui,
    engine_selection,
    song_history_commands,
    stats_session,
)
from quill.ui.radio.dial_hiss_player import HissPlayer
from quill.ui.radio.dial_warm_pool import WarmPool
from quill.ui.radio.playback_state import RadioPlayerState
from quill.ui.radio.player_controller import RadioPlayerController


class Clock:
    def __init__(self) -> None:
        self.now = 50.0

    def __call__(self) -> float:
        return self.now


class _Extras:
    def __init__(self) -> None:
        self.loads = 0
        self.marks = type("M", (), {"station_name": ""})()

    def on_load(self) -> None:
        self.loads += 1


class FakeMpv:
    """Just enough of MpvRadioEngine for the controller and the pool."""

    made: list[FakeMpv] = []

    def __init__(self, *_parent: Any, **kw: Any) -> None:
        self._on_loaded = kw.get("on_loaded")
        self._on_finished = kw.get("on_finished")
        self._on_error = kw.get("on_error")
        self._on_buffering = kw.get("on_buffering")
        self.timeshift = kw.get("timeshift_minutes", "unset")
        self._loaded = False
        self.loads: list[str] = []
        self.volume: int | None = None
        self.device: str | None = None
        self.graph: str | None = None
        self.closed = 0
        self.terminated = False
        self.live_extras = _Extras()
        FakeMpv.made.append(self)

    # what the tests do to it
    def connect(self) -> None:
        self._loaded = True
        self._on_loaded(0)

    def fail(self) -> None:
        self._on_error("That stream could not be opened.")

    # engine protocol
    def load(self, url: str) -> bool:
        self.loads.append(url)
        self._loaded = False
        return True

    def close(self) -> None:
        self.closed += 1
        self._loaded = False

    def terminate(self) -> None:
        self.terminated = True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def set_volume(self, percent: int) -> None:
        self.volume = percent

    def set_audio_device(self, name: str) -> None:
        self.device = name

    def set_filter_graph(self, graph: str) -> None:
        self.graph = graph

    def configure_timeshift(self, minutes: Any) -> None:
        self.timeshift = minutes

    def set_bounded(self, _bounded: bool) -> None:
        pass

    def is_bounded(self) -> bool:
        return False

    def set_real_time(self, _on: bool) -> None:
        pass

    def position_ms(self) -> int:
        return 0

    def length_ms(self) -> int:
        return 0


class FakeWx:
    """CallLater only records; the test ticks the dial itself."""

    def __init__(self) -> None:
        self.later: list[Any] = []

    def CallLater(self, ms: int, fn: Any) -> Any:  # noqa: N802 - wx's name
        self.later.append((ms, fn))
        return type("T", (), {"Stop": lambda _self: None})()


class Recorder:
    active_count = 0


class App:
    def __init__(self, frame: Any, controller: RadioPlayerController) -> None:
        self.frame = frame
        self._radio_history = RadioHistory(dial_tuning=True)
        self._radio_controller = controller
        self._radio_recorder = Recorder()
        self._radio_history_key = ""
        self._radio_track_title = ""
        self.said: list[str] = []

    def _announce(self, text: str) -> None:
        self.said.append(text)


def station(name: str) -> RadioStation:
    return RadioStation(name=name, stream_url=f"http://example.test/{name}")


def row(name: str) -> dial.DialRow:
    s = station(name)
    return dial.DialRow(key=s.stream_url, station=s, list_kind=dial.FAVORITES)


@pytest.fixture
def rig(wx_session_app: Any, monkeypatch: pytest.MonkeyPatch):
    FakeMpv.made = []
    monkeypatch.setattr(engine_selection, "mpv_output_device_available", lambda: True)
    frame = wx.Frame(None)
    controller = RadioPlayerController(frame, playback_engine="mpv", output_device="Speakers")
    main = FakeMpv(
        on_loaded=controller._on_loaded,
        on_finished=controller._on_finished,
        on_error=controller._on_error,
    )
    controller._mpv_engine = main
    controller._engine = main
    app = App(frame, controller)
    hiss_log: list[str] = []
    hiss = HissPlayer(
        backend=(
            lambda path: hiss_log.append(f"start {path.name}"),
            lambda: hiss_log.append("stop"),
        )
    )
    clock = Clock()
    fake_wx = FakeWx()
    pool = WarmPool(frame, factory=lambda parent, **kw: FakeMpv(parent, **kw))
    ui = dial_tuning_ui.DialTuningUI(
        app, fake_wx, clock=clock, pool=pool, hiss=hiss, is_metered=lambda: False
    )
    controller._on_state_changed = ui.on_state_changed
    yield type(
        "Rig",
        (),
        {
            "app": app,
            "controller": controller,
            "main": main,
            "ui": ui,
            "clock": clock,
            "wx": fake_wx,
            "pool": pool,
            "hiss": hiss_log,
        },
    )()
    ui.shutdown()
    frame.Destroy()


def settle(rig: Any, current: dial.DialRow, before: Any = None, after: Any = None) -> None:
    rig.ui.focus(current, before, after)
    rig.clock.now += 1.0
    rig.ui._tick()


# -- tuning ----------------------------------------------------------------------


def test_settling_plays_quietly_with_the_hiss_and_records_nothing(rig):
    a = row("A")
    settle(rig, a)
    assert rig.controller.state.station == a.station
    assert rig.main.loads == [a.station.stream_url]
    assert rig.controller.dial_quiet is True
    assert rig.hiss == ["start dial_hiss_low.wav"]
    assert dial_tuning_ui.passing_through(rig.app, a.station)
    assert dial_tuning_ui.quiet(rig.app, rig.controller.state)
    rig.main.connect()
    assert rig.controller.state.state is RadioPlayerState.PLAYING
    assert rig.hiss[-1] == "stop"
    assert rig.app.said == []  # GATE-13: the reader read the row; nothing more


def test_nothing_plays_before_the_wait(rig):
    rig.ui.focus(row("A"))
    rig.clock.now += 0.2
    rig.ui._tick()
    assert rig.controller.state.station is None
    assert rig.wx.later, "a timer is armed for the rest of the wait"


def test_neighbours_connect_muted_once_the_station_is_on(rig):
    before, a, after = row("B"), row("A"), row("C")
    settle(rig, a, before, after)
    assert rig.pool.engine_count == 0  # not while connecting
    rig.main.connect()
    assert set(rig.pool.keys) == {before.key, after.key}
    warm = [e for e in FakeMpv.made if e is not rig.main]
    assert len(warm) == 2 and all(e.volume == 0 and e.graph == "" for e in warm)
    assert all(e.device == "Speakers" for e in warm)
    assert len(FakeMpv.made) <= dial.MAX_PLAYERS


def test_a_real_neighbour_buffers_in_memory_only(monkeypatch):
    from quill.ui.radio import dial_warm_pool, mpv_radio_engine

    monkeypatch.setattr(mpv_radio_engine, "MpvRadioEngine", FakeMpv)
    engine = dial_warm_pool._default_factory(None, on_loaded=None)
    assert engine.timeshift == 0  # nothing on disk, and no sweep of the cache folder


def test_promotion_keeps_every_engine_property(rig):
    before, a, after = row("B"), row("A"), row("C")
    rig.controller.set_volume(40)
    settle(rig, a, before, after)
    rig.main.connect()
    warm_after = next(e for e in FakeMpv.made if e.loads == [after.station.stream_url])
    warm_after.connect()
    settle(rig, after, a, row("D"))
    controller = rig.controller
    assert controller._mpv_engine is warm_after and controller._engine is warm_after
    assert warm_after.loads == [after.station.stream_url]  # no reload: it was warm
    assert warm_after.device == "Speakers"
    assert warm_after.volume == controller._effective_volume() == 40
    assert warm_after.graph == controller._current_filter_graph()
    assert warm_after.live_extras.loads == 1
    assert warm_after.live_extras.marks.station_name == "C"
    assert warm_after._on_loaded == controller._on_loaded
    assert controller.state.station == after.station
    assert controller.state.state is RadioPlayerState.PLAYING
    # The old engine went back to the pool, muted, still on the station left.
    assert rig.main.volume == 0
    assert a.key in rig.pool.keys
    assert len(FakeMpv.made) <= dial.MAX_PLAYERS


def test_a_cold_station_plays_through_the_ordinary_path(rig):
    a, c = row("A"), row("C")
    settle(rig, a)
    rig.main.connect()
    settle(rig, c)
    assert rig.main.loads[-1] == c.station.stream_url


def test_enter_commits_with_a_fresh_connection(rig):
    a = row("A")
    settle(rig, a)
    rig.main.connect()
    rig.app._radio_history_key = a.key
    assert dial_tuning_ui.commit(rig.controller, a.station) is True
    assert rig.main.loads == [a.station.stream_url, a.station.stream_url]
    assert rig.controller.dial_quiet is False
    assert rig.app._radio_history_key == ""
    assert not dial_tuning_ui.passing_through(rig.app, a.station)
    assert dial_tuning_ui.commit(rig.controller, a.station) is False


def test_enter_on_a_row_the_dial_did_not_tune_is_left_alone(rig):
    assert dial_tuning_ui.commit(rig.controller, station("X")) is False
    assert dial_tuning_ui.commit(rig.controller, None) is False


def test_playing_something_else_ends_the_dial_session(rig):
    a, b, c = row("A"), row("B"), row("C")
    settle(rig, a, b, c)
    rig.main.connect()
    rig.controller.play_station(station("Elsewhere"))
    assert rig.ui.tuner.current_key == ""
    assert rig.pool.keys == ()
    assert rig.controller.dial_quiet is False


def test_recording_pauses_tuning_and_says_so_once(rig):
    rig.app._radio_recorder.active_count = 1
    settle(rig, row("A"))
    settle(rig, row("B"))
    assert rig.controller.state.station is None
    assert rig.app.said == [dial.RECORDING_PAUSED]


def test_dead_station_hiss_stops_then_says_once(rig):
    a = row("Dead FM")
    settle(rig, a)
    rig.clock.now += dial.SILENT_AFTER_S
    rig.ui._tick()
    assert rig.hiss[-1] == "stop"
    rig.clock.now += dial.SAY_AFTER_S
    rig.ui._tick()
    rig.clock.now += 30
    rig.ui._tick()
    assert rig.app.said == ["Dead FM is not answering."]


def test_mute_silences_the_hiss(rig):
    rig.controller.toggle_mute()
    settle(rig, row("A"))
    assert rig.hiss == []


def test_turning_off_lets_the_neighbours_go(rig):
    a, b, c = row("A"), row("B"), row("C")
    settle(rig, a, b, c)
    rig.main.connect()
    rig.app._radio_history.dial_tuning = False
    rig.ui.reload_settings()
    assert rig.pool.keys == ()
    assert rig.controller.dial_quiet is False


def test_leaving_the_list_keeps_playing_and_lets_neighbours_go(rig):
    a, b, c = row("A"), row("B"), row("C")
    settle(rig, a, b, c)
    rig.main.connect()
    rig.ui.left_list()
    assert rig.controller.state.station == a.station
    assert rig.pool.keys == ()


def test_the_dial_keeps_your_volume_unless_asked(rig):
    a = row("A")
    settle(rig, a)
    assert dial_tuning_ui.tuned_volume(rig.app, a.station)
    rig.app._radio_history.dial_remember_volume = True
    rig.ui.reload_settings()
    assert not dial_tuning_ui.tuned_volume(rig.app, a.station)


def test_shutdown_terminates_every_neighbour(rig):
    a, b, c = row("A"), row("B"), row("C")
    settle(rig, a, b, c)
    rig.main.connect()
    warm = [e for e in FakeMpv.made if e is not rig.main]
    rig.ui.shutdown()
    assert all(e.terminated for e in warm)


# -- the command -------------------------------------------------------------------


def test_toggle_says_the_new_state_and_saves(rig, monkeypatch):
    saved: list[Any] = []
    monkeypatch.setattr(
        "quill.ui.radio.history_save.save_history_async", lambda app, h: saved.append(h)
    )
    rig.app._radio_history.dial_tuning = False
    rig.ui.reload_settings()
    dial_tuning_commands.toggle_dial_tuning(rig.app)
    assert rig.app._radio_history.dial_tuning is True
    assert rig.app.said == [dial.state_word(True)]
    dial_tuning_commands.toggle_dial_tuning(rig.app)
    assert rig.app.said[-1] == dial.state_word(False)
    assert len(saved) == 2


# -- bookkeeping for stations only passed through ----------------------------------


def test_passed_through_stations_are_not_logged_or_counted(rig, monkeypatch):
    a = row("A")
    settle(rig, a)
    rig.main.connect()
    seen: list[str] = []
    monkeypatch.setattr(
        "quill.ui.radio.scrobble_commands.on_title", lambda host, title: seen.append(title)
    )
    song_history_commands.record_song(rig.app, "Artist - Song")
    assert seen == []
    stats_session.on_state_changed(rig.app, rig.controller.state)
    assert getattr(rig.app, "_radio_stats_started", None) is None


# -- the list hooks ----------------------------------------------------------------


class _Favorites:
    def __init__(self, stations: list[RadioStation]) -> None:
        self._by_key = {
            s.stream_url: type("F", (), {"station": s, "key": s.stream_url})() for s in stations
        }

    def find(self, key: str) -> Any:
        return self._by_key.get(key)


def _favorites_tree(rig: Any, names: list[str]) -> tuple[Any, list[Any]]:
    stations = [station(n) for n in names]
    rig.app._radio_favorites = _Favorites(stations)
    tree = wx.TreeCtrl(rig.app.frame, style=wx.TR_HIDE_ROOT)
    root = tree.AddRoot("Favorites")
    folder = tree.AppendItem(root, "Folder")
    tree.SetItemData(folder, ("folder", "Folder"))
    items = []
    for s in stations:
        item = tree.AppendItem(root, s.name)
        tree.SetItemData(item, ("station", s.stream_url))
        items.append(item)
    return tree, items


def test_a_tree_row_reports_itself_and_its_station_neighbours(rig, monkeypatch):
    tree, items = _favorites_tree(rig, ["A", "B", "C"])
    seen: list[tuple[Any, Any, Any]] = []
    monkeypatch.setattr(rig.ui, "focus", lambda r, b=None, a=None: seen.append((r, b, a)))
    monkeypatch.setattr(dial_tuning_ui, "_focused", lambda window, _wx: window is tree)
    dial_tuning_ui.attach_tree(
        rig.controller, tree, lambda item: dial_tuning_ui.favorite_row(rig.app, tree, item), wx
    )
    tree.SelectItem(items[1])
    event = wx.TreeEvent(wx.wxEVT_TREE_SEL_CHANGED, tree, items[1])
    tree.GetEventHandler().ProcessEvent(event)
    current, before, after = seen[-1]
    assert current.name == "B" and before.name == "A" and after.name == "C"


def test_a_folder_row_never_tunes(rig):
    tree, _items = _favorites_tree(rig, ["A"])
    folder, _cookie = tree.GetFirstChild(tree.GetRootItem())
    assert dial_tuning_ui.favorite_row(rig.app, tree, folder) is None


def test_browse_rows_carry_their_source(rig):
    tree = wx.TreeCtrl(rig.app.frame, style=wx.TR_HIDE_ROOT)
    root = tree.AddRoot("Browse")
    nets = tree.AppendItem(root, "Networks")
    tree.SetItemData(nets, {"node_id": "networks"})
    leaf = tree.AppendItem(nets, "KEXP")
    tree.SetItemData(leaf, {"node_id": "x", "station": station("KEXP"), "resolve_lazily": False})
    pods = tree.AppendItem(root, "Podcasts")
    tree.SetItemData(pods, {"node_id": "apple"})
    show = tree.AppendItem(pods, "Show")
    tree.SetItemData(show, {"node_id": "y", "station": station("Show"), "resolve_lazily": True})
    network_row = dial_tuning_ui.browse_row(tree, leaf)
    assert network_row.list_kind == dial.NETWORKS and dial.row_tunes(network_row)
    assert not dial.row_tunes(dial_tuning_ui.browse_row(tree, show))


def test_search_results_report_neighbours(rig, monkeypatch):
    results = wx.ListCtrl(rig.app.frame, style=wx.LC_REPORT)
    results.InsertColumn(0, "Name")
    stations = [station(n) for n in ("A", "B", "C")]
    for index, s in enumerate(stations):
        results.InsertItem(index, s.name)
    seen: list[tuple[Any, Any, Any]] = []
    monkeypatch.setattr(rig.ui, "focus", lambda r, b=None, a=None: seen.append((r, b, a)))
    monkeypatch.setattr(dial_tuning_ui, "_focused", lambda window, _wx: window is results)
    dial_tuning_ui.attach_list(
        rig.controller, results, lambda: dial_tuning_ui.search_rows(stations), wx
    )
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_FOCUSED, results.GetId())
    event.SetEventObject(results)
    event.SetIndex(0)
    results.GetEventHandler().ProcessEvent(event)
    current, before, after = seen[-1]
    assert current.name == "A" and before is None and after.name == "B"
    assert current.list_kind == dial.SEARCH


def test_go_to_playing_station_lands_on_the_favorite(rig):
    tree, items = _favorites_tree(rig, ["A", "B"])
    rig.app._favorites_tree = tree
    rig.app._main_view_host = None
    rig.controller._state.station = station("B")
    dial_tuning_commands.go_to_playing_station(rig.app)
    assert tree.GetSelection() == items[1]
    assert rig.app.said == []  # the reader reads the row


def test_go_to_playing_station_says_when_there_is_nothing(rig):
    rig.app._radio_favorites = _Favorites([])
    rig.app._favorites_tree = None
    rig.app._main_view_host = None
    dial_tuning_commands.go_to_playing_station(rig.app)
    assert rig.app.said == ["Nothing is playing."]
    rig.controller._state.station = station("Z")
    dial_tuning_commands.go_to_playing_station(rig.app)
    assert rig.app.said[-1] == "Z is playing. It is not in this list."


def test_menu_rows_show_their_keys(rig):
    menu = wx.Menu()
    rig.app._menu_label = lambda title, command_id: f"{title}\t{command_id}"
    ids = dial_tuning_commands.append_menu_items(rig.app, menu, wx)
    labels = [menu.FindItemById(int(i)).GetItemLabel() for i in ids]
    assert labels[0].endswith("radio.dial_tuning") and labels[1].endswith(
        "radio.go_to_playing_station"
    )
    assert menu.FindItemById(int(ids[0])).IsChecked() is True


# -- Preferences ---------------------------------------------------------------------


def test_preferences_rows_default_off_and_apply(rig):
    history = RadioHistory()
    rig.app._radio_history = history
    rows = prefs.DialRows(rig.app)
    checks = rows.checkboxes()
    assert [c.value for c in checks] == [False, True, True, True, False]
    assert all(c.group == prefs.GROUP and c.help_text for c in checks)
    choices = rows.choices()
    assert [c.selected_index for c in choices] == [2, 0]
    assert all(c.after_checks for c in choices)
    rows.apply([True, False, False, False, True], [4, 1])
    assert history.dial_tuning and not history.dial_keep_neighbours
    assert history.dial_wait_ms == 1000 and history.dial_hiss_level == "medium"
    assert history.dial_remember_volume
    assert rig.ui.enabled  # applied at once


def test_resting_on_the_station_already_playing_does_not_restart_it(rig):
    a = row("A")
    rig.controller.play_station(a.station)  # played the ordinary way, before the dial
    rig.main.connect()
    loads = list(rig.main.loads)
    settle(rig, a)
    assert rig.main.loads == loads
    assert not dial_tuning_ui.passing_through(rig.app, a.station)


def test_the_hiss_loops_on_its_own_mci_device_and_stops_only_itself() -> None:
    from pathlib import Path as _Path

    from quill.ui.radio import dial_hiss_player

    sent: list[str] = []
    start, stop = dial_hiss_player.mci_backend(lambda command: sent.append(command) or 0)
    start(_Path("C:/clips/hiss-soft.wav"))
    assert sent[-2:] == [
        'open "C:\clips\hiss-soft.wav" type mpegvideo alias quill_dial_hiss',
        "play quill_dial_hiss repeat",
    ]
    sent.clear()
    stop()
    assert sent == ["stop quill_dial_hiss", "close quill_dial_hiss"], (
        "never a process-wide winsound stop, which cut off every earcon"
    )


def test_the_hiss_falls_back_to_winsound_when_mci_refuses(monkeypatch) -> None:
    from pathlib import Path as _Path

    from quill.ui.radio import dial_hiss_player

    refused = dial_hiss_player.mci_backend(lambda command: 263 if command.startswith("open") else 0)
    calls: list[str] = []
    monkeypatch.setattr(dial_hiss_player, "mci_backend", lambda send=None: refused)
    monkeypatch.setattr(
        dial_hiss_player,
        "winsound_backend",
        lambda: (lambda path: calls.append(f"loop {path.name}"), lambda: calls.append("stop")),
    )
    start, stop = dial_hiss_player.default_backend()
    start(_Path("hiss.wav"))
    stop()
    assert calls == ["loop hiss.wav", "stop"]
