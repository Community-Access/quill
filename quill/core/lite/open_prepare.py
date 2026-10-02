"""Opening a file in QUILL Lite, split into the slow half and the quick half (F-05).

``DocumentFrame.load`` used to read, decode and safety-scan a file on the UI
thread. For a large file, a slow network folder, an antivirus scan that holds
the read, or a damaged RTF, the window stopped responding -- and a listener
cannot tell "working" from "hung" when nothing is said and nothing moves.

So opening is two phases:

1. **Prepare** (this module, any thread): read the bytes, decode them -- or
   scan an RTF and keep the sanitised copy -- and return an immutable
   :class:`PreparedDocument`. Nothing here touches a window.
2. **Commit** (``DocumentFileMixin._commit_load``, UI thread only): put the
   prepared text into the editor and do everything that follows a load.

The Rich Edit control is only ever mutated on the UI thread; the expensive
file and scan work does not have to be. :func:`prepare_in_background` is the
policy for *when* the split is worth its cost: a small local file opens
synchronously, because the window then never shows an empty document first.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.lite.textfile import decode_text
from quill.io.rtf_safety import scan_rtf_safety

__all__ = [
    "BACKGROUND_THRESHOLD_BYTES",
    "PLAIN",
    "RICH",
    "PreparedDocument",
    "prepare",
    "prepare_in_background",
]

#: The editor's two modes, spelled as ``quill.ui.richedit_editing`` spells
#: them; repeated here because a core module may not import the UI.
PLAIN = "plain"
RICH = "rich"

#: At or above this size a file is read off the UI thread. One mebibyte reads
#: in well under the time anybody notices on a local disk, so below it the
#: synchronous path's one advantage -- the document appears whole, at once --
#: wins.
BACKGROUND_THRESHOLD_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class PreparedDocument:
    """Everything a load needs from the file, decided off the UI thread."""

    mode: str
    #: Plain text: the decoded text and the two facts a save must preserve.
    text: str = ""
    encoding: str = "utf-8"
    newline: str = "\n"
    #: Rich text: the sanitised RTF, and what the safety scan removed.
    rtf: bytes = b""
    blocked: tuple[str, ...] = ()


def prepare(path: Path, mode: str) -> PreparedDocument:
    """Read and decode *path* for *mode*. Raises ``OSError`` if it cannot be read.

    No window, no wx, no announcement: this is the part that may run on a
    worker, and anything it said would be said from the wrong thread.
    """
    if mode == RICH:
        report = scan_rtf_safety(Path(path).read_text(encoding="utf-8", errors="replace"))
        return PreparedDocument(
            mode=RICH,
            rtf=report.sanitized_rtf.encode("utf-8", errors="replace"),
            blocked=tuple(report.blocked),
        )
    decoded = decode_text(Path(path).read_bytes())
    return PreparedDocument(
        mode=PLAIN, text=decoded.text, encoding=decoded.encoding, newline=decoded.newline
    )


def prepare_in_background(path: Path) -> bool:
    """Whether opening *path* should read it off the UI thread.

    Yes for a large file, and for a network path (``\\\\server\\share``), where
    even a small read can stall on the network or a scanner; no for everything
    else. A size that cannot be read means "do not guess": the synchronous path
    reports the failure exactly as it always has.
    """
    text = str(path)
    if text.startswith("\\\\") or text.startswith("//"):
        return True
    try:
        return Path(path).stat().st_size >= BACKGROUND_THRESHOLD_BYTES
    except OSError:
        return False
