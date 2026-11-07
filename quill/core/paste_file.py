"""Paste File: what to put in the document when the clipboard holds copied files.

Copy a file in File Explorer and press Paste in an editor, and you get nothing,
or a path you did not ask for. Paste File asks which you meant: each file's
text, read the way the editor would open it, or each file's full path. Both
editors run this through ``quill/ui/paste_file.py``; every decision and every
sentence is here, wx-free, so the two cannot answer it differently.

Two limits, both spoken rather than silent:

* **A file over** :data:`MAX_FILE_BYTES` **is refused by name.** Pasting a
  20 MB log into the middle of a letter is never what somebody meant, and
  reading it would freeze the window while they waited to find that out.
* **A file that is not text is refused by name** -- a picture, a program, an
  archive -- rather than pasted as a screen of nonsense a screen reader would
  then read aloud.

The rest are pasted, and the sentence says how many were and which were not.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "CHOICES",
    "MAX_FILE_BYTES",
    "PastePlan",
    "describe_paste",
    "file_text",
    "paths_text",
    "plan_paste",
    "refusal",
]

#: Five megabytes: a long book in plain text, and well past any letter.
MAX_FILE_BYTES = 5 * 1024 * 1024

#: ``(choice id, the row the dialog shows)``, in the order the dialog offers them.
CHOICES: tuple[tuple[str, str], ...] = (
    ("text", "Each file's text"),
    ("path", "Each file's full path"),
)

#: What sits between two files' text: a blank line, so each starts a paragraph.
_BETWEEN_FILES = "\n\n"


def _readable_suffixes() -> frozenset[str]:
    from quill.io.open_read import (
        BRF_SUFFIXES,
        LIGHT_STRUCTURED_SUFFIXES,
        OFFICE_STREAM_SUFFIXES,
    )

    return OFFICE_STREAM_SUFFIXES | LIGHT_STRUCTURED_SUFFIXES | BRF_SUFFIXES


def _looks_binary(path: Path) -> bool:
    """A NUL byte in the first 8 KB: what every text-or-not sniff agrees on."""
    try:
        with path.open("rb") as handle:
            head = handle.read(8192)
    except OSError:
        return False  # the read below will say what is wrong
    if head.startswith((b"\xff\xfe", b"\xfe\xff")):
        return False  # UTF-16 text is full of NULs and is still text
    return b"\x00" in head


def refusal(path: Path) -> str:
    """Why *path* cannot be pasted as text, or "" when it can."""
    name = path.name or str(path)
    if path.is_dir():
        return f"{name} is a folder"
    try:
        size = path.stat().st_size
    except OSError:
        return f"{name} could not be read"
    if size > MAX_FILE_BYTES:
        megabytes = size / (1024 * 1024)
        return f"{name} is {megabytes:.0f} MB, over the {MAX_FILE_BYTES // (1024 * 1024)} MB limit"
    if path.suffix.lower() not in _readable_suffixes() and _looks_binary(path):
        return f"{name} is not a text file"
    return ""


def file_text(path: Path) -> str:
    """*path*'s text, read the way the editor opens it (Word, PDF, plain text...)."""
    from quill.io.open_read import read_open_document

    document, _book = read_open_document(path, path.suffix.lower())
    return str(document.text)


def paths_text(paths: list[Path]) -> str:
    """One full path per line."""
    return "\n".join(str(path) for path in paths)


@dataclass(slots=True)
class PastePlan:
    """What Paste File will insert, and what it refused and why."""

    text: str = ""
    pasted: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)


def plan_paste(
    paths: list[Path],
    choice: str,
    *,
    reader: Callable[[Path], str] = file_text,
) -> PastePlan:
    """Read every file (or name it) and collect what was refused."""
    if choice == "path":
        return PastePlan(text=paths_text(paths), pasted=[p.name for p in paths])
    plan = PastePlan()
    pieces: list[str] = []
    for path in paths:
        reason = refusal(path)
        if not reason:
            try:
                pieces.append(reader(path).rstrip("\n"))
                plan.pasted.append(path.name)
                continue
            except Exception as error:  # noqa: BLE001 - every reader failure is one sentence
                reason = f"{path.name} could not be read: {error}"
        plan.refused.append(reason)
    plan.text = _BETWEEN_FILES.join(pieces)
    return plan


def describe_paste(plan: PastePlan, choice: str) -> str:
    """The one sentence after Paste File: what went in, then what did not."""
    count = len(plan.pasted)
    if choice == "path":
        noun = "path" if count == 1 else "paths"
        return f"Pasted {count} {noun}"
    parts = []
    if count:
        noun = "file" if count == 1 else "files"
        parts.append(f"Pasted the text of {count} {noun}")
    else:
        parts.append("Nothing was pasted")
    if plan.refused:
        parts.append("Not pasted: " + "; ".join(plan.refused))
    return ". ".join(parts)
