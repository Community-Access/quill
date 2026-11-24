"""FUX-14 in the media apps: a structural move says where it landed, once.

Radio, Cast, Player and Studio (through the shared PlayerPanel) each move by
chapter, and the Player now by bookmark too. Every test here failed before the
2026-11-23 change it names.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.apps.player_bookmarks import PlayerBookmarksMixin
from quill.core.media.bookmarks import MediaBookmark
from quill.core.podcasts.chapters import PodcastChapter, previous_chapter
from quill.core.structure_landing import describe_boundary, describe_landing
from quill.ui.audio_studio.player_panel import PlayerPanel
from quill.ui.main_frame_podcasts import PodcastsMixin
from quill.ui.media.winamp_mixin import MediaWinampKeysMixin
from quill.ui.radio import bounded_playback_ui as radio_ui

# -- the shared sentence -------------------------------------------------------


def test_a_landing_names_the_thing_its_kind_and_its_place() -> None:
    assert describe_landing("chapter", "Intro", 0, 12) == "Intro, chapter 1 of 12."


def test_a_worked_out_structure_says_estimated() -> None:
    said = describe_landing("chapter", "Weather", 2, 5, estimated=True)
    assert said == "Weather, chapter 3 of 5, estimated."


def test_an_untitled_structure_still_reads_and_detail_comes_last() -> None:
    assert describe_landing("bookmark", "  ", 1, 2, detail="3 minutes") == (
        "Untitled bookmark, bookmark 2 of 2, 3 minutes."
    )
    assert describe_boundary("bookmark", forward=False) == "This is the first bookmark."


# -- Quill Radio ---------------------------------------------------------------


class _RadioController:
    def __init__(self, chapters: list[Any], current: int, position: int = 0) -> None:
        self._chapters = chapters
        self.current = current
        self.position = position
        self.jumped: list[int] = []
        self.seeks: list[int] = []
        self.state = SimpleNamespace(station="a station")

    def is_seekable(self) -> bool:
        return True

    def chapters(self) -> list[Any]:
        return list(self._chapters)

    def current_chapter_index(self) -> int:
        return self.current

    def go_to_adjacent_chapter(self, delta: int) -> int:
        self.current = max(0, min(self.current + delta, len(self._chapters) - 1))
        self.jumped.append(self.current)
        return self.current

    def position_ms(self) -> int:
        return self.position

    def seek_to(self, ms: int) -> bool:
        self.seeks.append(ms)
        return True


class _RadioHost:
    def __init__(self, controller: _RadioController) -> None:
        self._radio_controller = controller
        self.said: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_radio_next_chapter_in_the_last_chapter_says_so_and_stays() -> None:
    """It used to seek back to the start of the chapter you were in."""
    chapters = [PodcastChapter(0, "Intro"), PodcastChapter(60_000, "Outro")]
    controller = _RadioController(chapters, current=1)
    host = _RadioHost(controller)
    radio_ui.next_chapter(host)
    assert controller.jumped == []
    assert host.said == [radio_ui.LAST_CHAPTER]


def test_radio_chapter_keys_reach_the_chapters_the_list_finds(monkeypatch) -> None:
    """The Chapters list read the file's marks and Cast's cache; the keys did not."""
    found = [
        PodcastChapter(0, "Cold open"),
        PodcastChapter(90_000, "The news", source="transcript"),
    ]
    monkeypatch.setattr(radio_ui, "_found_chapters", lambda _c: (found, "cache"))
    controller = _RadioController([], current=-1, position=10_000)
    host = _RadioHost(controller)
    radio_ui.next_chapter(host)
    assert controller.seeks == [90_000]
    assert host.said == ["The news, chapter 2 of 2, estimated."]
    controller.position = 200_000
    radio_ui.next_chapter(host)
    assert host.said[-1] == radio_ui.LAST_CHAPTER


def test_radio_no_chapters_is_not_called_a_video() -> None:
    assert "video" not in radio_ui.NO_CHAPTERS


# -- Quill Cast ----------------------------------------------------------------


def test_cast_previous_chapter_restarts_the_one_you_are_well_inside() -> None:
    chapters = [PodcastChapter(0, "One"), PodcastChapter(60_000, "Two")]
    assert previous_chapter(chapters, 20 * 60_000, restart_ms=3000) is chapters[1]
    assert previous_chapter(chapters, 61_000, restart_ms=3000) is chapters[0]
    assert previous_chapter(chapters, 30_000, restart_ms=3000) is chapters[0]
    assert previous_chapter(chapters, 30_000) is None  # the old contract, unchanged


class _CastController:
    def __init__(self, position: int) -> None:
        self.position = position
        self.seeks: list[int] = []

    def position_ms(self) -> int:
        return self.position

    def seek(self, ms: int) -> None:
        self.seeks.append(ms)


class _CastHost(PodcastsMixin):
    def __init__(self, chapters: list[PodcastChapter], position: int) -> None:
        self._podcast_current_chapters = chapters
        self._podcast_controller = _CastController(position)
        self.said: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_cast_chapter_moves_say_their_place_and_whether_they_were_worked_out() -> None:
    chapters = [
        PodcastChapter(0, "Intro"),
        PodcastChapter(60_000, "Topic", source="silence scan"),
        PodcastChapter(120_000, "Credits"),
    ]
    host = _CastHost(chapters, position=1_000)
    host.podcast_next_chapter()
    assert host.said == ["Topic, chapter 2 of 3, estimated."]
    host._podcast_controller.position = 20 * 60_000
    host.podcast_previous_chapter()
    assert host._podcast_controller.seeks[-1] == 120_000
    assert host.said[-1] == "Credits, chapter 3 of 3."
    host._podcast_controller.position = 1_000
    host.podcast_previous_chapter()
    assert host.said[-1] == "This is the first chapter."


# -- Quill Player and Studio's shared PlayerPanel ------------------------------


class _Engine:
    def __init__(self) -> None:
        self.seeks: list[int] = []

    def seek(self, ms: int, resume: bool = True) -> None:  # noqa: ARG002
        self.seeks.append(ms)


def _panel(chapters: list[Any], announced: int) -> SimpleNamespace:
    said: list[str] = []
    panel = SimpleNamespace(
        _chapters=chapters,
        _announced_chapter=announced,
        _engine=_Engine(),
        _loaded=True,
        _announce=said.append,
        _sync_play_label=lambda: None,
        _timer=SimpleNamespace(Start=lambda _ms: None),
        said=said,
    )
    panel._announce_chapter = lambda index, asked=False: PlayerPanel._announce_chapter(
        panel, index, asked=asked
    )
    return panel


def _chapter(title: str, start: int, end: int) -> SimpleNamespace:
    return SimpleNamespace(title=title, start_ms=start, end_ms=end, duration_ms=end - start)


def test_panel_previous_that_restarts_the_chapter_still_says_it() -> None:
    """The playback latch swallowed it: Previous restarted in silence."""
    panel = _panel([_chapter("One", 0, 60_000), _chapter("Two", 60_000, 90_000)], announced=1)
    PlayerPanel.play_chapter(panel, 1)
    assert panel.said == ["Two, chapter 2 of 2, 30 seconds long."]


def test_panel_previous_in_the_first_seconds_of_chapter_one_says_so() -> None:
    panel = _panel([_chapter("One", 0, 60_000)], announced=0)
    panel.playhead_ms = lambda: 1_000
    panel._chapter_at = lambda ms: PlayerPanel._chapter_at(panel, ms)
    PlayerPanel.previous_chapter(panel)
    assert panel._engine.seeks == []
    assert panel.said == ["This is the first chapter."]


def test_radio_previous_in_the_first_seconds_of_chapter_one_says_so() -> None:
    chapters = [PodcastChapter(0, "Intro"), PodcastChapter(60_000, "Outro")]
    controller = _RadioController(chapters, current=0, position=1_000)
    host = _RadioHost(controller)
    radio_ui.previous_chapter(host)
    assert controller.jumped == []
    assert host.said == [radio_ui.FIRST_CHAPTER]


def test_panel_playback_crossing_is_said_once() -> None:
    panel = _panel([_chapter("One", 0, 60_000)], announced=-1)
    PlayerPanel._announce_chapter(panel, 0)
    PlayerPanel._announce_chapter(panel, 0)
    assert len(panel.said) == 1


def test_panel_seek_can_leave_the_saying_to_its_caller() -> None:
    panel = _panel([], announced=-1)
    PlayerPanel.seek_to(panel, 5_000, announce=False)
    assert panel._engine.seeks == [5_000]
    assert panel.said == []


class _WinampPlayer:
    def __init__(self, said: list[str]) -> None:
        self.position = 100_000
        self._said = said

    def has_media(self) -> bool:
        return True

    def length_ms(self) -> int:
        return 600_000

    def playhead_ms(self) -> int:
        return self.position

    def seek_to(self, ms: int, *, announce: bool = True) -> None:
        self.position = ms
        if announce:
            self._said.append("timestamp")


class _WinampHost(MediaWinampKeysMixin):
    def __init__(self) -> None:
        self.said: list[str] = []
        self._player = _WinampPlayer(self.said)
        self._winamp_show_remaining = False

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_player_arrow_seek_is_spoken_once() -> None:
    host = _WinampHost()
    host._winamp_seek(5_000)
    assert len(host.said) == 1 and host.said[0] != "timestamp"


class _BookmarkList:
    def __init__(self) -> None:
        self.selection = -1
        self.focused = False

    def GetSelection(self) -> int:  # noqa: N802 - wx's name
        return self.selection

    def SetSelection(self, index: int) -> None:  # noqa: N802 - wx's name
        self.selection = index

    def HasFocus(self) -> bool:  # noqa: N802 - wx's name
        return self.focused


class _Store:
    def __init__(self, marks: list[MediaBookmark]) -> None:
        self._marks = marks

    def list(self, _key: str) -> list[MediaBookmark]:
        return sorted(self._marks, key=lambda m: m.position_ms)


class _PlayerHost(PlayerBookmarksMixin):
    def __init__(self, marks: list[MediaBookmark], position: int) -> None:
        self.said: list[str] = []
        self.seeks: list[tuple[int, bool]] = []
        self._book_key = "book"
        self._bookmarks = _Store(marks)
        self._bookmarks_list = _BookmarkList()
        self._player = SimpleNamespace(
            playhead_ms=lambda: self.position,
            seek_to=lambda ms, announce=True: self._seek(ms, announce),
        )
        self.position = position

    def _seek(self, ms: int, announce: bool) -> None:
        self.seeks.append((ms, announce))
        self.position = ms

    def _announce(self, message: str) -> None:
        self.said.append(message)


def _marks() -> list[MediaBookmark]:
    return [
        MediaBookmark(position_ms=60_000, note="The storm starts"),
        MediaBookmark(position_ms=300_000),
    ]


def test_player_next_bookmark_lands_and_says_note_place_and_time() -> None:
    host = _PlayerHost(_marks(), position=0)
    host._step_bookmark(1)
    assert host.seeks == [(60_000, False)]
    assert host.said == ["The storm starts, bookmark 1 of 2, 1 minute."]
    host._step_bookmark(1)  # standing on the first: Next moves on
    assert host.seeks[-1] == (300_000, False)
    assert host.said[-1] == "5 minutes, bookmark 2 of 2."
    host._step_bookmark(1)
    assert host.said[-1] == "This is the last bookmark."


def test_player_previous_bookmark_and_the_first_boundary() -> None:
    host = _PlayerHost(_marks(), position=400_000)
    host._step_bookmark(-1)
    assert host.seeks == [(300_000, False)]
    host._step_bookmark(-1)
    host._step_bookmark(-1)
    assert host.said[-1] == "This is the first bookmark."


def test_player_bookmark_step_in_a_focused_list_leaves_the_row_to_the_reader() -> None:
    host = _PlayerHost(_marks(), position=0)
    host._bookmarks_list.focused = True
    host._step_bookmark(1)
    assert host._bookmarks_list.selection == 0
    assert host.said == []


def test_player_bookmark_step_with_nothing_to_step_through_says_why() -> None:
    host = _PlayerHost([], position=0)
    host._step_bookmark(1)
    assert host.said == ["This book has no bookmarks."]
