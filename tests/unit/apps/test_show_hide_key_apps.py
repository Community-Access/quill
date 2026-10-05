"""Weather, Converter, Media Player and Inkwell: no show/hide key by default, a
File menu row to choose one, and the once-only sentence for somebody who had
the old default (questions.md 37b, option 3, 2026-10-05).

Real frames, never shown. ``machine_global`` because a frame that *does* get a
key registers it system-wide (tests/conftest.py groups those on one worker).
"""

from __future__ import annotations

import pytest
import wx

pytestmark = pytest.mark.machine_global


@pytest.fixture
def app():
    a = wx.App(False)
    yield a
    a.Destroy()


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def later(monkeypatch):
    """The show/hide sentence each frame schedules with wx.CallLater, captured
    instead of run (anything else scheduled is dropped)."""
    calls: list[tuple] = []

    def capture(_ms, fn, *args):
        if getattr(fn, "__name__", "") == "_say_show_hide_notice":
            calls.append((fn, args))

    monkeypatch.setattr(wx, "CallLater", capture)
    return calls


def _file_labels(frame) -> list[str]:
    bar = frame.frame.GetMenuBar()
    menu = bar.GetMenu(bar.FindMenu("File"))
    return [item.GetItemLabel() for item in menu.GetMenuItems() if not item.IsSeparator()]


def _weather():
    from quill.apps.weather import WeatherAppFrame

    return WeatherAppFrame(safe_mode=True)


def _inkwell():
    from quill.apps.inkwell import QuillInkwellFrame

    return QuillInkwellFrame(safe_mode=True)


def _close(frame) -> None:
    for name in ("_ipc_timer",):
        timer = getattr(frame, name, None)
        if timer is not None:
            timer.Stop()
    remove = getattr(frame, "_remove_tray_icon", None)
    if remove is not None:
        remove()
    frame.frame.Destroy()


@pytest.mark.parametrize("build", [_weather, _inkwell], ids=["weather", "inkwell"])
def test_no_key_by_default_and_a_row_to_choose_one(app, data_dir, later, build) -> None:
    frame = build()
    try:
        assert frame._show_hide_key == ""
        assert not getattr(frame, "_tray_hotkey_registered", False)
        assert "Show and &Hide Key...\tCtrl+Alt+Shift+H" in _file_labels(frame)
        assert later == []  # somebody new is told nothing
    finally:
        _close(frame)


def test_a_weather_user_who_had_the_old_key_is_told_once(app, data_dir, later) -> None:
    from quill.core.family_chords import retired_key_notice

    (data_dir / "weather_settings.json").write_text("{}", encoding="utf-8")
    frame = _weather()
    try:
        assert frame._show_hide_key == ""
        assert [args for _fn, args in later] == [(retired_key_notice("weather"),)]
    finally:
        _close(frame)
    later.clear()
    frame = _weather()
    try:
        assert later == []
    finally:
        _close(frame)


def test_an_inkwell_user_who_had_the_old_key_is_told_once(app, data_dir, later) -> None:
    from quill.core.expansion.settings import InkwellSettings, load_settings, save_settings
    from quill.core.family_chords import retired_key_notice

    save_settings(data_dir, InkwellSettings(tray_hotkey="Ctrl+Alt+Shift+I"))
    frame = _inkwell()
    try:
        assert [args for _fn, args in later] == [(retired_key_notice("inkwell"),)]
        assert load_settings(data_dir).tray_hotkey == ""
    finally:
        _close(frame)


def test_the_converters_shortcut_list_names_only_a_chosen_key() -> None:
    from quill.apps.converter_menu import shortcut_list

    bar = type("Bar", (), {"GetMenuCount": lambda self: 0})()
    assert "Anywhere" not in shortcut_list(bar)
    assert "Anywhere: Ctrl+Alt+Shift+Left shows or hides Quill Converter" in shortcut_list(
        bar, "Ctrl+Alt+Shift+Left"
    )


def test_converter_and_player_start_with_no_key() -> None:
    """The two frames whose construction needs FFmpeg or a media engine are
    checked at the source: each asks the shared store, never a literal."""
    from pathlib import Path

    apps = Path(__file__).resolve().parents[3] / "quill" / "apps"
    assert 'self._start_show_hide_key("converter"' in (apps / "converter.py").read_text("utf-8")
    assert 'self._start_show_hide_key("player")' in (apps / "player.py").read_text("utf-8")
    assert '_append_show_hide_key_item(file_menu, "converter")' in (
        apps / "converter_menu.py"
    ).read_text("utf-8")
    assert '_append_show_hide_key_item(file_menu, "player")' in (
        apps / "player_menus.py"
    ).read_text("utf-8")


# -- Inkwell's Quick Insert and Expand Word keys (2026-10-05) ------------------ #


def test_inkwell_registers_neither_other_key_by_default_and_offers_both_rows(
    app, data_dir, later
) -> None:
    frame = _inkwell()
    try:
        assert not any(getattr(frame, "_inkwell_keys", {}).values())
        labels = _file_labels(frame)
        assert "&Quick Insert Key...\tCtrl+Alt+Shift+K" in labels
        assert "Expand &Word Key...\tCtrl+Alt+Shift+E" in labels
        assert later == []
    finally:
        _close(frame)


def test_an_inkwell_user_on_the_old_quick_insert_and_expand_keys_is_told_once(
    app, data_dir, later
) -> None:
    from quill.core.expansion.settings import (
        InkwellSettings,
        load_settings,
        retired_keys_notice,
        save_settings,
    )

    save_settings(
        data_dir,
        InkwellSettings(
            quick_insert_hotkey="Ctrl+Alt+Shift+K", expand_now_hotkey="Ctrl+Alt+Shift+X"
        ),
    )
    frame = _inkwell()
    try:
        assert [args for _fn, args in later] == [
            (retired_keys_notice(["Quick Insert", "Expand Word"]),)
        ]
        assert not any(getattr(frame, "_inkwell_keys", {}).values())
        saved = load_settings(data_dir)
        assert (saved.quick_insert_hotkey, saved.expand_now_hotkey) == ("", "")
    finally:
        _close(frame)
    later.clear()
    frame = _inkwell()
    try:
        assert later == []
    finally:
        _close(frame)


def test_choosing_inkwells_quick_insert_key_keeps_it(app, data_dir, later, monkeypatch) -> None:
    from quill.core.expansion.settings import load_settings
    from quill.ui import show_hide_key_picker

    frame = _inkwell()
    swapped: list[tuple[int, str]] = []
    said: list[str] = []
    try:
        monkeypatch.setattr(
            show_hide_key_picker, "choose_show_hide_key", lambda *_a, **_k: "Ctrl+Alt+PageDown"
        )
        monkeypatch.setattr(
            frame, "_replace_global_hotkey", lambda hid, chord: swapped.append((hid, chord)) or True
        )
        monkeypatch.setattr(frame, "_announce", lambda text, **_k: said.append(text))
        frame.choose_inkwell_key("quick_insert_hotkey")
        assert [chord for _hid, chord in swapped] == ["Ctrl+Alt+PageDown"]
        assert load_settings(data_dir).quick_insert_hotkey == "Ctrl+Alt+PageDown"
        assert said == ["Ctrl+Alt+PageDown now opens Quill Inkwell's Quick Insert."]
    finally:
        _close(frame)
