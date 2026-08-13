"""Player Information counts this episode's notes (x.md item 11).

A regression test for a silent one: ``notes_for_episode`` *filters* a loaded
list, it does not load one, and the call site passed only two of its three
arguments. The resulting ``TypeError`` was swallowed by a broad ``except``, so
the report confidently said "0 notes" for an episode with fifty -- a fabricated
measurement, which is exactly what the A-10 rule forbids.

The mixin method is exercised against a stub host rather than a real
``MainFrame``: the thing under test is what it reads and reports, and building
a whole frame to learn that would test wx instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts.episode_notes import add_episode_note
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.main_frame_podcasts import PodcastsMixin


class _State:
    def __init__(self, show_id: str, episode_guid: str) -> None:
        self.show_id = show_id
        self.episode_guid = episode_guid
        self.title = "Episode One"


class _Controller:
    def __init__(self, state: _State) -> None:
        self.state = state
        self.rate = 1.0

    def position_ms(self) -> int:
        return 12_000

    def length_ms(self) -> int:
        return 600_000


class _Host:
    """The slice of MainFrame that _podcast_player_info actually reads."""

    _podcast_player_info = PodcastsMixin._podcast_player_info

    def __init__(self, library: PodcastLibrary, state: _State) -> None:
        self._podcast_library = library
        self._podcast_controller = _Controller(state)
        self._podcast_current_chapters: list[object] = []
        self._podcast_chapters_source = ""


@pytest.fixture
def isolated_notes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    return tmp_path


def _library() -> tuple[PodcastLibrary, PodcastShow, PodcastEpisode]:
    episode = PodcastEpisode(
        guid="ep-1",
        title="Episode One",
        audio_url="https://example.com/ep1.mp3",
        published="2026-07-01T00:00:00",
    )
    show = PodcastShow(
        id="show-1",
        title="The Daily",
        feed_url="https://example.com/feed.xml",
        episodes=[episode],
    )
    library = PodcastLibrary(shows=[show])
    return library, show, episode


def test_the_report_counts_the_notes_that_exist(isolated_notes: Path) -> None:
    """The bug: this was always 0, whatever the listener had written."""
    library, show, episode = _library()
    add_episode_note(show.id, episode.guid, 10_000, "first")
    add_episode_note(show.id, episode.guid, 20_000, "second")
    add_episode_note(show.id, episode.guid, 30_000, "third")

    info = _Host(library, _State(show.id, episode.guid))._podcast_player_info()

    assert info.note_count == 3


def test_notes_on_a_different_episode_are_not_counted(isolated_notes: Path) -> None:
    library, show, episode = _library()
    add_episode_note(show.id, episode.guid, 10_000, "mine")
    add_episode_note(show.id, "some-other-episode", 10_000, "not mine")

    info = _Host(library, _State(show.id, episode.guid))._podcast_player_info()

    assert info.note_count == 1


def test_an_episode_with_no_notes_reports_zero(isolated_notes: Path) -> None:
    """Still zero when zero is the truth -- the fix must not invent notes."""
    library, show, episode = _library()

    info = _Host(library, _State(show.id, episode.guid))._podcast_player_info()

    assert info.note_count == 0


def test_nothing_playing_still_produces_a_report(isolated_notes: Path) -> None:
    library, _show, _episode = _library()

    info = _Host(library, _State("", ""))._podcast_player_info()

    assert info.note_count == 0
    assert info.collection == ""
