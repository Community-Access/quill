"""The Bookmarks window, and the jump it cannot do on its own (4.4).

Going to a bookmark means something different in each app -- tune in, seek a
recording, open an episode -- so the window holds a registry keyed by anchor
kind rather than a stored callback. Registering by kind is what lets a row
survive a restart and still know how to be opened; a closure would not.

The important consequence, and the reason it is a registry rather than a hidden
filter: **a row this app cannot open still appears.** A station bookmarked in
Quill Radio is in QUILL Cast's list, with Go There dimmed and a reason. Hiding
it would leave somebody wondering where their bookmark went, which is worse
than a button that says why it is off.
"""

from __future__ import annotations

import pytest

from quill.core import bookmark_anchors
from quill.core.media.bookmarks import BookmarkStore, MediaBookmark

wx = pytest.importorskip("wx")

from quill.ui import bookmarks_dialog  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_registry():
    bookmarks_dialog.clear_jumps()
    yield
    bookmarks_dialog.clear_jumps()


@pytest.fixture
def store(tmp_path) -> BookmarkStore:
    return BookmarkStore(tmp_path / "media_bookmarks.json")


def _mark(position_ms: int = 1000, **kwargs) -> MediaBookmark:
    return MediaBookmark(position_ms=position_ms, **kwargs)


# -- the registry ----------------------------------------------------------------


def test_nothing_can_be_jumped_to_until_an_app_says_so() -> None:
    assert bookmarks_dialog.can_jump("station:https://s") is False


def test_an_app_claims_the_kinds_it_can_play() -> None:
    bookmarks_dialog.register_jump(bookmark_anchors.STATION, lambda _a, _m: "Tuned in.")

    assert bookmarks_dialog.can_jump("station:https://s") is True
    assert bookmarks_dialog.can_jump("podcast:a|b") is False


def test_a_row_this_app_cannot_open_says_which_kind_it_is() -> None:
    """Dimmed with a reason. Hiding the row would leave somebody wondering
    where their bookmark went."""
    said = bookmarks_dialog.jump("station:https://s", _mark())

    assert "cannot open a station" in said


def test_registering_twice_replaces_rather_than_stacking() -> None:
    """An app that rebuilds its frame must not end up with two handlers."""
    bookmarks_dialog.register_jump(bookmark_anchors.STATION, lambda _a, _m: "first")
    bookmarks_dialog.register_jump(bookmark_anchors.STATION, lambda _a, _m: "second")

    assert bookmarks_dialog.jump("station:https://s", _mark()) == "second"


def test_a_handler_that_says_nothing_still_gets_an_answer() -> None:
    bookmarks_dialog.register_jump(bookmark_anchors.STATION, lambda _a, _m: "")

    assert "1 second" in bookmarks_dialog.jump("station:https://s", _mark())


def test_a_handler_that_raises_is_reported_not_propagated() -> None:
    """A jump that failed must say so; a window that dies on a click must not."""

    def _boom(_anchor, _mark):
        raise RuntimeError("the stream is gone")

    bookmarks_dialog.register_jump(bookmark_anchors.STATION, _boom)

    said = bookmarks_dialog.jump("station:https://s", _mark())

    assert "Could not go there" in said
    assert "the stream is gone" in said


def test_the_handler_is_given_both_the_anchor_and_the_bookmark() -> None:
    seen: list[tuple[str, MediaBookmark]] = []
    bookmarks_dialog.register_jump(
        bookmark_anchors.PODCAST, lambda anchor, mark: seen.append((anchor, mark)) or "ok"
    )
    mark = _mark(42_000, note="here")

    bookmarks_dialog.jump("podcast:the-daily|ep-412", mark)

    assert seen == [("podcast:the-daily|ep-412", mark)]


# -- what each app claims --------------------------------------------------------


def test_quill_radio_claims_everything_it_can_play() -> None:
    from quill.ui.radio import bookmarks_wiring

    host = type("_Host", (), {"_register_bookmark_jumps": _capture, "_bookmark_target": None})()
    host.claimed = {}
    bookmarks_wiring.register(host)

    assert set(host.claimed) == {
        bookmark_anchors.STATION,
        bookmark_anchors.RECORDING,
        bookmark_anchors.VIDEO,
        bookmark_anchors.PODCAST,
    }


def test_quill_cast_claims_only_podcasts_and_says_so_about_the_rest() -> None:
    from quill.ui.podcasts import bookmarks_wiring

    host = type("_Host", (), {"_register_bookmark_jumps": _capture, "_bookmark_target": None})()
    host.claimed = {}
    bookmarks_wiring.register(host)

    assert set(host.claimed) == {bookmark_anchors.PODCAST}


def test_registering_also_teaches_the_app_what_it_is_playing() -> None:
    """Two halves of one fact; splitting them is how one gets forgotten."""
    from quill.ui.radio import bookmarks_wiring

    host = type("_Host", (), {"_register_bookmark_jumps": _capture})()
    host.claimed = {}
    bookmarks_wiring.register(host)

    assert callable(host._bookmark_target)
    assert host._bookmark_target() == ("", 0, "")


def _capture(self, kinds):  # noqa: ANN001 - a stand-in for the mixin method
    self.claimed = dict(kinds)


# -- Radio's anchoring -----------------------------------------------------------


def test_radio_anchors_a_live_station_as_a_station() -> None:
    from quill.ui.radio import bookmarks_wiring

    anchor, position, title = bookmarks_wiring.target_for(_radio_host(_station()))

    assert anchor == "station:https://s/live"
    assert position == 90_000
    assert title == "Main Menu"


def test_radio_anchors_a_recording_by_its_file() -> None:
    from quill.ui.radio import bookmarks_wiring

    station = _station(url="C:/rec/show.mp3", source="Recordings")
    anchor, _position, _title = bookmarks_wiring.target_for(_radio_host(station))

    assert bookmark_anchors.kind_of(anchor) == bookmark_anchors.RECORDING


def test_radio_anchors_a_youtube_row_as_a_video() -> None:
    from quill.ui.radio import bookmarks_wiring

    station = _station(url="https://youtu.be/abc", source="YouTube")
    anchor, _position, _title = bookmarks_wiring.target_for(_radio_host(station))

    assert bookmark_anchors.kind_of(anchor) == bookmark_anchors.VIDEO


def test_radio_with_nothing_playing_anchors_nothing() -> None:
    from quill.ui.radio import bookmarks_wiring

    assert bookmarks_wiring.target_for(_radio_host(None)) == ("", 0, "")


def test_a_position_that_raises_is_zero_rather_than_an_exception() -> None:
    """A position is never worth taking a keystroke down for."""
    from quill.ui.radio import bookmarks_wiring

    class _Controller:
        state = type("_S", (), {"station": _station()})()

        def position_ms(self):
            raise RuntimeError("the engine is between states")

    host = type("_Host", (), {"_radio_controller": _Controller()})()
    _anchor, position, _title = bookmarks_wiring.target_for(host)

    assert position == 0


def _station(url: str = "https://s/live", source: str = "Popular Stations"):
    return type(
        "_Station",
        (),
        {
            "stream_url": url,
            "name": "Main Menu",
            "source": source,
            "show_id": "",
            "episode_guid": "",
        },
    )()


def _radio_host(station):
    class _Controller:
        state = type("_S", (), {"station": station})()

        def position_ms(self) -> int:
            return 90_000

    return type("_Host", (), {"_radio_controller": _Controller()})()
