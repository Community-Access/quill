"""Where a document to open can come from, besides the Open dialog (2026-10-04).

PlanCake (Andre, Oire Software) opens a plan however it arrives: a file copied
in File Explorer, a path copied out of a chat as text, a web link, or a file
dragged onto the window. The 2026-10-04 design note brought the same to both
editors, and this module is the part of it with no window in it, so QUILL and
QUILL Lite decide the same things the same way:

* :func:`classify_clipboard` -- what the clipboard holds that can be opened:
  files, a path typed as text, or a link. **Open from Clipboard** in both
  editors calls it, and says :data:`NOTHING_TO_OPEN` when the answer is none.
* :func:`prepare_url` -- a link as somebody pasted it, made into one QUILL can
  download, with an ordinary GitHub page link turned into the raw file behind
  it (PlanCake's idea too).
* :func:`consent_question` and :func:`failure_sentence` -- the two things Open
  from URL says: the question before any of the file is downloaded, naming the
  host and the size, and one plain sentence when the download fails.

wx-free, strict-typed.
"""

from __future__ import annotations

import os
import re
import urllib.parse
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "FILES",
    "NONE",
    "NOTHING_TO_OPEN",
    "URL",
    "ClipboardOpen",
    "classify_clipboard",
    "clipboard_sentence",
    "consent_question",
    "dropped_sentence",
    "failure_sentence",
    "format_size",
    "github_raw_url",
    "path_from_text",
    "prepare_url",
]

#: What :func:`classify_clipboard` found.
FILES = "files"
URL = "url"
NONE = "none"

#: The one sentence both editors say when nothing on the clipboard can open.
NOTHING_TO_OPEN = "The clipboard holds no file, path or link."

_GITHUB_BLOB = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<rest>.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ClipboardOpen:
    """What the clipboard offers to open, in the order it should open.

    ``skipped`` counts what was on the clipboard and is not a file that can
    open -- a folder copied with the files, say -- so the outcome can say so.
    """

    kind: str
    paths: tuple[Path, ...] = field(default_factory=tuple)
    url: str = ""
    skipped: int = 0


def github_raw_url(url: str) -> str:
    """The raw file behind an ordinary GitHub page link; anything else unchanged.

    ``https://github.com/owner/repo/blob/main/docs/plan.md`` shows a web page
    *about* the file; ``https://raw.githubusercontent.com/owner/repo/main/docs/plan.md``
    is the file. People copy the first, because it is what the browser shows.
    """
    match = _GITHUB_BLOB.match(url.strip())
    if match is None:
        return url
    rest = match.group("rest").split("#", 1)[0].split("?", 1)[0]
    return f"https://raw.githubusercontent.com/{match.group('owner')}/{match.group('repo')}/{rest}"


def prepare_url(text: str) -> str:
    """*text* as a downloadable http(s) URL, or ``""`` when it is not one.

    Tolerates what a link picks up on its way through a chat: surrounding
    quotes or angle brackets, and a bare ``www.`` with no scheme.
    """
    candidate = text.strip().strip("<>").strip().strip("\"'").strip()
    if not candidate or any(character.isspace() for character in candidate):
        return ""
    if candidate.lower().startswith("www."):
        candidate = "https://" + candidate
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    return github_raw_url(candidate)


def path_from_text(text: str) -> Path | None:
    """A path written as text -- quoted, ``file:`` URL or plain -- or ``None``.

    Does not check that it exists; :func:`classify_clipboard` does.
    """
    candidate = text.strip().strip("\"'").strip()
    if not candidate or "\n" in candidate:
        return None
    if candidate.lower().startswith("file:"):
        parsed = urllib.parse.urlparse(candidate)
        local = urllib.parse.unquote(parsed.path)
        if parsed.netloc:
            local = f"//{parsed.netloc}{local}"
        elif re.match(r"^/[A-Za-z]:", local):
            local = local[1:]
        candidate = local
    candidate = os.path.expandvars(os.path.expanduser(candidate))
    return Path(candidate)


def classify_clipboard(
    files: Sequence[str],
    text: str | None,
    *,
    is_file: Callable[[Path], bool] | None = None,
) -> ClipboardOpen:
    """Decide what Open from Clipboard opens, in PlanCake's order.

    1. Files copied in File Explorer, every one that is a file, in order.
    2. Text that is one path, or one path per line, to files that exist.
    3. Text that is a link.

    Otherwise :data:`NONE`. *is_file* is injectable so tests need no disk.
    """
    exists = is_file or (lambda path: path.is_file())
    if files:
        found = tuple(Path(item) for item in files if exists(Path(item)))
        if found:
            return ClipboardOpen(FILES, paths=found, skipped=len(files) - len(found))
    if not text or not text.strip():
        return ClipboardOpen(NONE)
    lines = [line for line in text.strip().splitlines() if line.strip()]
    candidates = [path_from_text(line) for line in lines]
    paths = tuple(path for path in candidates if path is not None and exists(path))
    if paths and len(paths) == len(lines):
        return ClipboardOpen(FILES, paths=paths)
    if len(lines) == 1:
        url = prepare_url(lines[0])
        if url:
            return ClipboardOpen(URL, url=url)
    return ClipboardOpen(NONE)


def format_size(size: int | None) -> str:
    """A size in the words a person uses: "12 KB", "3.4 MB", "512 bytes"."""
    if size is None or size < 0:
        return "an unknown size"
    if size < 1024:
        return f"{size} byte{'s' if size != 1 else ''}"
    if size < 1024 * 1024:
        return f"{max(1, round(size / 1024))} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def consent_question(host: str, filename: str, size: int | None) -> str:
    """The question Open from URL asks before downloading any of the file.

    Names the host and the size, as the user guide promises. A server that
    does not say how large the file is is said to have not said, rather than
    guessed at.
    """
    where = host or "that address"
    if size is None:
        sized = "The server did not say how large it is."
    else:
        sized = f"It is {format_size(size)}."
    return f"Download {filename} from {where}? {sized}"


def failure_sentence(error: BaseException, host: str) -> str:
    """One plain sentence for a download that did not work.

    The coded transport errors are told apart by kind, never by spelling out
    the exception, which is written for a log rather than for a person.
    """
    from quill.io.remote_transport import (
        RemoteAuthError,
        RemoteNotFoundError,
        RemoteTransportError,
    )

    where = host or "that address"
    if isinstance(error, RemoteNotFoundError):
        return f"Nothing was found at that address on {where}."
    if isinstance(error, RemoteAuthError):
        return f"{where} would not allow the download without signing in."
    message = str(error)
    if isinstance(error, RemoteTransportError) and "refuses downloads larger" in message:
        return "That file is larger than QUILL downloads from a link."
    if isinstance(error, RemoteTransportError) and "exceeds" in message:
        return "That file is larger than QUILL downloads from a link."
    return (
        f"Could not download from {where}. Check the address and your connection, then try again."
    )


def clipboard_sentence(opened: int, skipped: int) -> str:
    """What Open from Clipboard says after opening files; ``""`` for just one.

    One file opening is heard already -- its window or tab takes focus and
    the screen reader reads the title -- so only what is not heard is said:
    how many, when it was several, and what could not be opened.
    """
    if opened <= 1 and not skipped:
        return ""
    noun = "file" if opened == 1 else "files"
    sentence = f"Opened {opened} {noun} from the clipboard."
    if skipped:
        sentence += f" {skipped} could not be opened."
    return sentence


def dropped_sentence(opened: int, skipped: int) -> str:
    """What dropping files on the window did, said once (only what is not seen)."""
    if opened == 0:
        return "Nothing dropped could be opened."
    noun = "file" if opened == 1 else "files"
    sentence = f"Opened {opened} dropped {noun}."
    if skipped:
        sentence += f" {skipped} could not be opened."
    return sentence
