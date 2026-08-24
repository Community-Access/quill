"""Which one window Quill Radio opens itself with, if any.

It was a checkbox -- "Open Browse Stations at startup" -- and a checkbox can
only answer for one of the six windows there now. It is a choice of exactly one
or none, everything else stays closed, and none is the default.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.radio import startup_window as startup


def test_none_is_the_first_answer_and_the_default() -> None:
    """An app that opens a window you did not ask for is one you must close."""
    assert startup.STARTUP_WINDOWS[0][0] == startup.NONE
    assert startup.normalize(None) == startup.NONE
    assert startup.index_of(startup.NONE) == 0


@pytest.mark.parametrize("window_id", ["browse", "search", "favorites", "recordings", "player"])
def test_every_offered_window_round_trips(window_id: str) -> None:
    assert startup.is_valid(window_id)
    assert startup.from_index(startup.index_of(window_id)) == window_id
    assert startup.label(window_id) != startup.label(startup.NONE)


@pytest.mark.parametrize("junk", [None, 42, "carrier pigeon", ["browse"], object()])
def test_junk_reads_as_none_rather_than_raising(junk: Any) -> None:
    """A settings file with a typo behaves like one with nothing in it."""
    assert startup.normalize(junk) == startup.NONE
    assert startup.index_of(junk) == 0
    assert startup.label(junk) == startup.STARTUP_WINDOWS[0][1]


@pytest.mark.parametrize("junk", [None, -1, 99, "1", 1.5])
def test_an_impossible_selection_reads_as_none(junk: Any) -> None:
    assert startup.from_index(junk) == startup.NONE


def test_the_old_checkbox_becomes_the_choice_it_meant() -> None:
    """An upgrade must not take away a window somebody chose to have."""
    assert startup.migrate_from_checkbox(True) == "browse"
    assert startup.migrate_from_checkbox(False) == startup.NONE


def test_a_stored_choice_survives_a_history_round_trip(tmp_path) -> None:
    from quill.core.radio.history import RadioHistory, load_history, save_history

    history = RadioHistory()
    history.startup_window = "search"
    save_history(tmp_path, history)

    assert load_history(tmp_path).startup_window == "search"


def test_a_profile_that_only_has_the_old_checkbox_is_migrated(tmp_path) -> None:
    import json

    from quill.core.radio.history import load_history

    (tmp_path / "radio_history.json").write_text(
        json.dumps({"open_browse_at_startup": True}), encoding="utf-8"
    )

    assert load_history(tmp_path).startup_window == "browse"


def test_a_profile_with_neither_opens_nothing(tmp_path) -> None:
    import json

    from quill.core.radio.history import load_history

    (tmp_path / "radio_history.json").write_text(json.dumps({}), encoding="utf-8")

    assert load_history(tmp_path).startup_window == startup.NONE


# -- the app half ------------------------------------------------------------------


class _App:
    """Stands in for the Radio frame: every opener is a command it already has."""

    def __init__(self, chosen: str) -> None:
        self._radio_history = type("H", (), {"startup_window": chosen})()
        self.opened: list[str] = []

    def open_browse_stations(self) -> None:
        self.opened.append("browse")

    def open_internet_radio(self) -> None:
        self.opened.append("search")

    def open_manage_radio_favorites(self) -> None:
        self.opened.append("favorites")

    def open_radio_recordings(self) -> None:
        self.opened.append("recordings")

    def _radio_go_to_player(self) -> None:
        self.opened.append("player")


def test_exactly_one_window_opens_and_the_rest_stay_closed() -> None:
    """Favorites *and* Browse both appearing was the report."""
    from quill.apps.radio_startup_window import open_startup_window

    app = _App("browse")

    assert open_startup_window(app) == "browse"
    assert app.opened == ["browse"]


def test_none_opens_nothing_at_all() -> None:
    from quill.apps.radio_startup_window import open_startup_window

    app = _App(startup.NONE)

    assert open_startup_window(app) == ""
    assert app.opened == []


def test_a_window_that_fails_to_open_never_breaks_the_launch() -> None:
    from quill.apps.radio_startup_window import open_startup_window

    class _Broken(_App):
        def open_browse_stations(self) -> None:
            raise RuntimeError("no window today")

    app = _Broken("browse")

    assert open_startup_window(app) == ""
    assert app.opened == []


def test_every_choice_names_a_command_the_app_really_has() -> None:
    """A choice that opens nothing because the method was renamed is a dead row."""
    from quill.apps.radio_startup_window import OPENERS

    offered = {wid for wid, _label in startup.STARTUP_WINDOWS if wid}

    assert set(OPENERS) == offered
    app = _App("browse")
    for method in OPENERS.values():
        assert callable(getattr(app, method, None)), method
