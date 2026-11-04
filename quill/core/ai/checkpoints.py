"""A private safety net under every agent turn; Undo Last Turn (code.md 4.5) -- wx-free.

A turn can touch many files, so one Control Z in one document is not enough.
Before a turn first changes anything -- an accepted review, or a command it
runs -- QUILL notes every visible file in the project; afterwards it notes
them again. **Undo Last Turn** puts back every file that turn changed and
removes every file it created, across the whole project, then says what it
did.

**It refuses rather than loses work.** When the person has edited one of
those files since the turn, undo stops and names it: "cli.py has changed
since the agent's turn. Undo would lose your edits."

**The person's repository is untouched.** The store is content-addressed
copies in QUILL's own app data (the ``restore_points.py`` approach, decision
5), keyed by a hash of the project's path. It never touches ``.git``, works
the same with or without git, and is never sent anywhere. Only the last
:data:`KEEP_TURNS` turns per project are kept; older copies are swept.

Secret files are never copied: the walk is :meth:`Project.files`, which hides
them, so a checkpoint can never become a second home for a key.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.ai.change_set import write_bytes_atomic
from quill.core.ai.project import Project
from quill.core.error_codes import CodedError
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "KEEP_TURNS",
    "CheckpointError",
    "CheckpointStore",
    "TurnRecord",
    "UndoReport",
]

#: Turns kept per project, newest last.
KEEP_TURNS = 10
#: A file bigger than this is not copied (and so is never undone).
MAX_COPY_BYTES = 5 * 1024 * 1024
#: The most files one snapshot covers.
MAX_FILES = 5000

Snapshot = dict[str, str]  # project-relative path -> sha256 of its bytes


class CheckpointError(CodedError):
    """A checkpoint could not be written or read."""

    code = "QUILL-AI-CHECKPOINT-FAILED"


@dataclass
class TurnRecord:
    number: int
    started: float
    before: Snapshot = field(default_factory=dict)
    after: Snapshot = field(default_factory=dict)

    def changed(self) -> list[str]:
        """Every path this turn changed, created or removed."""
        paths = set(self.before) | set(self.after)
        return sorted(p for p in paths if self.before.get(p) != self.after.get(p))

    def to_json(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "started": self.started,
            "before": self.before,
            "after": self.after,
        }

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> TurnRecord:
        return cls(
            number=int(raw.get("number", 0)),
            started=float(raw.get("started", 0.0)),
            before={str(k): str(v) for k, v in dict(raw.get("before", {})).items()},
            after={str(k): str(v) for k, v in dict(raw.get("after", {})).items()},
        )


@dataclass(frozen=True, slots=True)
class UndoReport:
    ok: bool
    sentence: str
    restored: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    edited_since: tuple[str, ...] = ()


class CheckpointStore:
    """The checkpoints of one project, in ``<data>/ai/checkpoints/<project key>``."""

    def __init__(self, project: Project, data_dir: Path) -> None:
        self._project = project
        self._dir = Path(data_dir) / "ai" / "checkpoints" / project.key
        self._objects = self._dir / "objects"
        self._index = self._dir / "turns.json"
        self._hash_cache: dict[str, tuple[int, int, str]] = {}
        self._open: TurnRecord | None = None

    @property
    def folder(self) -> Path:
        return self._dir

    # -- hashing and copying -------------------------------------------------- #

    def _hash(self, rel: str, path: Path) -> str | None:
        try:
            stat = path.stat()
        except OSError:
            return None
        if stat.st_size > MAX_COPY_BYTES:
            return None
        cached = self._hash_cache.get(rel)
        if cached and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
            return cached[2]
        try:
            data = path.read_bytes()
        except OSError:
            return None
        digest = hashlib.sha256(data).hexdigest()
        stored = self._objects / digest
        if not stored.exists():
            self._objects.mkdir(parents=True, exist_ok=True)
            temp = stored.with_suffix(".tmp")
            temp.write_bytes(data)
            temp.replace(stored)
        self._hash_cache[rel] = (stat.st_mtime_ns, stat.st_size, digest)
        return digest

    def snapshot(self) -> Snapshot:
        """Every visible file's content hash, copying any new content into the store."""
        found: Snapshot = {}
        for rel, path in self._project.files(MAX_FILES):
            digest = self._hash(rel, path)
            if digest is not None:
                found[rel] = digest
        return found

    # -- turns ------------------------------------------------------------------ #

    def turns(self) -> list[TurnRecord]:
        raw = read_json(self._index, default={})
        items = raw.get("turns", []) if isinstance(raw, dict) else []
        return [TurnRecord.from_json(item) for item in items if isinstance(item, dict)]

    def _save(self, turns: list[TurnRecord]) -> None:
        kept = turns[-KEEP_TURNS:]
        try:
            write_json_atomic(self._index, {"version": 1, "turns": [t.to_json() for t in kept]})
        except OSError as error:
            raise CheckpointError(f"The checkpoint could not be saved: {error}") from error
        self._sweep(kept)

    def _sweep(self, kept: list[TurnRecord]) -> None:
        live = {d for t in kept for d in (*t.before.values(), *t.after.values())}
        if not self._objects.is_dir():
            return
        for stored in self._objects.iterdir():
            if stored.name not in live:
                try:
                    stored.unlink()
                except OSError:
                    pass

    def ensure_turn(self) -> TurnRecord:
        """Start the current turn's record, once, just before its first change."""
        if self._open is None:
            turns = self.turns()
            number = (turns[-1].number + 1) if turns else 1
            before = self.snapshot()
            self._open = TurnRecord(
                number=number, started=time.time(), before=before, after=dict(before)
            )
        return self._open

    @property
    def open_turn(self) -> TurnRecord | None:
        return self._open

    def record_after(self) -> None:
        """Note the project as it is now, as the open turn's result."""
        if self._open is None:
            return
        self._open.after = self.snapshot()
        turns = [t for t in self.turns() if t.number != self._open.number]
        if self._open.changed():
            self._save([*turns, self._open])

    def close_turn(self) -> TurnRecord | None:
        """End the turn: the next change starts a new one."""
        turn = self._open
        if turn is not None:
            self.record_after()
        self._open = None
        return turn if turn is not None and turn.changed() else None

    # -- undo -------------------------------------------------------------------- #

    def last_turn(self) -> TurnRecord | None:
        turns = self.turns()
        return turns[-1] if turns else None

    def undo_last(self) -> UndoReport:
        """Put back everything the last recorded turn changed, or say why not."""
        if self._open is not None:
            self.close_turn()
        turns = self.turns()
        if not turns:
            return UndoReport(False, "There is no agent turn to undo in this project.")
        turn = turns[-1]
        changed = turn.changed()
        edited: list[str] = []
        for rel in changed:
            path = self._project.root / rel
            now = self._current_hash(path)
            if now != turn.after.get(rel):
                edited.append(rel)
        if edited:
            names = ", ".join(edited[:3]) + (" and others" if len(edited) > 3 else "")
            verb = "has" if len(edited) == 1 else "have"
            return UndoReport(
                False,
                f"{names} {verb} changed since the agent's turn. Undo would lose your edits.",
                edited_since=tuple(edited),
            )
        restored: list[str] = []
        removed: list[str] = []
        for rel in changed:
            path = self._project.resolve(rel)
            digest = turn.before.get(rel)
            if digest is None:
                path.unlink(missing_ok=True)
                removed.append(rel)
                continue
            write_bytes_atomic(path, (self._objects / digest).read_bytes())
            restored.append(rel)
        self._hash_cache.clear()
        self._save(turns[:-1])
        return UndoReport(
            True, _undo_sentence(turn.number, restored, removed), tuple(restored), tuple(removed)
        )

    def before_text(self, turn: TurnRecord, rel: str) -> str:
        """A file as it was before *turn*, for the comparison the refusal offers."""
        digest = turn.before.get(rel)
        if digest is None:
            return ""
        return (self._objects / digest).read_bytes().decode("utf-8", errors="replace")

    @staticmethod
    def _current_hash(path: Path) -> str | None:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return None


def _undo_sentence(number: int, restored: list[str], removed: list[str]) -> str:
    parts: list[str] = []
    if restored:
        names = " and ".join(restored) if len(restored) <= 2 else f"{len(restored)} files"
        parts.append(
            f"{names} is back as it was" if len(restored) == 1 else f"{names} are back as they were"
        )
    if removed:
        names = " and ".join(removed) if len(removed) <= 2 else f"{len(removed)} new files"
        parts.append(f"removed {names}")
    body = "; ".join(parts) if parts else "nothing needed changing"
    return f"Undid turn {number}. {body[0].upper()}{body[1:]}."
