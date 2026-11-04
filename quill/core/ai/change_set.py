"""A turn's proposed edits, and the one place they reach the disk (code.md 4.2, 5.4).

When an agent edits, creates, deletes or renames a project file, nothing is
written. The proposal joins the turn's :class:`ChangeSet`, which is what the
Review Changes window shows: one row per file, one change at a time. The
person accepts or rejects each change, or a file at once, and only then does
:meth:`ChangeSet.apply` write -- every accepted change together, or none of
them.

**All or nothing.** Every new text is written to a temporary file beside its
target first; only when all of those exist are they moved into place, and a
failure part-way puts every file already replaced back as it was. A rejected
change never reaches the disk; a test proves it (GATE-PROJECT-REVIEW).

**The model is told the truth.** :meth:`ChangeSet.outcome_text` says what
happened in the person's terms -- "Accepted 2 of 3 changes in cli.py; the
person rejected the change at line 40" -- and that is what the engine reads.

Line endings are kept: a file that arrived with CRLF is written back with
CRLF. Text is UTF-8. wx-free.
"""

from __future__ import annotations

import difflib
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = [
    "ApplyReport",
    "ChangeKind",
    "ChangeSet",
    "ChangeSetError",
    "FileChange",
    "Hunk",
    "write_bytes_atomic",
    "write_text_atomic",
]


class ChangeSetError(CodedError):
    """A proposed change could not be recorded or written."""

    code = "QUILL-AI-CHANGESET-FAILED"


class ChangeKind(StrEnum):
    EDIT = "edit"
    CREATE = "create"
    DELETE = "delete"
    RENAME = "rename"


@dataclass
class Hunk:
    """One change inside a file: lines ``old_start`` to ``old_start + len(old) - 1``."""

    old_start: int  # 1-based line in the original
    old: list[str]
    new: list[str]
    accepted: bool = True

    @property
    def old_end(self) -> int:
        return self.old_start + max(len(self.old), 1) - 1


@dataclass
class FileChange:
    """Everything proposed for one file in this turn."""

    path: str
    kind: ChangeKind
    original: str = ""  # "" for a new file
    proposed: str = ""  # "" for a deletion
    new_path: str = ""  # a rename's destination
    reason: str = ""
    hunks: list[Hunk] = field(default_factory=list)
    #: For a create, delete or rename: the whole file's yes or no.
    accepted: bool = True
    #: The original's line ending, kept when it is written back.
    newline: str = "\n"

    @property
    def change_count(self) -> int:
        return len(self.hunks) if self.kind is ChangeKind.EDIT else 1

    @property
    def accepted_count(self) -> int:
        if self.kind is ChangeKind.EDIT:
            return sum(1 for hunk in self.hunks if hunk.accepted)
        return 1 if self.accepted else 0

    def set_all(self, accepted: bool) -> None:
        self.accepted = accepted
        for hunk in self.hunks:
            hunk.accepted = accepted

    def result_text(self) -> str:
        """The file as it would be with only the accepted hunks."""
        if self.kind is not ChangeKind.EDIT:
            return self.proposed
        lines = self.original.split("\n")
        out: list[str] = []
        cursor = 0
        for hunk in self.hunks:
            start = hunk.old_start - 1
            out.extend(lines[cursor:start])
            out.extend(hunk.new if hunk.accepted else hunk.old)
            cursor = start + len(hunk.old)
        out.extend(lines[cursor:])
        return "\n".join(out)

    def row_text(self) -> str:
        """The review list's sentence for this file."""
        if self.kind is ChangeKind.CREATE:
            count = self.proposed.count("\n") + (0 if self.proposed.endswith("\n") else 1)
            what = f"new file, {count} line{'s' if count != 1 else ''}"
        elif self.kind is ChangeKind.DELETE:
            what = "deleted"
        elif self.kind is ChangeKind.RENAME:
            what = f"renamed to {self.new_path}"
        else:
            n = self.change_count
            what = f"changed, {n} change{'s' if n != 1 else ''}"
        taken = self.accepted_count
        if taken == self.change_count:
            state = "taken"
        elif taken == 0:
            state = "not taken"
        else:
            state = f"{taken} of {self.change_count} taken"
        return f"{self.path}, {what}, {state}"


def _hunks(original: str, proposed: str) -> list[Hunk]:
    old = original.split("\n")
    new = proposed.split("\n")
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    hunks: list[Hunk] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        hunks.append(Hunk(old_start=i1 + 1, old=old[i1:i2], new=new[j1:j2]))
    return hunks


def _newline_of(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def write_text_atomic(path: Path, text: str) -> None:
    """Write *text* (UTF-8, line endings as given) to *path* atomically."""
    write_bytes_atomic(path, text.encode("utf-8"))


def write_bytes_atomic(path: Path, data: bytes) -> None:
    """Write *data* to *path* through a temporary file and a replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".quill-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


@dataclass(frozen=True, slots=True)
class ApplyReport:
    written: tuple[str, ...] = ()
    created: tuple[str, ...] = ()
    deleted: tuple[str, ...] = ()
    renamed: tuple[tuple[str, str], ...] = ()
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def touched(self) -> tuple[str, ...]:
        moved = tuple(p for pair in self.renamed for p in pair)
        return (*self.written, *self.created, *self.deleted, *moved)


class ChangeSet:
    """The edits proposed in one turn, in the order they were first proposed."""

    def __init__(self) -> None:
        self._files: dict[str, FileChange] = {}

    # -- proposing ------------------------------------------------------------ #

    @property
    def files(self) -> list[FileChange]:
        return list(self._files.values())

    @property
    def pending(self) -> bool:
        return bool(self._files)

    def get(self, path: str) -> FileChange | None:
        return self._files.get(path)

    def current_text(self, path: str, read: Callable[[str], str]) -> str:
        """What the agent should edit against: its own proposal, or the file."""
        change = self._files.get(path)
        if change is not None and change.kind in (ChangeKind.EDIT, ChangeKind.CREATE):
            return change.proposed
        return read(path)

    def propose_edit(self, path: str, original: str, proposed: str, reason: str = "") -> FileChange:
        """Record a new version of *path*. A second edit builds on the first."""
        existing = self._files.get(path)
        if existing is not None and existing.kind is ChangeKind.CREATE:
            existing.proposed = proposed
            existing.reason = reason or existing.reason
            return existing
        if existing is not None and existing.kind is ChangeKind.EDIT:
            original = existing.original
        if existing is not None and existing.kind in (ChangeKind.DELETE, ChangeKind.RENAME):
            raise ChangeSetError(f"{path} is already proposed for {existing.kind.value}.")
        newline = _newline_of(original)
        base = original.replace("\r\n", "\n")
        target = proposed.replace("\r\n", "\n")
        if base == target:
            raise ChangeSetError(f"That leaves {path} exactly as it is.")
        change = FileChange(
            path=path,
            kind=ChangeKind.EDIT,
            original=base,
            proposed=target,
            reason=reason or (existing.reason if existing else ""),
            hunks=_hunks(base, target),
            newline=newline,
        )
        self._files[path] = change
        return change

    def propose_create(self, path: str, text: str, reason: str = "") -> FileChange:
        if path in self._files and self._files[path].kind is not ChangeKind.CREATE:
            raise ChangeSetError(f"{path} already has a change proposed.")
        change = FileChange(path=path, kind=ChangeKind.CREATE, proposed=text, reason=reason)
        self._files[path] = change
        return change

    def propose_delete(self, path: str, original: str, reason: str = "") -> FileChange:
        if path in self._files:
            raise ChangeSetError(f"{path} already has a change proposed.")
        change = FileChange(path=path, kind=ChangeKind.DELETE, original=original, reason=reason)
        self._files[path] = change
        return change

    def propose_rename(self, path: str, new_path: str, reason: str = "") -> FileChange:
        if path in self._files or new_path in self._files:
            raise ChangeSetError(f"{path} already has a change proposed.")
        change = FileChange(path=path, kind=ChangeKind.RENAME, new_path=new_path, reason=reason)
        self._files[path] = change
        return change

    def clear(self) -> None:
        self._files.clear()

    # -- the person's answers ------------------------------------------------- #

    def accept_all(self) -> None:
        for change in self._files.values():
            change.set_all(True)

    def reject_all(self) -> None:
        for change in self._files.values():
            change.set_all(False)

    # -- writing --------------------------------------------------------------- #

    def apply(self, resolve: Callable[[str], Path]) -> ApplyReport:
        """Write every accepted change together, or none; then forget the set.

        *resolve* turns a project path into an absolute one and refuses one
        outside the project (``Project.resolve``), so even a hand-built change
        set cannot write elsewhere.
        """
        staged: list[tuple[Path, str]] = []  # (target, new text) for writes
        deletes: list[Path] = []
        renames: list[tuple[Path, Path]] = []
        written: list[str] = []
        created: list[str] = []
        deleted: list[str] = []
        renamed: list[tuple[str, str]] = []
        try:
            for change in self._files.values():
                if change.accepted_count == 0:
                    continue
                target = resolve(change.path)
                if change.kind is ChangeKind.EDIT:
                    staged.append((target, change.result_text().replace("\n", change.newline)))
                    written.append(change.path)
                elif change.kind is ChangeKind.CREATE:
                    if target.exists():
                        raise ChangeSetError(f"{change.path} exists now, so it was not created.")
                    staged.append((target, change.proposed))
                    created.append(change.path)
                elif change.kind is ChangeKind.DELETE:
                    deletes.append(target)
                    deleted.append(change.path)
                else:
                    destination = resolve(change.new_path)
                    if destination.exists():
                        raise ChangeSetError(f"{change.new_path} already exists.")
                    renames.append((target, destination))
                    renamed.append((change.path, change.new_path))
        except (ChangeSetError, CodedError, OSError) as error:
            return ApplyReport(error=str(error))
        failure = _commit(staged, deletes, renames)
        if failure:
            return ApplyReport(error=failure)
        self.clear()
        return ApplyReport(tuple(written), tuple(created), tuple(deleted), tuple(renamed))

    # -- telling the model ------------------------------------------------------ #

    def outcome_text(self) -> str:
        """What the person decided, file by file, for the engine to read."""
        parts: list[str] = []
        for change in self._files.values():
            parts.append(_outcome_for(change))
        return " ".join(parts) if parts else "There were no changes to review."


def _outcome_for(change: FileChange) -> str:
    if change.kind is not ChangeKind.EDIT:
        verb = {
            ChangeKind.CREATE: "creating",
            ChangeKind.DELETE: "deleting",
            ChangeKind.RENAME: "renaming",
        }[change.kind]
        if change.accepted:
            return f"The person accepted {verb} {change.path}."
        return f"The person rejected {verb} {change.path}; it was not done."
    total = change.change_count
    taken = change.accepted_count
    if taken == total:
        return f"Accepted all {total} change{'s' if total != 1 else ''} in {change.path}."
    if taken == 0:
        return f"Rejected every change in {change.path}; the file is unchanged."
    rejected = [f"line {hunk.old_start}" for hunk in change.hunks if not hunk.accepted]
    return (
        f"Accepted {taken} of {total} changes in {change.path}; the person rejected "
        f"the change{'s' if len(rejected) != 1 else ''} at {', '.join(rejected)}."
    )


def _commit(
    staged: list[tuple[Path, str]], deletes: list[Path], renames: list[tuple[Path, Path]]
) -> str:
    """Write everything or nothing. Returns "" or the reason it was all put back."""
    temps: list[tuple[Path, Path]] = []
    backups: list[tuple[Path, bytes | None]] = []
    moved: list[tuple[Path, Path]] = []
    try:
        for target, text in staged:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=".quill-", suffix=".tmp", dir=str(target.parent)
            )
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
            temps.append((Path(temp_name), target))
        for temp_path, target in temps:
            backups.append((target, target.read_bytes() if target.exists() else None))
            os.replace(temp_path, target)
        for target in deletes:
            backups.append((target, target.read_bytes()))
            target.unlink()
        for source, destination in renames:
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, destination)
            moved.append((source, destination))
    except OSError as error:
        for source, destination in reversed(moved):
            try:
                os.replace(destination, source)
            except OSError:
                pass
        for target, data in reversed(backups):
            try:
                if data is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_bytes(data)
            except OSError:
                pass
        for leftover, _target in temps:
            try:
                leftover.unlink(missing_ok=True)
            except OSError:
                pass
        return f"Nothing was written, because {error.strerror or error}."
    return ""
