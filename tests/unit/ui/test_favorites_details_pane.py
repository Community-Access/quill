"""The note, read back where people keep their favorites.

3.1.0 shipped notes on stations and a details pane that could show them --
in the browse tree only. Manage Favorites, which is where a listener with
sixty saved stations actually works, had no pane at all, so a note written on
a favorite was never seen again from that window.

Two properties matter beyond "it appears":

* **The note goes last.** The details are what the app knows and the note is
  what you told yourself; somebody arrowing a list wants the identification
  first and their own words after. Same order as the browse tree, which is the
  other place the same note is read.
* **It is labelled.** An unlabelled paragraph appended to a station's own
  blurb reads as more of the station's blurb.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.radio.favorites import FavoriteStation
from quill.core.radio.item_notes import set_note
from quill.core.radio.models import RadioStation
from quill.ui.radio import favorites_details


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    return tmp_path


def _favorite(**kwargs: object) -> FavoriteStation:
    station = RadioStation(
        name="Radio Paradise",
        stream_url="https://stream.example/rp",
        country="United States",
        **kwargs,  # type: ignore[arg-type]
    )
    return FavoriteStation(station=station)


def test_a_favorite_with_no_note_is_just_its_details(data_dir: Path) -> None:
    favorite = _favorite()
    assert favorites_details.describe(favorite) == favorite.station.details_text
    assert "Your note" not in favorites_details.describe(favorite)


def test_the_note_comes_after_the_details_and_says_it_is_yours(data_dir: Path) -> None:
    favorite = _favorite()
    set_note(data_dir, favorite.station, "Only worth it on Sundays")
    text = favorites_details.describe(favorite)
    assert text.startswith(favorite.station.details_text)
    assert text.endswith("Your note: Only worth it on Sundays")


def test_the_same_note_the_browse_tree_reads(data_dir: Path) -> None:
    """One note per station, not one per window -- keyed by stream URL, so the
    two surfaces cannot drift apart."""
    from quill.ui.radio import browse_details

    favorite = _favorite()
    set_note(data_dir, favorite.station, "The morning show is the good one")
    assert favorites_details.describe(favorite) == browse_details._with_note(
        favorite.station, favorite.station.details_text
    )


def test_nothing_selected_clears_the_pane_rather_than_leaving_the_last_row(
    data_dir: Path,
) -> None:
    assert favorites_details.describe(None) == ""


def test_a_folder_row_gets_a_line_rather_than_an_empty_box() -> None:
    """An empty pane beside a highlighted row reads as a window that failed to
    load; a short true sentence reads as one with nothing more to say."""

    class _Store:
        favorites = [
            FavoriteStation(station=RadioStation(name="A", stream_url="a"), folder="News"),
            FavoriteStation(station=RadioStation(name="B", stream_url="b"), folder="News"),
            FavoriteStation(station=RadioStation(name="C", stream_url="c"), folder="Jazz"),
        ]

    assert favorites_details.describe_folder(_Store(), "News") == "Folder: News\n2 stations."
    assert favorites_details.describe_folder(_Store(), "Jazz") == "Folder: Jazz\n1 station."
    assert favorites_details.describe_folder(_Store(), "") == ""


def test_a_broken_store_costs_the_count_not_the_selection() -> None:
    class _Broken:
        @property
        def favorites(self) -> list[object]:
            raise RuntimeError("store is mid-reload")

    assert favorites_details.describe_folder(_Broken(), "News").startswith("Folder: News")


# -- the pane, driven the way the dialog drives it ----------------------------


class _Pane:
    def __init__(self) -> None:
        self.text = "stale"

    def ChangeValue(self, value: str) -> None:  # noqa: N802 - wx's spelling
        self.text = value


class _Dialog:
    def __init__(self, selected: object, favorite: object = None, store: object = None) -> None:
        self._details = _Pane()
        self._selection = selected
        self._favorite = favorite
        self._store = store

    def _selected(self) -> object:
        return self._selection

    def _selected_favorite(self) -> object:
        return self._favorite


def test_refresh_reads_the_station_under_the_cursor(data_dir: Path) -> None:
    favorite = _favorite()
    set_note(data_dir, favorite.station, "Ask about the 3am repeat")
    dialog = _Dialog(("station", "key"), favorite)
    favorites_details.refresh(dialog)
    assert "Ask about the 3am repeat" in dialog._details.text


def test_refresh_never_takes_the_selection_down_with_it() -> None:
    class _Exploding(_Dialog):
        def _selected(self) -> object:
            raise RuntimeError("tree is rebuilding")

    dialog = _Exploding(None)
    favorites_details.refresh(dialog)  # must not raise
    assert dialog._details.text == ""


def test_a_window_built_before_the_pane_existed_is_simply_skipped() -> None:
    class _NoPane:
        pass

    favorites_details.refresh(_NoPane())  # must not raise
