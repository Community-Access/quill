"""Quill Radio's empty Favorites name the first station's two routes (FUX-09).

Built on the real window: with no favorites, the line before the tree says
what to do and the keys that do it, and it is where focus lands; with a
favorite, the line is gone and focus is on the tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.usefixtures("closed_machine_doors")


@pytest.fixture
def radio(quill_data_dir: Path, wx_session_app):
    from quill.apps.radio import RadioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    try:
        yield frame
    finally:
        frame._radio_shutdown()
        set_transition_announcement_policy(None)


def test_an_empty_favorites_tree_has_a_line_naming_browse_and_add_with_their_keys(radio) -> None:
    line = radio._favorites_first_task
    assert line.shown
    assert line.text == (
        "No favorite stations yet. Browse Stations (Ctrl+B) finds one online, or Add "
        "Custom Station (Ctrl+N) takes its address."
    )
    assert radio.said == []  # shown, never spoken (GATE-13)


def test_the_line_says_a_rebound_key(radio) -> None:
    from quill.ui.radio import favorites_first_task

    radio.keymap["radio.browse"] = "F7"
    favorites_first_task.refresh(radio)
    assert "Browse Stations (F7)" in radio._favorites_first_task.text


def test_launch_focus_lands_on_the_line_while_the_tree_is_empty(radio, monkeypatch) -> None:
    focused: list[object] = []
    monkeypatch.setattr(
        radio._favorites_first_task.ctrl, "SetFocus", lambda: focused.append("line")
    )
    monkeypatch.setattr(radio._favorites_tree, "SetFocus", lambda: focused.append("tree"))
    radio._focus_initial_control()
    assert focused == ["line"]


def test_a_first_favorite_hides_the_line_and_focus_goes_to_the_tree(radio, monkeypatch) -> None:
    from quill.core.radio.favorites import FavoriteStation
    from quill.core.radio.models import RadioStation

    radio._radio_favorites.favorites.append(
        FavoriteStation(station=RadioStation(name="KJAZZ", stream_url="http://example.invalid/k"))
    )
    radio._reload_favorites_tree()
    assert not radio._favorites_first_task.shown
    focused: list[object] = []
    monkeypatch.setattr(radio._favorites_tree, "SetFocus", lambda: focused.append("tree"))
    radio._focus_initial_control()
    assert focused == ["tree"]


def test_the_line_follows_a_key_rebound_while_the_window_is_open(radio) -> None:
    radio.keymap["radio.browse"] = "F7"
    radio._build_menu_bar()  # what Keyboard Shortcuts does after an edit
    assert "Browse Stations (F7)" in radio._favorites_first_task.text
