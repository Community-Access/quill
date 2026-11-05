"""Quill Media Player opens an https address, from its command line or a second launch.

The WordPress player's "Open in Quill Media Player" passes the file's address on
the Player's command line. Before this, ``main()`` turned it into a ``Path``
(``https://`` folded to ``https:\\``), the window opened only files that exist,
and a second launch dropped its arguments. These tests drive the real window
over the real shared transport panel, with only the panel's engine faked, and
the real IPC queue in an isolated data folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.apps.player_address import (  # noqa: E402
    HANDOVER_ACTION,
    address_problem,
    decode_handover,
    hand_over,
    is_web_address,
    launch_arguments,
    title_for_address,
)

pytestmark = pytest.mark.usefixtures("closed_machine_doors")

URL = "https://example.test/wp-content/uploads/2026/11/Quill%20Tone.mp3?ver=2"


class _Engine:
    """Plays nothing; records what it was asked to load and whether it played."""

    def __init__(self) -> None:
        self.loaded: list[str] = []
        self.played = 0

    def load(self, path: str) -> bool:
        self.loaded.append(path)
        return True

    def play(self) -> None:
        self.played += 1

    def position_ms(self) -> int:
        return 0

    def is_playing(self) -> bool:
        return False

    def length_ms(self) -> int:
        return 3_000

    def __getattr__(self, _name: str) -> Any:
        return lambda *_a, **_k: None


@pytest.fixture
def player(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch, request):
    from tests.unit.docs._app_menu_bar import real_app_shell

    with real_app_shell(monkeypatch, request, "quill.apps.player", "QuillMediaPlayerFrame") as app:
        said: list[str] = []
        boxes: list[str] = []
        app._announce = lambda message, **_kw: said.append(str(message))
        app._player._announce_fn = app._announce
        app._show_message_box = lambda message, *_a, **_k: boxes.append(message)
        app._restore_from_tray = lambda: said.append("<shown>")
        app._player._engine = _Engine()
        app.said, app.boxes = said, boxes
        try:
            yield app
        finally:
            app._player._timer.Stop()


# -- the rules, without a window --------------------------------------------------


def test_launch_arguments_keep_an_address_whole() -> None:
    assert launch_arguments(["--tray", URL, r"C:\Books\a.mp3"]) == [URL, r"C:\Books\a.mp3"]


def test_a_drive_letter_is_not_a_web_address() -> None:
    assert is_web_address(URL)
    assert not is_web_address(r"C:\Books\a.mp3")
    assert not is_web_address("C://Books/a.mp3")


def test_only_https_is_played() -> None:
    assert address_problem(URL) is None
    http = address_problem("http://example.test/a.mp3")
    assert http is not None and "https only" in http and "http://example.test/a.mp3" in http
    ftp = address_problem("ftp://example.test/a.mp3")
    assert ftp is not None and "cannot play ftp addresses" in ftp
    assert address_problem("https:///a.mp3") is not None


def test_the_title_is_the_file_name() -> None:
    assert title_for_address(URL) == "Quill Tone.mp3"
    assert title_for_address("https://example.test/") == "example.test"


def test_an_address_survives_the_ipc_queue(quill_data_dir: Path) -> None:
    from quill.core.ipc import drain_open_requests, enqueue_open_request

    hand_over([URL, r"C:\Books\a.mp3"], enqueue_open_request, slot="player")
    first, second = drain_open_requests(slot="player")
    assert first is not None and first.action == HANDOVER_ACTION
    assert decode_handover(first.path) == URL
    assert second is not None and second.path == Path(r"C:\Books\a.mp3")
    assert decode_handover(second.path) is None


def test_a_bare_second_launch_still_only_asks_to_be_shown(quill_data_dir: Path) -> None:
    from quill.core.ipc import drain_open_requests, enqueue_open_request

    hand_over([], enqueue_open_request, slot="player")
    assert drain_open_requests(slot="player") == [None]


# -- the real window ----------------------------------------------------------------


def test_an_address_on_the_command_line_streams_and_plays(player) -> None:
    assert (lambda w: w._open_launch_arguments([URL]))(player) is True

    engine = player._player._engine
    assert engine.loaded == [URL]  # the address itself, nothing downloaded
    assert player._now_playing.GetValue() == "Quill Tone.mp3"
    assert player._book_key == URL and player._book_path is None
    player._player._on_engine_loaded(3_000)
    assert engine.played == 1  # plays as soon as it has loaded
    assert "Loaded, 0:03" in player.said


def test_http_is_refused_in_words_and_nothing_loads(player) -> None:
    assert (lambda w: w._open_launch_arguments(["http://example.test/a.mp3"]))(player) is False
    assert player._player._engine.loaded == []
    assert player.boxes and "https only" in player.boxes[0]


def test_a_local_file_still_opens(player, tmp_path: Path) -> None:
    book = tmp_path / "chapter one.mp3"
    book.write_bytes(b"\0")
    assert (lambda w: w._open_launch_arguments([str(tmp_path / "missing.mp3"), str(book)]))(player)
    assert player._player._engine.loaded == [str(book)]
    assert player._now_playing.GetValue() == "chapter one"


def test_a_second_launch_hands_its_address_to_the_running_player(
    player, quill_data_dir: Path
) -> None:
    from quill.core.ipc import enqueue_open_request

    hand_over([URL], enqueue_open_request, slot="player")
    (lambda w: w._on_handover_timer())(player)

    assert player.said[0] == "<shown>"
    assert player._player._engine.loaded == [URL]


def test_a_bare_second_launch_shows_the_window_and_opens_nothing(
    player, quill_data_dir: Path
) -> None:
    from quill.core.ipc import enqueue_open_request

    hand_over([], enqueue_open_request, slot="player")
    (lambda w: w._on_handover_timer())(player)

    assert player.said == ["<shown>"]
    assert player._player._engine.loaded == []


def test_the_handover_clock_stops_when_the_window_closes(player) -> None:
    from quill.apps import player_close

    assert player._handover_timer.IsRunning()

    class _Event:
        def Skip(self) -> None:  # noqa: N802 - wx API shape
            pass

    player_close.on_player_close(player, _Event())
    assert not player._handover_timer.IsRunning()


def test_go_to_position_works_on_a_stream(player, monkeypatch: pytest.MonkeyPatch) -> None:
    player._open_address(URL)
    shown: list[str] = []
    monkeypatch.setattr(player, "_show_modal_dialog", lambda _d, title: shown.append(title))
    (lambda w: w._on_go_to_position(None))(player)
    assert shown == ["Go to Position"]
    assert not player.boxes
