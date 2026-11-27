"""Saying which work a recovery offer is, in the person's own terms (FUX-05).

A recovery offer is a question about somebody's work, and it can only be
answered if it says *which* work: "Unsaved changes to chapter3.md, autosaved
today at 2:14 PM: 1,200 words more than the saved file." Until 2026-11 QUILL's
crash offer said "Restore the latest autosave snapshot", which names a file
format, not a document; it offered only the newest snapshot of the session, so
a second modified document was never offered at all; and after a power cut,
with no error in the log, it offered nothing, although the snapshots were on
disk and nothing else had a copy.

This module answers three questions, wx-free so each is testable on its own:

* :func:`snapshots_by_document` -- every document of a session that left a
  snapshot, newest copy of each, newest document first.
* :func:`worth_offering` -- whether a snapshot holds anything the saved file
  does not. A snapshot identical to its file is not lost work, and is the
  reason the offer was once gated on log evidence; comparing is the honest
  version of that gate.
* :func:`compare_with_saved` and :func:`offer_sentence` -- the words.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

__all__ = [
    "compare_with_saved",
    "offer_sentence",
    "read_saved_text",
    "snapshot_when",
    "snapshots_by_document",
    "word_count",
    "words_phrase",
    "worth_offering",
]

_WORD = re.compile(r"\w+(?:['’]\w+)*")

#: Formats whose bytes are not their words. A recovered copy is compared with
#: one of these by date only, never by a word count it cannot honestly give.
_NOT_TEXT = frozenset({
    ".docx",
    ".doc",
    ".odt",
    ".pdf",
    ".epub",
    ".pages",
    ".xlsx",
    ".pptx",
    ".mobi",
})

#: Read no more of a saved file than this to compare it. A larger file is
#: compared by date only, so launch never stalls on a giant document.
_COMPARE_LIMIT = 20_000_000


def word_count(text: str) -> int:
    """How many words *text* holds, the way a person would count them."""
    return len(_WORD.findall(text))


def words_phrase(count: int) -> str:
    """``1 word``, ``1,200 words``."""
    return "1 word" if count == 1 else f"{count:,} words"


def read_saved_text(original_path: str) -> str | None:
    """The saved file's words, or None when they cannot be read as text."""
    path = Path(original_path)
    if path.suffix.lower() in _NOT_TEXT:
        return None
    try:
        if path.stat().st_size > _COMPARE_LIMIT:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw[:4096]:
        return None
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    if path.suffix.lower() == ".rtf":
        try:
            from quill.io.rtf import rtf_to_markdown

            text = rtf_to_markdown(text)
        except Exception:  # noqa: BLE001 - a damaged file is compared by date
            return None
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _modified_at(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def compare_with_saved(text: str, original_path: str, copied_at: float | None) -> str:
    """How the recovered *text* stands against the file it is a copy of.

    "" for a document that never had a file, or when nothing true can be said.
    Never claims a count it could not make: a Word file is compared by date.
    """
    if not original_path:
        return ""
    saved_path = Path(original_path)
    saved_at = _modified_at(saved_path)
    if saved_at is None:
        return "the saved file is no longer there"
    later = (
        copied_at is not None and saved_at > copied_at + 2
    )  # a save in the same breath as the copy is the same moment
    saved = read_saved_text(original_path)
    if saved is None:
        return "the saved file was changed after this copy" if later else ""
    mine = text.replace("\r\n", "\n").replace("\r", "\n")
    if mine == saved:
        return "the same as the saved file"
    difference = word_count(mine) - word_count(saved)
    if difference > 0:
        phrase = f"{words_phrase(difference)} more than the saved file"
    elif difference < 0:
        phrase = f"{words_phrase(-difference)} fewer than the saved file"
    else:
        phrase = "as long as the saved file, with different words"
    if later:
        phrase += ", which was changed after this copy"
    return phrase


def worth_offering(snapshot: Path, original_path: str | None) -> bool | None:
    """Whether *snapshot* holds work the saved file does not.

    True: offer it (the file is gone, never existed, or differs). False: it is
    the saved file word for word, so nothing is lost by not asking. None: no
    comparison is possible (an older snapshot with no note, a Word file), and
    the caller falls back to whatever it decided before comparing existed.
    """
    if original_path is None:
        return None
    if not original_path:
        return True
    if not Path(original_path).exists():
        return True
    saved = read_saved_text(original_path)
    if saved is None:
        return None
    try:
        mine = snapshot.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return True
    return mine.replace("\r\n", "\n").replace("\r", "\n") != saved


def snapshots_by_document(session_id: str, *, include_untitled: bool = True) -> list[Path]:
    """The newest non-empty snapshot of each document *session_id* autosaved.

    Newest document first, which is the one most likely to have been in front
    when the session ended.
    """
    from uuid import UUID

    from quill.core.autosave import is_untitled_snapshot
    from quill.core.paths import app_data_dir

    UUID(session_id)
    root = app_data_dir() / "autosave" / session_id
    newest: dict[str, tuple[float, Path]] = {}
    try:
        candidates = list(root.glob("*.snap"))
    except OSError:
        return []
    for path in candidates:
        if not include_untitled and is_untitled_snapshot(path):
            continue
        try:
            info = path.stat()
        except OSError:
            continue
        if info.st_size <= 0:
            continue
        key = path.name.split("-", 1)[0]
        held = newest.get(key)
        # Names sort in write order within a key (see autosave_document), so
        # the name breaks an mtime tie on a coarse clock.
        if held is None or (info.st_mtime, path.name) > (held[0], held[1].name):
            newest[key] = (info.st_mtime, path)
    ordered = sorted(newest.values(), key=lambda item: (item[0], item[1].name), reverse=True)
    return [path for _mtime, path in ordered]


def offer_sentence(original_path: str | None, when: str, comparison: str) -> str:
    """One sentence naming the work: what, from when, and against what.

    *when* is :func:`quill.core.action_feedback.when_said` output ("today at
    2:14 PM"); *comparison* is :func:`compare_with_saved` output.
    """
    if original_path:
        head = f"Unsaved changes to {Path(original_path).name}, autosaved {when}"
    elif original_path == "":
        head = f"An untitled document that was never saved, autosaved {when}"
    else:
        head = f"A document whose name was not recorded, autosaved {when}"
    return f"{head}: {comparison}." if comparison else f"{head}."


def snapshot_when(snapshot: Path) -> datetime | None:
    """When *snapshot* was written, or None when the file will not say."""
    try:
        return datetime.fromtimestamp(snapshot.stat().st_mtime)
    except (OSError, ValueError):
        return None
