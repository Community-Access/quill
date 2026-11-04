"""Quill Media Player opens a web address, and a second launch hands its files over.

Two routes reach the Player with something to play: its command line (Explorer's
Open With, QUILL's Tools > Media, the WordPress player's "Open in Quill Media
Player", which passes the file's https address), and a second launch while the
Player is already running. Before 2026-11-04 the first route read every argument
as a file path, so ``https://site/a.mp3`` became ``https:\\site\\a.mp3`` and
nothing played, and the second route dropped its arguments and was never read.

An address is played the way a local file is: the shared transport panel loads
it and the engine streams it. Nothing is written to disk and no resume position
is kept for it, because a web address is not a file the listener owns. Only
``https`` is accepted; ``http`` is refused in words, the same rule the
connection to a WordPress site follows.

The hand-over rides the family's IPC queue (``quill.core.ipc``), whose request
carries a ``Path``. A ``Path`` folds the ``//`` of an address and turns its
slashes round on Windows, so an address travels hex-encoded under its own
action and is decoded here; a file path travels as itself.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

__all__ = [
    "HANDOVER_ACTION",
    "PlayerAddressMixin",
    "address_problem",
    "decode_handover",
    "encode_handover",
    "hand_over",
    "is_web_address",
    "launch_arguments",
    "title_for_address",
]

_TITLE = "Quill Media Player"

#: The IPC action a second launch uses for a web address.
HANDOVER_ACTION = "play-address"

#: How often the running Player looks for a second launch's hand-over.
_HANDOVER_POLL_MS = 600


def launch_arguments(argv: Iterable[str]) -> list[str]:
    """The things to open, as typed: every argument that is not a ``-`` switch.

    Kept as strings, because ``Path`` would mangle a web address.
    """
    return [arg for arg in argv if arg and not arg.startswith("-")]


def is_web_address(text: str) -> bool:
    """True for anything shaped ``scheme://...``; a drive letter is not a scheme."""
    if "://" not in text:
        return False
    scheme = urlsplit(text).scheme
    return len(scheme) > 1 and scheme.isascii() and scheme.isalpha()


def address_problem(url: str) -> str | None:
    """Why this address will not be played, or None when it will."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    if scheme == "https" and parts.hostname:
        return None
    if scheme == "https":
        return f"That web address has no site name in it, so there is nothing to play.\n\n{url}"
    if scheme == "http":
        return (
            "Quill Media Player plays web addresses that start with https only. "
            "This one starts with http, which is not private. Ask for its https "
            f"address, or download the file and open it.\n\n{url}"
        )
    return (
        f"Quill Media Player cannot play {scheme} addresses. It plays files on this "
        f"computer and web addresses that start with https.\n\n{url}"
    )


def title_for_address(url: str) -> str:
    """The name to show for an address: its file name, or else its site."""
    parts = urlsplit(url)
    name = unquote(parts.path.rstrip("/").rsplit("/", 1)[-1])
    return name or parts.hostname or url


def encode_handover(url: str) -> Path:
    """An address as a ``Path`` that survives the IPC queue unchanged."""
    return Path(url.encode("utf-8").hex())


def decode_handover(path: Path | str) -> str | None:
    """The address :func:`encode_handover` wrote, or None for anything else."""
    try:
        return bytes.fromhex(Path(path).name).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def hand_over(arguments: list[str], enqueue: Callable[..., None], *, slot: str) -> None:
    """What a second launch sends the running Player: its things to open, or a nudge.

    With nothing to open it asks only to be shown, as before.
    """
    if not arguments:
        enqueue(None, slot=slot)
        return
    for argument in arguments:
        if is_web_address(argument):
            enqueue(encode_handover(argument), action=HANDOVER_ACTION, slot=slot)
        else:
            enqueue(Path(argument), slot=slot)


class PlayerAddressMixin:
    """Opening an address, and taking a second launch's hand-over, for the Player."""

    frame: Any
    _player: Any
    _book_path: Path | None
    _book_key: str
    _chapters: list
    _chapter_nodes: list

    def _open_launch_arguments(self, arguments: Iterable[str]) -> bool:
        """Open the first thing in *arguments* that can be opened; True when one was.

        A web address plays at once; a file that exists loads the way File >
        Open loads it. A file that is not there is passed over, as it always was.
        """
        for argument in arguments:
            if is_web_address(argument):
                return self._open_address(argument)
            path = Path(argument)
            if path.is_file():
                self._load_book(path)
                return True
        return False

    def _open_address(self, url: str) -> bool:
        """Stream *url* from the start: loaded, then playing, with nothing saved."""
        url = url.strip()
        problem = address_problem(url)
        if problem is not None:
            self._show_message_box(problem, _TITLE)
            return False
        title = title_for_address(url)
        if not self._player.load(url, [], resume_ms=0, autoplay=True):
            self._show_message_box(f"Could not play {title}.\n\n{url}", _TITLE)
            return False
        from quill.ui.media.now_playing_apps import refresh_player_card

        self._book_path = None  # nothing on disk, so no resume position is kept
        self._book_key = url  # bookmarks still work while it plays
        self._chapters = []
        self._chapter_nodes = []
        self._set_playlist_from_nodes()
        self._now_playing.SetValue(title)
        refresh_player_card(self, title=title)
        self._refresh_chapters()
        self._refresh_bookmarks()
        self._set_status(f"Playing {title}")
        return True

    # -- the second launch's hand-over -----------------------------------------

    def _start_handover_poll(self) -> None:
        """Look for a second launch's hand-over; stopped on close (player_close)."""
        import wx

        self._handover_timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_handover_timer, self._handover_timer)
        self._handover_timer.Start(_HANDOVER_POLL_MS)

    def _on_handover_timer(self, _event: object = None) -> None:
        from quill.core.ipc import drain_open_requests

        self._take_handover(drain_open_requests(slot="player"))

    def _take_handover(self, requests: list) -> None:
        """Open what a second launch sent, and bring the window forward."""
        if not requests:
            return
        arguments: list[str] = []
        for request in requests:
            if request is None:
                continue
            if request.action == HANDOVER_ACTION:
                url = decode_handover(request.path)
                if url:
                    arguments.append(url)
            else:
                arguments.append(str(request.path))
        self._restore_from_tray()
        if arguments:
            self._open_launch_arguments(arguments)
