"""The Vault model — a folder of notes, parsed into indexable metadata (wx-free).

``scan_vault`` walks a vault root, parses every Markdown/plain-text note, and
returns a :class:`Vault` mapping each note's relative POSIX path to its
:class:`~quill.core.vault.note.NoteInfo`. Dot-directories (notably the ``.quill``
index cache) are skipped. The result is the input to the link/backlink index and
the resolver.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from quill.core.vault.note import NoteInfo, parse_note

__all__ = ["Vault", "scan_vault", "CACHE_DIRNAME"]

CACHE_DIRNAME = ".quill"
_TEXT_SUFFIXES = (".md", ".markdown", ".txt")


@dataclass(frozen=True, slots=True)
class Vault:
    """A scanned vault: its root, every note's metadata, and its raw text.

    ``texts`` keeps each note's raw contents (keyed like ``notes``) so the link
    index can quote the sentence around a backlink and find unlinked mentions
    without re-reading files. Notes are plain text and small; this stays cheap.
    """

    root: Path
    notes: dict[str, NoteInfo]
    texts: dict[str, str]


def scan_vault(root: Path) -> Vault:
    """Parse every note under ``root`` into a :class:`Vault`."""
    notes: dict[str, NoteInfo] = {}
    texts: dict[str, str] = {}
    for path in _iter_note_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        texts[rel] = text
        notes[rel] = parse_note(text, path.stem)
    return Vault(root=root, notes=notes, texts=texts)


def _iter_note_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue  # skip .quill/ and any other dot-directory or dotfile
        yield path
