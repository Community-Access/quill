"""External file-change detection and safe-reload decisions (FEAT-19).

A small, UI-agnostic helper that watches the open document's file for external
modification or deletion and decides what should happen, without ever touching
``wx`` or moving the cursor itself. The UI layer owns the editor buffer and is
responsible for preserving the cursor, selection, and scroll position when it
acts on a decision; this module only answers *what* should happen.

The model is deliberately pure and testable:

* :class:`FileSnapshot` captures the on-disk identity of a file (existence,
  size, modification time, and a content hash) at a point in time.
* :class:`ExternalChangeWatcher` remembers the last snapshot it reported and,
  on each poll, classifies the file as unchanged, modified, or deleted.
* :func:`decide_reload` turns a change plus the buffer's dirty state and the
  user's settings into one of a small set of :class:`ReloadDecision` actions.

The watcher is polled (reusing the existing watch-folder polling pattern) off
the UI thread; the decision functions are synchronous and side-effect free.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Change classifications reported by the watcher.
CHANGE_NONE = "none"
CHANGE_MODIFIED = "modified"
CHANGE_DELETED = "deleted"


class ReloadAction(Enum):
    """What the UI should do in response to an external change."""

    NONE = "none"
    RELOAD = "reload"
    KEEP_MINE = "keep_mine"
    PROMPT_CLEAN = "prompt_clean"
    PROMPT_CONFLICT = "prompt_conflict"
    PROMPT_DELETED = "prompt_deleted"


@dataclass(frozen=True, slots=True)
class ReloadDecision:
    """An action plus a ready-to-speak announcement for the UI to honor."""

    action: ReloadAction
    announcement: str

    @property
    def needs_prompt(self) -> bool:
        return self.action in (
            ReloadAction.PROMPT_CLEAN,
            ReloadAction.PROMPT_CONFLICT,
            ReloadAction.PROMPT_DELETED,
        )


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    """The on-disk identity of a file at one moment.

    ``exists`` is ``False`` for a missing/deleted file, in which case the other
    fields are zeroed. ``digest`` is a content hash so a save that rewrites the
    same bytes (or only touches the mtime) is correctly seen as *unchanged*.
    """

    exists: bool
    size: int = 0
    mtime_ns: int = 0
    digest: str = ""

    @classmethod
    def of(cls, path: str | Path) -> FileSnapshot:
        """Snapshot ``path`` now. A missing or unreadable file is ``exists=False``."""
        file_path = Path(path)
        try:
            stat = file_path.stat()
        except (OSError, ValueError):
            return cls(exists=False)
        digest = _hash_file(file_path)
        if digest is None:
            return cls(exists=False)
        return cls(
            exists=True,
            size=int(stat.st_size),
            mtime_ns=int(stat.st_mtime_ns),
            digest=digest,
        )

    def same_content_as(self, other: FileSnapshot) -> bool:
        """True when both exist and hold identical content (ignoring mtime)."""
        if not (self.exists and other.exists):
            return False
        return self.size == other.size and self.digest == other.digest


def _hash_file(path: Path, *, chunk_size: int = 65536) -> str | None:
    """Return a hex SHA-256 of ``path``'s bytes, or None if it can't be read."""
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b""):
                hasher.update(chunk)
    except (OSError, ValueError):
        return None
    return hasher.hexdigest()


def classify_change(previous: FileSnapshot, current: FileSnapshot) -> str:
    """Classify the transition from ``previous`` to ``current`` (pure).

    Returns :data:`CHANGE_NONE`, :data:`CHANGE_MODIFIED`, or
    :data:`CHANGE_DELETED`. A file that never existed and still does not is
    ``CHANGE_NONE``; a file that reappears with new content is ``CHANGE_MODIFIED``.
    """
    if not current.exists:
        return CHANGE_DELETED if previous.exists else CHANGE_NONE
    if not previous.exists:
        # The file (re)appeared where we had none — treat as a modification so
        # the UI can offer to load it rather than silently ignoring it.
        return CHANGE_MODIFIED
    return CHANGE_NONE if current.same_content_as(previous) else CHANGE_MODIFIED


class ExternalChangeWatcher:
    """Remembers the last reported snapshot of one file and reports changes.

    Construct with the file's path; :meth:`prime` records the baseline (call it
    right after opening or saving). :meth:`poll` re-snapshots and returns the
    classification relative to the last reported state, advancing the baseline
    so each external change is reported exactly once.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._last = FileSnapshot.of(self._path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def last(self) -> FileSnapshot:
        return self._last

    def prime(self, snapshot: FileSnapshot | None = None) -> None:
        """Reset the baseline to ``snapshot`` (or a fresh on-disk snapshot)."""
        self._last = snapshot if snapshot is not None else FileSnapshot.of(self._path)

    def poll(self) -> str:
        """Re-snapshot and return the change since the last reported state."""
        current = FileSnapshot.of(self._path)
        change = classify_change(self._last, current)
        if change != CHANGE_NONE:
            self._last = current
        return change


#: The two answers a person can ask to have remembered for a file format.
REMEMBER_RELOAD = "reload"
REMEMBER_KEEP = "keep"


def format_key(file_name: str) -> str:
    """The remembered-answer key for a file: its lower-case suffix, or "".

    A file format, not a file. "Do not ask me again about .docx" is a statement
    about how Word behaves, and the person making it is not thinking about one
    document.
    """
    suffix = Path(file_name).suffix.lower()
    return suffix if suffix else ""


def remembered_answer(
    file_name: str,
    *,
    always_reload: Sequence[str] = (),
    always_keep: Sequence[str] = (),
) -> str:
    """The answer this person asked to have remembered for this file format.

    ``""`` when there is none, which is the normal case and means ask. Reload
    wins a format listed in both: of the two ways to be wrong, quietly showing
    text that is no longer on disk is the one nobody notices.
    """
    key = format_key(file_name)
    if not key:
        return ""
    if key in {str(item).lower() for item in always_reload}:
        return REMEMBER_RELOAD
    if key in {str(item).lower() for item in always_keep}:
        return REMEMBER_KEEP
    return ""


def decide_reload(
    change: str,
    *,
    buffer_dirty: bool,
    watch_enabled: bool = True,
    auto_reload_when_clean: bool = False,
    prompt_on_conflict: bool = True,
    file_name: str = "",
    remembered: str = "",
) -> ReloadDecision:
    """Decide what to do for ``change`` given the buffer state and settings (pure).

    **Nothing reloads silently by default** (bad.md F5, decided 2026-09-18).
    QUILL used to replace a clean tab in place whenever the file changed, which
    is right for a text file a build regenerates and wrong for everything else:
    a ``.docx`` rewritten by Word came back as its own bytes decoded into
    replacement characters, marked clean, with nothing said. A person who
    cannot see the screen change has no cue at all that the text under the
    caret is no longer the text they were reading.

    So a change asks -- every format, dirty or clean -- and the question
    carries a "do not ask me again for this format" answer, so somebody whose
    build rewrites ``.md`` files every few seconds says so once
    (:func:`remembered_answer`). ``auto_reload_when_clean`` remains as the
    blanket escape hatch for anyone who wants the old behaviour for every
    format at once, and now defaults to off.

    * Watching off, or no change → do nothing.
    * A remembered answer for this format → take it, without asking.
    * Modified while the buffer is clean → ask (or reload, under the blanket
      setting).
    * Modified while the buffer is dirty → never overwrite silently; ask for
      reload / keep-mine / compare (when prompting is on), else stay quiet.
    * Deleted → ask; the buffer is kept so the user's text is never lost.
    """
    if not watch_enabled or change == CHANGE_NONE:
        return ReloadDecision(ReloadAction.NONE, "")

    label = f" ({file_name})" if file_name else ""

    if change == CHANGE_DELETED:
        if prompt_on_conflict:
            return ReloadDecision(
                ReloadAction.PROMPT_DELETED,
                f"The file{label} was deleted on disk. Keep your text or close.",
            )
        return ReloadDecision(ReloadAction.NONE, "")

    # change == CHANGE_MODIFIED
    if remembered == REMEMBER_RELOAD:
        return ReloadDecision(ReloadAction.RELOAD, f"Reloaded{label} from disk.")
    if remembered == REMEMBER_KEEP:
        return ReloadDecision(
            ReloadAction.KEEP_MINE,
            f"The file{label} changed on disk. Keeping what is open, as you asked.",
        )

    if buffer_dirty:
        if prompt_on_conflict:
            return ReloadDecision(
                ReloadAction.PROMPT_CONFLICT,
                f"The file{label} changed on disk and you have unsaved edits. "
                "Reload, keep mine, or compare.",
            )
        return ReloadDecision(ReloadAction.NONE, "")

    if auto_reload_when_clean:
        return ReloadDecision(ReloadAction.RELOAD, "Reloaded from disk.")
    return ReloadDecision(
        ReloadAction.PROMPT_CLEAN,
        f"The file{label} changed on disk. Reload to see the new version.",
    )
