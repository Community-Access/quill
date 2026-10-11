"""A listener's request: the station's website beside Play and Stop."""

from __future__ import annotations

import sys
import threading
from types import SimpleNamespace

from quill.core.radio.history import RadioHistory, load_history
from quill.core.radio.history_writer import RadioHistorySnapshotWriter
from quill.core.radio.website_overrides import station_key
from quill.ui.radio import station_website_button as site
from quill.ui.radio.history_save import RadioHistorySaveCoordinator


def _host(playing=None, favorite=None) -> SimpleNamespace:
    said: list[str] = []
    return SimpleNamespace(
        _radio_controller=SimpleNamespace(state=SimpleNamespace(station=playing)),
        _selected_favorite=lambda: favorite,
        _radio_history=SimpleNamespace(website_overrides={}),
        _announce=said.append,
        said=said,
    )


def test_the_playing_station_wins_and_its_site_opens() -> None:
    playing = SimpleNamespace(display_name="Double Tap Live", homepage="https://doubletaponair.com")
    other = SimpleNamespace(display_label="Other", station=SimpleNamespace(homepage="https://x"))
    host = _host(playing, other)
    opened: list[str] = []
    assert site.press(host, opener=lambda url: opened.append(url) or True)
    assert opened == ["https://doubletaponair.com"]
    assert host.said == ["Opened the website for Double Tap Live."]


def test_with_nothing_playing_the_selected_favorite_is_used() -> None:
    favorite = SimpleNamespace(
        display_label="KSPN", station=SimpleNamespace(homepage="https://espn.com")
    )
    assert site.target(_host(None, favorite)) == ("KSPN", "https://espn.com")


def test_a_station_without_a_website_can_be_given_one_and_opened() -> None:
    playing = SimpleNamespace(display_name="Mystery FM", homepage="")
    host = _host(playing)
    opened: list[str] = []
    assert site.press(
        host,
        opener=lambda url: opened.append(url) or True,
        add_website=lambda *_args: "https://mystery.example.org",
    )
    assert opened == ["https://mystery.example.org"]
    assert host.said == ["Opened the website for Mystery FM."]


def test_cancelling_website_entry_does_not_open_a_browser() -> None:
    playing = SimpleNamespace(display_name="Mystery FM", homepage="")
    host = _host(playing)
    opened: list[str] = []
    assert not site.press(
        host,
        opener=lambda url: opened.append(url) or True,
        add_website=lambda *_args: None,
    )
    assert opened == []


def test_edit_website_normalizes_and_persists_the_local_override(monkeypatch, tmp_path) -> None:
    class TextEntryDialog:
        def __init__(self, _parent, _prompt, _title, *, value):
            self.value = value

        def GetValue(self):
            return "mystery.example.org"

        def Destroy(self):
            pass

    fake_wx = SimpleNamespace(
        ID_OK=1,
        ID_CANCEL=2,
        TextEntryDialog=TextEntryDialog,
    )
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    monkeypatch.setattr("quill.ui.dialog_contract.apply_modal_ids", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "quill.ui.dialog_contract.show_modal_dialog",
        lambda *_args, **_kwargs: fake_wx.ID_OK,
    )
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)

    station = SimpleNamespace(
        source="Radio Browser",
        station_uuid="station-123",
        name="Mystery FM",
        display_name="Mystery FM",
        stream_url="https://stream.example.org/live",
        homepage="",
    )
    history = RadioHistory()
    host = SimpleNamespace(_radio_history=history, _announce=lambda _message: None)

    assert site.edit_website(host, station, parent=object()) == "https://mystery.example.org"
    key = station_key(station)
    assert history.website_overrides == {key: "https://mystery.example.org"}
    coordinator = host._radio_history_save_coordinator
    try:
        assert coordinator.flush(3)
        assert load_history(tmp_path).website_overrides == {key: "https://mystery.example.org"}
    finally:
        coordinator.close()


def test_history_write_failure_is_dispatched_for_ui_thread_announcement(tmp_path) -> None:
    messages: list[tuple[str, int]] = []
    callbacks: list[tuple[int, object]] = []
    ui_thread = threading.get_ident()

    def fail_write(_data_dir, _snapshot):
        raise OSError("settings are not writable")

    writer = RadioHistorySnapshotWriter(fail_write)
    coordinator = RadioHistorySaveCoordinator(
        lambda message: messages.append((message, threading.get_ident())),
        writer=writer,
        dispatch=lambda callback: callbacks.append((threading.get_ident(), callback)),
    )
    try:
        coordinator.save(tmp_path, RadioHistory())
        assert not writer.flush(2)
        assert messages == []
        assert callbacks
        callback_thread, callback = callbacks[0]
        assert callback_thread != ui_thread
        callback()  # type: ignore[operator]
        assert messages == [
            (
                "Radio settings could not be saved. Check that Quill can write its settings.",
                ui_thread,
            )
        ]
    finally:
        coordinator.close()


def test_worker_only_receives_a_detached_history_snapshot(tmp_path) -> None:
    entered = threading.Event()
    release = threading.Event()
    snapshots: list[dict[str, object]] = []

    def block_write(_data_dir, snapshot):
        snapshots.append(snapshot)
        entered.set()
        assert release.wait(3)

    history = RadioHistory(website_overrides={"station": "https://before.example"})
    writer = RadioHistorySnapshotWriter(block_write)
    coordinator = RadioHistorySaveCoordinator(None, writer=writer)
    try:
        coordinator.save(tmp_path, history)
        assert entered.wait(2)
        history.website_overrides["station"] = "https://after.example"
        assert snapshots[0]["website_overrides"] == {"station": "https://before.example"}
    finally:
        release.set()
        coordinator.close()


def test_nothing_to_point_at_says_how_to_get_one() -> None:
    host = _host()
    assert not site.press(host, opener=lambda _url: True)
    assert "Favorites" in host.said[0]
