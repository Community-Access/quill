"""Opening and saving a Word (.docx) document as rich text: the decisions, wx-free.

QUILL has edited Word documents as rich text since Phase 7 of One Editor,
Every Format: the document is read into the shared ``RichDocument`` model,
shown in the native rich control as RTF, and written back through
``rich_to_docx_bytes``. Until 2026-10-17 every decision on that path lived in
``quill.ui.main_frame_rich_mode`` -- which QUILL Lite cannot import, and which a
second copy in QUILL Lite would have drifted from by the first edit. So the
decisions moved here, and both editors call them (CLAUDE.md: QUILL Lite may
never be ahead of QUILL, and shared capability lives in the shared package):

* **The fidelity scan** (:func:`fidelity_findings`): which features of this
  file a rich edit cannot carry -- tables, images, comments, tracked changes,
  headers, footers, footnotes, extra sections. Named specifically, never as
  "some formatting may be lost".
* **The three-way choice** for a file the scan flags (:func:`fidelity_question`,
  :data:`FIDELITY_CHOICES`, :func:`choice_for_selection`): open for reading and
  plain editing (the default, because it is the one that cannot hurt the
  file), edit as rich text with the losses named, or edit a copy. Each app
  asks it in its own dialog; the sentences are these.
* **The one-time backup** (:func:`backup_path_for`, :func:`backup_original`,
  :func:`needs_backup`): before the first overwrite of a flagged original, the
  original is copied beside itself as ``name.backup-YYYYMMDD-HHMMSS.docx``.
  Neither editor ever silently rewrites somebody's Word file.
* **Read to RTF, and RTF back to Word bytes** (:func:`read_docx_as_rtf`,
  :func:`rtf_to_docx_bytes`, :func:`write_docx_from_rtf`).

Nothing here touches a window, so the read can run on a worker thread -- which
is how QUILL Lite opens a Word file without freezing (F-05).

python-docx is optional in both builds (:func:`word_rich_available`); without
it each editor stays on its read-extract path, exactly as before.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from shutil import copy2
from typing import Any

__all__ = [
    "CHOICE_COPY",
    "CHOICE_RICH",
    "CHOICE_TEXT",
    "FIDELITY_DIALOG_TITLE",
    "OPENED_RICH_SENTENCE",
    "RICH_WORD_SUFFIXES",
    "backup_original",
    "backup_path_for",
    "choice_for_selection",
    "fidelity_choices",
    "fidelity_findings",
    "fidelity_question",
    "is_rich_word_path",
    "needs_backup",
    "read_docx_as_rtf",
    "rtf_to_docx_bytes",
    "word_rich_available",
    "write_docx_from_rtf",
]

#: The three answers to the fidelity question, in the order they are offered.
CHOICE_TEXT = "text"
CHOICE_RICH = "rich"
CHOICE_COPY = "copy"
_CHOICE_ORDER = (CHOICE_TEXT, CHOICE_RICH, CHOICE_COPY)

#: The dialog's title in both editors.
FIDELITY_DIALOG_TITLE = "Open Word document"

#: Said once a Word document is in the editor as rich text, in both editors.
OPENED_RICH_SENTENCE = "Opened as Rich Text. Headings and bold are shown formatted."

#: The Word formats either editor edits as rich text. Only ``.docx``: the
#: writer makes a plain Word document, and a ``.docm`` written without its
#: macros under a ``.docm`` name is a file Word refuses to open. A ``.docm``
#: therefore opens as text in both editors, as it always has.
RICH_WORD_SUFFIXES = frozenset({".docx"})


def is_rich_word_path(path: Path | str) -> bool:
    """True for a file either editor may open and save as a rich Word document."""
    return Path(path).suffix.lower() in RICH_WORD_SUFFIXES


def word_rich_available() -> bool:
    """Whether this build can read and write Word documents (python-docx)."""
    try:
        from quill.io.docx_writer import python_docx_available
    except Exception:  # noqa: BLE001 - the io layer is a soft boundary here
        return False
    return bool(python_docx_available())


def fidelity_findings(path: Path) -> list[str]:
    """What a rich edit of *path* cannot carry; empty for a clean file."""
    from quill.io.docx_reader import scan_docx_features

    return list(scan_docx_features(Path(path)))


def fidelity_question(name: str, findings: list[str] | tuple[str, ...], *, app: str) -> str:
    """The question a flagged file is opened with. *app* is "QUILL" or "QUILL Lite"."""
    inventory = ", ".join(findings)
    return (
        f"{name} contains features {app}'s rich editor cannot carry: {inventory}.\n\n"
        "How should it open?"
    )


def fidelity_choices(findings: list[str] | tuple[str, ...]) -> list[str]:
    """The three rows of the choice, the safe one first and preselected."""
    inventory = ", ".join(findings)
    return [
        "Open for reading and plain editing (recommended)",
        f"Edit as Rich Text — these will not survive a save: {inventory}",
        "Edit a copy as Rich Text (the original stays untouched)",
    ]


def choice_for_selection(index: int) -> str:
    """The answer a selected row stands for, clamped so a stray index is safe."""
    return _CHOICE_ORDER[max(0, min(len(_CHOICE_ORDER) - 1, int(index)))]


def backup_path_for(target: Path, *, now: datetime | None = None) -> Path:
    """``report.backup-20261017-143000.docx`` beside ``report.docx``."""
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    return target.with_name(f"{target.stem}.backup-{stamp}{target.suffix}")


def backup_original(target: Path) -> Path | None:
    """Copy *target* to a timestamped sibling. ``None`` when the copy failed."""
    backup = backup_path_for(Path(target))
    try:
        copy2(target, backup)
    except OSError:
        return None
    return backup


def needs_backup(*, flagged: bool, backup_done: bool, target: Path) -> bool:
    """Whether this save must copy the original aside first.

    Only a flagged original (one whose features a save drops), only once per
    editing session, and only when there is a file there to lose.
    """
    return bool(flagged) and not backup_done and Path(target).exists()


def read_docx_as_rtf(path: Path) -> str:
    """The Word document as RTF for the native rich control. Raises on failure."""
    from quill.io.docx_reader import read_docx_rich
    from quill.io.rtf_model import rich_to_rtf

    return rich_to_rtf(read_docx_rich(Path(path)))


def rtf_to_docx_bytes(rtf: str) -> bytes:
    """The rich control's RTF as the bytes of a Word document.

    Trailing empty paragraphs are dropped first. The rich control always ends
    its RTF with a paragraph mark of its own, which reads back as one more
    empty paragraph -- so every save of a Word document used to add a blank
    line at its end, one per save, for ever (found 2026-10-17 by saving the
    same document three times).
    """
    from quill.io.docx_writer import rich_to_docx_bytes
    from quill.io.rtf_model import rtf_to_rich

    # The control's stream also ends in a NUL after the closing brace, which
    # the reader takes for one more paragraph holding a control character.
    document = rtf_to_rich(rtf.rstrip("\x00\r\n "))
    paragraphs = document.paragraphs
    while paragraphs and _is_empty(paragraphs[-1]):
        paragraphs.pop()
    return rich_to_docx_bytes(document)


def _is_empty(paragraph: Any) -> bool:
    if getattr(paragraph, "style", "paragraph") != "paragraph":
        return False
    return not "".join(str(span.text) for span in paragraph.spans).strip("\x00 \t\r\n ")


def write_docx_from_rtf(target: Path, rtf: str) -> None:
    """Write the rich control's RTF to *target* as Word, atomically."""
    from quill.core.storage import write_bytes_atomic

    write_bytes_atomic(Path(target), rtf_to_docx_bytes(rtf))
