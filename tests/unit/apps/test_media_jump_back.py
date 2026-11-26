"""Back to Where I Was, and the right saved place, in Cast and Media Player (FUX-01).

A jump in either player used to be one-way: Go to Position, Next or Previous
Chapter, or a chapter chosen from a list moved the time and kept nothing of
where you were. The rule is :mod:`quill.core.media.jump_back`; these drive
each app's real functions and methods over duck-typed hosts, because what is
under test is which time is kept and where the player lands, not a window.

Media Player also saved a book's place under the wrong file and kept a place in
the closing credits of a finished one, and never resumed a DAISY book at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from quill.apps.player import QuillMediaPlayerFrame
from quill.apps.player_jumps import PlayerJumpsMixin
from quill.core.media.jump_back import NOTHING_TO_GO_BACK_TO, JumpBack
from quill.core.media.positions import PositionStore
from quill.core.podcasts.chapters import PodcastChapter
from quill.ui.podcasts.chapter_moves import step_chapter
from quill.ui.podcasts.jump_back_wiring import back_to_where_i_was

MINUTE = 60_000

# --------------------------------------------------------------------------- #
# The rule
# --------------------------------------------------------------------------- #


def test_back_returns_and_back_again_comes_home() -> None:
    jumps = JumpBack()
    jumps.before_jump("ep", 5 * MINUTE, 40 * MINUTE)

    assert jumps.back("ep", 41 * MINUTE) == 5 * MINUTE
    assert jumps.back("ep", 5 * MINUTE) == 41 * MINUTE


def test_a_place_belongs_to_its_recording() -> None:
    jumps = JumpBack()
    jumps.before_jump("ep-1", 5 * MINUTE, 40 * MINUTE)
    assert jumps.back("ep-2", MINUTE) is None


def test_a_nudge_is_not_a_jump() -> None:
    """A second or two is the skip keys' business; it must not replace the real place."""
    jumps = JumpBack()
    jumps.before_jump("ep", 5 * MINUTE, 40 * MINUTE)
    jumps.before_jump("ep", 40 * MINUTE, 40 * MINUTE + 500)
    assert jumps.back("ep", 40 * MINUTE) == 5 * MINUTE


# --------------------------------------------------------------------------- #
# QUILL Cast
# --------------------------------------------------------------------------- #


class _CastController:
    def __init__(self) -> None:
        self.state = SimpleNamespace(
            show_id="show", episode_guid="guid-1", state=SimpleNamespace(name="PLAYING")
        )
        self.position = 0

    def position_ms(self) -> int:
        return self.position

    def seek(self, ms: int) -> None:
        self.position = int(ms)


class _CastHost:
    def __init__(self) -> None:
        self._podcast_controller = _CastController()
        self._podcast_current_chapters = [
            PodcastChapter(title="Intro", start_ms=0),
            PodcastChapter(title="Interview", start_ms=10 * MINUTE),
            PodcastChapter(title="Listener mail", start_ms=30 * MINUTE),
        ]
        self.said: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_cast_goes_back_after_a_chapter_jump() -> None:
    host = _CastHost()
    host._podcast_controller.position = 2 * MINUTE + 5000

    step_chapter(host, 1)
    assert host._podcast_controller.position == 10 * MINUTE
    back_to_where_i_was(host)

    assert host._podcast_controller.position == 2 * MINUTE + 5000
    assert host.said[-1] == "Back to 2 minutes 5 seconds."
    back_to_where_i_was(host)  # and there again
    assert host._podcast_controller.position == 10 * MINUTE


def test_cast_says_when_there_is_nowhere_to_go_back_to() -> None:
    host = _CastHost()
    back_to_where_i_was(host)
    assert host.said == [NOTHING_TO_GO_BACK_TO]


def test_cast_forgets_the_place_when_another_episode_plays() -> None:
    host = _CastHost()
    host._podcast_controller.position = 3 * MINUTE
    step_chapter(host, 1)
    host._podcast_controller.state.episode_guid = "guid-2"

    back_to_where_i_was(host)

    assert host.said[-1] == NOTHING_TO_GO_BACK_TO


def test_cast_go_to_position_notes_the_place(monkeypatch) -> None:
    import wx

    from quill.ui.podcasts import go_to_position as module

    class _Dialog:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def get_target_ms(self) -> int:
            return 45 * MINUTE

        def clamped_message(self) -> str:
            return ""

        def Destroy(self) -> None:  # noqa: N802 - wx API shape
            pass

    monkeypatch.setattr("quill.ui.media.go_to_position_dialog.GoToPositionDialog", _Dialog)
    monkeypatch.setattr("quill.ui.dialog_contract.show_modal_dialog", lambda *_a, **_k: wx.ID_OK)
    host = _CastHost()
    host.frame = None
    host._podcast_controller.length_ms = lambda: 60 * MINUTE
    host._podcast_controller.position = 7 * MINUTE

    module.go_to_position(host)
    back_to_where_i_was(host)

    assert host._podcast_controller.position == 7 * MINUTE


# --------------------------------------------------------------------------- #
# Media Player
# --------------------------------------------------------------------------- #


class _Panel:
    def __init__(self, length: int = 60 * MINUTE) -> None:
        self.position = 0
        self.length = length
        self.loads: list[tuple[str, int]] = []

    def playhead_ms(self) -> int:
        return self.position

    def length_ms(self) -> int:
        return self.length

    def seek_to(self, ms: int, *, announce: bool = True) -> None:
        self.position = int(ms)

    def load(self, path: str, chapters: list, *, resume_ms: int = 0, autoplay: bool = False):
        self.loads.append((path, resume_ms))
        self.position = resume_ms
        return True


@dataclass
class _Item:
    payload: tuple

    def IsOk(self) -> bool:  # noqa: N802 - wx API shape
        return True


class _Tree:
    def GetItemData(self, item: _Item) -> tuple:  # noqa: N802 - wx API shape
        return item.payload

    def GetItemText(self, _item: _Item) -> str:  # noqa: N802 - wx API shape
        return "Part"


class _Player(PlayerJumpsMixin):
    def __init__(self, book: Path | None) -> None:
        self._book_key = str(book) if book else None
        self._book_path = book
        self._player = _Panel()
        self._chapter_tree = _Tree()
        self._playlist: list = []
        self.said: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _set_status(self, _text: str) -> None:
        pass

    _play_payload = QuillMediaPlayerFrame._play_payload
    _play_track_node = QuillMediaPlayerFrame._play_track_node


def test_player_goes_back_after_a_chapter_chosen_in_the_tree(tmp_path: Path) -> None:
    player = _Player(tmp_path / "book.m4b")
    player._player.position = 12 * MINUTE
    event = SimpleNamespace(GetItem=lambda: _Item(("seek", 50 * MINUTE)))

    player._on_chapter_activate(event)
    player._on_back_to_where_i_was()

    assert player._player.position == 12 * MINUTE
    assert player.said[-1] == "Back to 12 minutes."


def test_player_with_nothing_open_says_so() -> None:
    player = _Player(None)
    player._on_back_to_where_i_was()
    assert player.said == ["Open a file first."]


def _media(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(name.encode() * 4000)
    return path


def test_each_file_of_a_book_keeps_its_own_place(quill_data_dir: Path, tmp_path: Path) -> None:
    """Track four's time used to be saved under track one's name."""
    first, fourth = _media(tmp_path, "01.mp3"), _media(tmp_path, "04.mp3")
    player = _Player(first)
    player._player.position = 3 * MINUTE

    player._play_payload(("load", str(fourth)), "Part 4", autoplay=True)
    player._player.position = 9 * MINUTE
    player._save_resume()

    store = PositionStore(quill_data_dir)
    assert store.position_for(first) == 3 * MINUTE
    assert store.position_for(fourth) == 9 * MINUTE


def test_a_finished_file_starts_again_from_the_beginning(
    quill_data_dir: Path, tmp_path: Path
) -> None:
    book = _media(tmp_path, "book.mp3")
    player = _Player(book)
    player._player.position = 30 * MINUTE
    player._save_resume()
    assert PositionStore(quill_data_dir).position_for(book) == 30 * MINUTE

    player._player.position = 60 * MINUTE - 5000  # the closing credits
    player._save_resume()

    assert PositionStore(quill_data_dir).position_for(book) == 0


def test_a_daisy_book_resumes(quill_data_dir: Path, tmp_path: Path, monkeypatch) -> None:
    audio = _media(tmp_path, "daisy.mp3")
    ncx = tmp_path / "navigation.ncx"
    ncx.write_text("<ncx/>", encoding="utf-8")
    PositionStore(quill_data_dir).remember(audio, 14 * MINUTE)
    monkeypatch.setattr("quill.core.media.parse_ncx", lambda _text: [])
    monkeypatch.setattr("quill.core.media.resolve_heading_times", lambda headings, _load: [])

    player = _Player(None)
    player._daisy_build = lambda _resolved, _root: ([], [], audio)
    player._set_playlist_from_nodes = lambda: None
    player._now_playing = SimpleNamespace(SetValue=lambda _v: None)
    player._refresh_chapters = player._refresh_bookmarks = lambda: None
    player.frame = None
    monkeypatch.setattr("quill.apps.player.refresh_player_card", lambda *_a, **_k: None)

    QuillMediaPlayerFrame._load_daisy(player, ncx)

    assert player._player.loads == [(str(audio), 14 * MINUTE)]


def test_player_goes_back_across_files_of_a_book(quill_data_dir: Path, tmp_path: Path) -> None:
    """In a book of several files most chapters are in another file."""
    first, fourth = _media(tmp_path, "01.mp3"), _media(tmp_path, "04.mp3")
    player = _Player(first)
    player._player.position = 6 * MINUTE
    event = SimpleNamespace(GetItem=lambda: _Item(("track", (str(fourth), 0))))

    player._on_chapter_activate(event)
    assert player._book_path == fourth
    player._player.position = MINUTE
    player._on_back_to_where_i_was()

    assert player._book_path == first
    assert player._player.loads[-1] == (str(first), 6 * MINUTE)
    assert player.said[-1] == "Back to 6 minutes."
    player._on_back_to_where_i_was()  # and there again
    assert player._player.loads[-1] == (str(fourth), MINUTE)


def test_player_does_not_go_back_while_loading(tmp_path: Path) -> None:
    player = _Player(tmp_path / "book.m4b")
    player._player.position = 12 * MINUTE
    player._on_chapter_activate(SimpleNamespace(GetItem=lambda: _Item(("seek", 50 * MINUTE))))
    player._player.length = 0

    player._on_back_to_where_i_was()
    assert player.said == ["Still loading."]
    player._player.length = 60 * MINUTE
    player._on_back_to_where_i_was()  # the place was kept
    assert player._player.position == 12 * MINUTE


def test_cast_does_not_go_back_while_loading() -> None:
    host = _CastHost()
    host._podcast_controller.position = 2 * MINUTE
    step_chapter(host, 1)
    host._podcast_controller.state.state = SimpleNamespace(name="LOADING")

    back_to_where_i_was(host)

    assert host.said[-1] == "Still loading."
    assert host._podcast_controller.position == 10 * MINUTE


def test_now_playing_slider_leaves_alt_left_to_the_menu() -> None:
    """There, Alt+Left used to move back five seconds instead of going back."""
    import wx

    from quill.ui.podcasts.now_playing_window import NowPlayingWindow

    skipped: list[bool] = []
    event = SimpleNamespace(
        GetKeyCode=lambda: wx.WXK_LEFT,
        AltDown=lambda: True,
        ShiftDown=lambda: False,
        ControlDown=lambda: False,
        Skip=lambda: skipped.append(True),
    )
    window = SimpleNamespace(_controller=lambda: (_ for _ in ()).throw(AssertionError("moved")))

    NowPlayingWindow._on_slider_key(window, event)

    assert skipped == [True]


# --------------------------------------------------------------------------- #
# Studio: the Chapter Workbench keeps its place however it is left
# --------------------------------------------------------------------------- #


def test_the_workbench_keeps_its_place_when_left_with_close_or_escape(
    tmp_path: Path, monkeypatch
) -> None:
    """Close and Escape end the window with ID_CANCEL and no EVT_CLOSE.

    That close event was the only place the position was saved, the history
    told and the player stopped, so leaving with the Close button kept nothing.
    """
    from quill.ui.audio_studio import chapter_workbench as module

    book = SimpleNamespace(path=tmp_path / "book.m4b")
    saved: list[int] = []
    closed: list[tuple[str, int, int]] = []
    stopped: list[bool] = []

    class _Dialog:
        def __init__(self, *_a: Any, on_closed: Any = None, **_k: Any) -> None:
            self._book = book
            self._on_closed_cb = on_closed
            self.player = SimpleNamespace(
                playhead_ms=lambda: 25 * MINUTE,
                current_chapter_index=lambda: 3,
                shutdown=lambda: stopped.append(True),
            )

        keep_place_and_stop = module.ChapterWorkbenchDialog.keep_place_and_stop

        def _cancel_silence_scan(self, *, spoken: bool) -> None:
            pass

        def Destroy(self) -> None:  # noqa: N802 - wx API shape
            pass

    monkeypatch.setattr(module, "ChapterWorkbenchDialog", _Dialog)
    monkeypatch.setattr(module, "bind_host_shortcuts", lambda *_a: None)
    monkeypatch.setattr("quill.core.speech.book_file.read_book", lambda _p: book)
    monkeypatch.setattr("quill.core.recent.add_recent_audiobook_file", lambda _p: None)
    monkeypatch.setattr(
        "quill.core.speech.listening_positions.save_position_ms",
        lambda _d, _p, ms: saved.append(ms),
    )
    frame = SimpleNamespace(frame=None, _show_modal_dialog=lambda *_a: 5101)  # ID_CANCEL

    module.open_book_in_workbench(frame, book.path, on_closed=lambda *args: closed.append(args))

    assert saved == [25 * MINUTE]
    assert closed == [(str(book.path), 25 * MINUTE, 3)]
    assert stopped == [True]
