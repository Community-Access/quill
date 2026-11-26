"""What an episode row says about where its audio is (FUX-13).

The Manager's Status and Downloaded columns used to read two facts: whether the
episode had a ``downloaded_path``, and whether its download was queued, running
or paused. Two states fell through:

* a download that **failed** read "Streaming", the same as an episode nobody
  asked to download, so the listener never learned the download had stopped,
  or why;
* a downloaded file that was later **deleted or moved** outside Cast still read
  "Downloaded", the promise that it plays offline, when it would stream (or not
  play at all with no connection).

The words here are the row's own: one state, in words, with the reason and what
still works. Nothing is announced; the row is read when the listener reaches
it. wx-free so the wording is tested without a window.
"""

from __future__ import annotations

from pathlib import Path

#: The download states that are still under way, said by their own name.
_IN_FLIGHT = ("queued", "downloading", "paused")


def file_present(downloaded_path: str) -> bool:
    """Whether the downloaded file is still where Cast put it."""
    if not downloaded_path:
        return False
    try:
        return Path(downloaded_path).is_file()
    except OSError:
        return False


#: The longest reason a row carries; the whole message is in the log and Details.
REASON_LIMIT = 60


def first_sentence(message: str) -> str:
    """The first sentence of a download error, for a row that has little room.

    Cut on a word at :data:`REASON_LIMIT` characters, so an error with no full
    stop (an exception's text, an address) does not take over the row.
    """
    text = " ".join((message or "").split())
    if not text:
        return ""
    head, dot, _rest = text.partition(". ")
    sentence = head + (dot.strip() if dot else "")
    if len(sentence) <= REASON_LIMIT:
        return sentence
    return sentence[:REASON_LIMIT].rsplit(" ", 1)[0].rstrip(",;:") + "..."


def status_words(
    *,
    downloaded_path: str,
    played: bool,
    item_status: str = "",
    item_error: str = "",
    present: bool | None = None,
) -> str:
    """The Status cell for one episode.

    *present* is whether the downloaded file is on disk; ``None`` asks the disk.
    """
    if downloaded_path:
        on_disk = file_present(downloaded_path) if present is None else present
        if on_disk:
            return "Downloaded" + (", played" if played else "")
        return "File missing, will stream. Download to get it back"
    if item_status in _IN_FLIGHT:
        return item_status.capitalize()
    if item_status == "failed":
        reason = first_sentence(item_error)
        sentence = "Download failed, will stream"
        return f"{sentence}: {reason}" if reason else sentence
    return "Streaming"


def downloaded_words(downloaded_path: str, *, present: bool | None = None) -> str:
    """The Downloaded cell: whether this episode plays without a connection."""
    if not downloaded_path:
        return "Streams"
    on_disk = file_present(downloaded_path) if present is None else present
    return "Downloaded" if on_disk else "File missing, streams"
