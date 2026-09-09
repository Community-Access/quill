"""Timestamped backups: a dated copy of the file, kept on every save.

Different from recovery, and the difference is the whole point. Recovery
(:mod:`quill.core.lite.recovery`) is about work that was *never* saved -- it
exists between a crash and the next launch and is deleted the moment you save.
This is about work that *was* saved, and then saved over: the paragraph you cut
an hour ago, the version before the search-and-replace. Recovery cannot help
with either, because from its point of view nothing went wrong.

Off by default (:data:`quill.core.lite.features.DEFAULT_OFF`), because it
quietly fills a folder and most people editing a shopping list do not want a
version history of it. Discoverable under View > Customize Features, which is
where somebody who *has* lost an hour of work will go looking.

The layout is QUILL's own (``quill/core/backups.py``): one folder per document,
keyed by a hash of its path so two files called ``notes.txt`` in different places
cannot collide, and one UTF-8 ``.bak`` per save named by the moment it was
written. UTF-8 always, whatever the document's own encoding: a backup is a
recovery artifact with no round-trip requirement, and writing it in a narrow
encoding buys a ``UnicodeEncodeError`` that would abort the *save* rather than
just the backup.

The folder is QuillLite's, not QUILL's -- the same rule as everything else here.

Writing them was only ever half the feature. Until 2026-09-09 there was no way
to *see* a backup from inside the app, which made this a safety net nobody could
reach: the files were there, correctly named, and finding one meant knowing that
``%LOCALAPPDATA%\\QuillLite\\backups`` existed and which of the hashed folders
was yours. :func:`read_backup` and :func:`backup_saved_at` are what the browser
in ``lite_window_tools`` needs, and they live here so the naming convention has
exactly one reader and one writer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path

from quill.core.lite.paths import data_dir
from quill.core.storage import write_text_atomic

__all__ = [
    "backup_root",
    "backup_saved_at",
    "list_backups",
    "prune_backups",
    "read_backup",
    "write_backup",
]

#: How many backups of one document are kept. Twenty saves is a working
#: afternoon; beyond that the oldest go, because an unbounded history of a
#: scratch file is a disk-space bug wearing a feature's name.
KEEP_PER_DOCUMENT = 20


def _document_key(path: Path) -> str:
    """A stable folder name for *path*: its name, plus a hash of the full path.

    The name is there so a person can find their own file in the backups folder;
    the hash is there so two files called ``notes.txt`` in different folders do
    not share a history.
    """
    digest = sha1(str(path.resolve()).encode("utf-8", "replace")).hexdigest()[:10]
    return f"{path.stem}-{digest}"


def backup_root(path: Path) -> Path:
    """Where *path*'s backups live."""
    return data_dir() / "backups" / _document_key(path)


def write_backup(path: Path, text: str) -> Path | None:
    """Keep a dated copy of *text* for *path*. ``None`` when it could not be written.

    Never raises: a backup that fails must not be able to fail the save it was
    taken alongside. That is the whole reliability argument for doing it *after*
    the real write rather than before.
    """
    try:
        root = backup_root(path)
        root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        target = root / f"{stamp}.bak"
        suffix = 1
        while target.exists():
            target = root / f"{stamp}-{suffix}.bak"
            suffix += 1
        write_text_atomic(target, text, encoding="utf-8", newline="")
        prune_backups(path)
        return target
    except OSError:
        return None


def list_backups(path: Path) -> list[Path]:
    """Every backup of *path*, newest first."""
    try:
        return sorted(backup_root(path).glob("*.bak"), reverse=True)
    except OSError:
        return []


def backup_saved_at(backup: Path) -> datetime | None:
    """When *backup* was written, from its own name, in local time.

    The filename is the timestamp, so nothing has to be read off disk to build
    a list of twenty versions. ``None`` when the name is not one of ours --
    somebody's own file dropped in the folder must show up as unreadable rather
    than as a plausible wrong date.
    """
    stem = backup.stem.split("-", 1)[0]  # the "-1" collision suffix, if any
    try:
        stamp = datetime.strptime(stem, "%Y%m%dT%H%M%S%fZ").replace(tzinfo=UTC)
    except ValueError:
        return None
    return stamp.astimezone()


def read_backup(backup: Path) -> str | None:
    """The text of one backup, or ``None`` when it cannot be read.

    Always UTF-8, because that is what :func:`write_backup` always writes,
    whatever encoding the document itself uses. ``None`` rather than an
    exception: a backup can have been pruned or removed between the list being
    built and a row being chosen, and the caller can say so.
    """
    try:
        return backup.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def prune_backups(path: Path, keep: int = KEEP_PER_DOCUMENT) -> int:
    """Delete all but the newest *keep* backups. Returns how many went."""
    removed = 0
    for stale in list_backups(path)[keep:]:
        try:
            stale.unlink()
            removed += 1
        except OSError:
            continue
    return removed
