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

**A PDF always goes to the worker** (2026-10-15). It is read through the reader
QUILL's File > Open uses (:func:`quill.core.pdf_open.read_pdf_for_open`), and a
two-hundred-page extraction is seconds, not milliseconds, whatever the file's
size on disk. The prepared document carries what the reader found
(:attr:`PreparedDocument.pdf`) so the UI half can ask for a password, offer
OCR, or say why nothing opened -- the questions a worker thread may not ask.

**Word, Excel and PowerPoint files go to the worker too** (2026-10-16), read
as text by the readers QUILL's File > Open uses (:func:`read_office_for_open`).
Like a PDF, the file is never written back: Save goes to Save As
(``quill.apps.lite_window_pdf.is_read_only_source``).

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.lite.textfile import decode_text
from quill.core.pdf_open import PdfOpen, is_pdf_path, read_pdf_for_open
from quill.io.rtf_safety import scan_rtf_safety

__all__ = [
    "BACKGROUND_THRESHOLD_BYTES",
    "OFFICE_OPEN_SUFFIXES",
    "PLAIN",
    "RICH",
    "PreparedDocument",
    "is_office_open_path",
    "prepare",
    "prepare_in_background",
    "read_office_for_open",
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
    #: A PDF: what the shared reader found. ``text`` is its text (form feeds
    #: between pages); the rest -- locked, scanned, outline -- is for the UI.
    pdf: PdfOpen | None = None


#: The Office formats QUILL Lite opens as text: exactly the ones QUILL's own
#: File > Open reads (``quill.io.open_read.OFFICE_STREAM_SUFFIXES``), never
#: more, because QUILL Lite may never be ahead of QUILL. Read by the same
#: shared readers (``quill.io.office_text``), which need nothing QUILL Lite's
#: build leaves out: it ships no MarkItDown or lxml (openpyxl only since the
#: portable gained the office-text group, 2026-10-17), and the readers fall
#: back to the standard library (2026-10-16).
OFFICE_OPEN_SUFFIXES = frozenset({
    ".docx",
    ".docm",
    ".doc",
    ".odt",
    ".pptx",
    ".ppt",
    ".xlsx",
    ".xls",
})


def is_office_open_path(path: Path | str) -> bool:
    return Path(path).suffix.lower() in OFFICE_OPEN_SUFFIXES


def read_office_for_open(path: Path) -> str:
    """An Office file's text for the editor. ``OSError`` with a sentence if unreadable.

    ``OSError`` because that is what both open paths already report as "Could
    not open <name>" with the reason under it; the reason is the shared
    reader's own sentence (damaged, password-protected, or a .doc/.xls/.ppt
    with no LibreOffice and the Save As that fixes it).
    """
    # QUILL's own reader first, MarkItDown only when it fails (2026-10-16): the
    # same order and the same reader as QUILL's File > Open, and no 11-17 s
    # MarkItDown import on a Word file QUILL can read itself.
    from quill.io.office_text import OfficeReadError, read_office_text_preferring_own

    if not Path(path).is_file():
        raise FileNotFoundError(f"{Path(path).name} is no longer there.")
    try:
        return read_office_text_preferring_own(path).text
    except OfficeReadError as exc:
        raise OSError(exc.sentence) from exc


def prepare(path: Path, mode: str, *, password: str | None = None) -> PreparedDocument:
    """Read and decode *path* for *mode*. Raises ``OSError`` if it cannot be read.

    No window, no wx, no announcement: this is the part that may run on a
    worker, and anything it said would be said from the wrong thread.
    *password* unlocks a PDF for this read only; it is not kept anywhere.
    """
    if is_pdf_path(path):
        if not Path(path).is_file():
            raise FileNotFoundError(f"{Path(path).name} is no longer there.")
        found = read_pdf_for_open(Path(path), password=password)
        return PreparedDocument(mode=PLAIN, text=found.text, pdf=found)
    if is_office_open_path(path):
        return PreparedDocument(mode=PLAIN, text=read_office_for_open(Path(path)))
    if mode == RICH:
        # Latin-1 both ways, because it maps every byte to one character and
        # back: an RTF file is 7-bit by the spec, and the 8-bit bytes some
        # writers put in anyway now reach the control as the bytes they were,
        # instead of as UTF-8 replacement characters (2026-10-04: nothing a
        # file is opened for editing through may use errors="replace").
        report = scan_rtf_safety(Path(path).read_bytes().decode("latin-1"))
        return PreparedDocument(
            mode=RICH,
            rtf=report.sanitized_rtf.encode("latin-1", errors="strict"),
            blocked=tuple(report.blocked),
        )
    decoded = decode_text(Path(path).read_bytes())
    return PreparedDocument(
        mode=PLAIN, text=decoded.text, encoding=decoded.encoding, newline=decoded.newline
    )


def prepare_in_background(path: Path) -> bool:
    """Whether opening *path* should read it off the UI thread.

    Yes for a large file, for a network path (``\\\\server\\share``), where
    even a small read can stall on the network or a scanner, and for every PDF,
    whose text extraction is slow at any size; no for everything else. A size
    that cannot be read means "do not guess": the synchronous path reports the
    failure exactly as it always has.
    """
    text = str(path)
    if text.startswith("\\\\") or text.startswith("//") or is_pdf_path(path):
        return True
    if is_office_open_path(path):
        return True  # unzipping and walking XML is not instant, whatever the size
    try:
        return Path(path).stat().st_size >= BACKGROUND_THRESHOLD_BYTES
    except OSError:
        return False
