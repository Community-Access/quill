"""A system-wide key per favourite (xradio2 4.9, todo P3 Radio extras 6).

Driven against a fake frame that records RegisterHotKey calls: no real key is
registered and none is probed (the "held by another program" answer is a
fake too), so this is not a machine_global test.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.radio import favorite_hotkeys
from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.models import RadioStation

wx = pytest.importorskip("wx")

from quill.ui.radio import favorite_hotkeys_ui  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)


class _Frame:
    def __init__(self, *, refuse: set[int] | None = None) -> None:
        self.registered: dict[int, tuple[int, int]] = {}
        self.bound: dict[int, object] = {}
        self._refuse = refuse or set()

    def RegisterHotKey(self, hotkey_id: int, flags: int, code: int) -> bool:  # noqa: N802
        if code in self._refuse:
            return False
        self.registered[hotkey_id] = (flags, code)
        return True

    def UnregisterHotKey(self, hotkey_id: int) -> bool:  # noqa: N802
        self.registered.pop(hotkey_id, None)
        return True

    def Bind(self, _event, handler, id: int) -> None:  # noqa: A002, N802
        self.bound[id] = handler


class _Controller:
    def __init__(self) -> None:
        self.played: list[str] = []

    def play_station(self, station: RadioStation) -> None:
        self.played.append(station.name)


def _app(frame: _Frame | None = None):
    store = RadioFavoritesStore()
    store.add(RadioStation(name="WXYZ", stream_url="https://wxyz.test/"))
    store.add(RadioStation(name="KQED", stream_url="https://kqed.test/"))
    said: list[str] = []
    app = SimpleNamespace(
        frame=frame or _Frame(),
        _radio_favorites=store,
        _radio_controller=_Controller(),
        _announce=said.append,
        said=said,
    )
    return app


def test_there_are_no_keys_by_default(tmp_path: Path) -> None:
    app = _app()
    assert favorite_hotkeys.load_hotkeys(tmp_path) == {}
    assert favorite_hotkeys_ui.register_all(app, wx, platform="win32") == []
    assert app.frame.registered == {}


def test_a_chosen_key_is_saved_registered_and_plays_the_station(tmp_path: Path) -> None:
    app = _app()
    favorite = app._radio_favorites.favorites[0]

    changed = favorite_hotkeys_ui.choose_key(
        app,
        favorite,
        parent=None,
        ask=lambda _prompt, _current: "Ctrl+Alt+PageUp",
        claimed=lambda _chord: False,
    )

    assert changed
    assert favorite_hotkeys.load_hotkeys(tmp_path) == {favorite.key: "Ctrl+Alt+PageUp"}
    assert app.said[-1] == "Ctrl+Alt+PageUp now plays WXYZ from anywhere."
    favorite_hotkeys_ui.register_all(app, wx, platform="win32")
    (hotkey_id,) = app.frame.registered
    app.frame.bound[hotkey_id](None)
    assert app._radio_controller.played == ["WXYZ"]
    assert app.said[-1] == "Playing WXYZ."


def test_a_key_another_favorite_holds_is_refused_with_its_name(tmp_path: Path) -> None:
    app = _app()
    first, second = app._radio_favorites.favorites
    favorite_hotkeys.set_hotkey(tmp_path, first.key, "Ctrl+Alt+PageUp")

    changed = favorite_hotkeys_ui.choose_key(
        app,
        second,
        parent=None,
        ask=lambda _p, _c: "Ctrl+Alt+PageUp",
        claimed=lambda _chord: False,
    )

    assert not changed
    assert "already Quill Radio's key for WXYZ" in app.said[-1]
    assert favorite_hotkeys.load_hotkeys(tmp_path) == {first.key: "Ctrl+Alt+PageUp"}


def test_a_key_with_no_ctrl_or_alt_is_refused() -> None:
    app = _app()
    favorite = app._radio_favorites.favorites[0]
    favorite_hotkeys_ui.choose_key(
        app, favorite, parent=None, ask=lambda _p, _c: "Shift+F7", claimed=lambda _c: False
    )
    assert "no Ctrl or Alt" in app.said[-1]


def test_a_key_another_program_holds_is_refused() -> None:
    app = _app()
    favorite = app._radio_favorites.favorites[0]
    favorite_hotkeys_ui.choose_key(
        app,
        favorite,
        parent=None,
        ask=lambda _p, _c: "Ctrl+Alt+PageUp",
        claimed=lambda _c: True,
    )
    assert "held by another program" in app.said[-1]


def test_an_empty_answer_removes_the_key(tmp_path: Path) -> None:
    app = _app()
    favorite = app._radio_favorites.favorites[0]
    favorite_hotkeys.set_hotkey(tmp_path, favorite.key, "Ctrl+Alt+PageUp")

    favorite_hotkeys_ui.choose_key(
        app, favorite, parent=None, ask=lambda _p, _c: "", claimed=lambda _c: False
    )

    assert favorite_hotkeys.load_hotkeys(tmp_path) == {}
    assert app.said[-1] == "WXYZ no longer has a system-wide key."


def test_cancel_changes_nothing(tmp_path: Path) -> None:
    app = _app()
    favorite = app._radio_favorites.favorites[0]
    assert not favorite_hotkeys_ui.choose_key(
        app, favorite, parent=None, ask=lambda _p, _c: None, claimed=lambda _c: False
    )
    assert app.said == []


def test_keys_for_removed_favorites_are_not_registered(tmp_path: Path) -> None:
    app = _app()
    favorite_hotkeys.save_hotkeys(tmp_path, {"gone": "Ctrl+Alt+PageDown"})
    assert favorite_hotkeys_ui.register_all(app, wx, platform="win32") == []
    assert app.frame.registered == {}


def test_a_key_windows_refuses_at_startup_is_reported_not_kept() -> None:
    app = _app(_Frame(refuse={wx.WXK_PAGEUP, 0x21}))
    favorite = app._radio_favorites.favorites[0]
    favorite_hotkeys.save_hotkeys(
        Path(favorite_hotkeys_ui._data_dir()), {favorite.key: "Ctrl+Alt+PageUp"}
    )
    assert favorite_hotkeys_ui.register_all(app, wx, platform="win32") == ["Ctrl+Alt+PageUp"]
    assert app.frame.registered == {}


def test_nothing_is_registered_off_windows(tmp_path: Path) -> None:
    app = _app()
    favorite = app._radio_favorites.favorites[0]
    favorite_hotkeys.set_hotkey(tmp_path, favorite.key, "Ctrl+Alt+PageUp")
    assert favorite_hotkeys_ui.register_all(app, wx, platform="linux") == []
    assert app.frame.registered == {}
