"""The Read-Only Guard's memory: which files somebody has locked against edits.

Both editors keep the same kind of list -- QUILL in its own data folder, QUILL
Lite in its -- and both read and write it through this module, so the two cannot
disagree about what a path *is* (rule 10: value flows both ways, and so do
fixes).

**Why paths are normalised.** The list used to be keyed on the path exactly as
the open happened to spell it. A file opened from File Explorer arrives as the
shell spells it, and the same file opened from Open Recent or the Open window
can differ in case, in a relative segment or in the slash; a guard set one way
was simply not found the other way, so a document locked yesterday opened
editable today with nothing said. Keys now go through
:meth:`quill.core.bookmarks.DocumentMemory.key_for` -- the same normalisation
bookmarks, the last caret position and document notes already use -- so every
per-file memory agrees on what one file is. Entries written by older builds are
normalised as they are read, so nothing anybody locked is lost.

**Why a failed save is reported.** Turning the guard on still works for this
session when the list cannot be written (a full disk, a locked data folder), but
"the guard will be remembered" would then be untrue. :meth:`ReadOnlyGuards.set`
returns the reason instead of swallowing it, and the editors say it.

No ``wx`` here: this is the rule both editors share, and the toolkit is theirs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = [
    "GUARD_FILENAME",
    "READ_ONLY_REFUSAL",
    "DocumentReadOnlyError",
    "ReadOnlyGuards",
    "guard_key",
    "refuse_if_guarded",
    "toggle_sentence",
]

#: The file each editor keeps its list in, inside that editor's data folder.
GUARD_FILENAME = "read-only-guards.json"

#: What a refused edit says, in both editors. One sentence with one home.
READ_ONLY_REFUSAL = "Document is read-only"

_SCHEMA_VERSION = 1


class DocumentReadOnlyError(CodedError):
    """An edit reached a document the Read-Only Guard protects.

    Raised by the editors' shared text-changing paths so that a command which
    only discovers the guard part-way through stops *before* it says it did
    anything; the command runner turns it into :data:`READ_ONLY_REFUSAL`.
    """

    code = "QUILL-CORE-READONLY-REFUSED"

    def __init__(self) -> None:
        super().__init__(READ_ONLY_REFUSAL)


def guard_key(path: object) -> str | None:
    """The normalised key for *path*, or ``None`` for an untitled document."""
    from quill.core.bookmarks import DocumentMemory

    return DocumentMemory.key_for(path)


def refuse_if_guarded(host: object) -> bool:
    """``True``, having said why, when *host*'s document is guarded.

    For the commands that write only sometimes -- a word tool's Replace, an
    answer's Use -- so the reading half of the command stays available and only
    the write is refused. *host* is either editor's window: both answer
    ``_host_read_only`` (the shared editor-host hook) and ``_announce``.
    """
    check = getattr(host, "_host_read_only", None)
    if not callable(check) or not check():
        return False
    announce = getattr(host, "_announce", None)
    if callable(announce):
        announce(READ_ONLY_REFUSAL)
    return True


def toggle_sentence(read_only: bool, *, saved: bool, reason: str = "") -> str:
    """What the toggle says: the new state, and whether it will be remembered.

    A guard that could not be written is still on for this session, so the
    first half is true either way; the second half is only said when it is not
    the usual answer, because "and it will be remembered" every time would be
    the app narrating its own plumbing.
    """
    state = "Document is read-only" if read_only else "Document is editable"
    if saved:
        return state
    because = f" ({reason})" if reason else ""
    return f"{state} for now, but it could not be remembered for next time{because}."


@dataclass
class ReadOnlyGuards:
    """The guarded paths kept in one JSON file. Load once, ask often."""

    store: Path
    _keys: set[str] | None = field(default=None, init=False, repr=False)

    def _loaded(self) -> set[str]:
        if self._keys is None:
            self._keys = self._read()
        return self._keys

    def _read(self) -> set[str]:
        from quill.core.storage import read_json

        try:
            stored = read_json(self.store, [])
        except (OSError, ValueError):
            stored = []
        # A versioned envelope {"schema_version", "paths": [...]} or the bare
        # list the first builds wrote; both are read, and both are normalised.
        items = stored.get("paths", []) if isinstance(stored, dict) else stored
        keys: set[str] = set()
        if isinstance(items, list):
            for item in items:
                key = guard_key(str(item)) if item else None
                if key:
                    keys.add(key)
        return keys

    def is_guarded(self, path: object) -> bool:
        key = guard_key(path)
        return bool(key) and key in self._loaded()

    def set(self, path: object, guarded: bool) -> str:
        """Remember (or forget) the guard for *path*.

        Returns ``""`` when the list was written, otherwise the plain reason it
        was not. The in-memory answer changes either way, so the rest of this
        session behaves as the person asked.
        """
        key = guard_key(path)
        if not key:
            return "it has no file name yet"
        keys = self._loaded()
        if guarded:
            keys.add(key)
        else:
            keys.discard(key)
        from quill.core.storage import write_json_atomic

        try:
            write_json_atomic(
                self.store, {"schema_version": _SCHEMA_VERSION, "paths": sorted(keys)}
            )
        except OSError as error:
            return error.strerror or type(error).__name__
        return ""

    def keys(self) -> frozenset[str]:
        return frozenset(self._loaded())
