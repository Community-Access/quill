"""Named sets of documents, for any family app that converts many at once.

When the person chooses more than one file for a batch conversion, the app
asks for a **set name**. The set gets its own folder inside the person's
usual output folder, one subfolder per document, and a plain-text log,
``Conversion log.txt``, that says what happened and when. This module is the
part every app shares: Scribe for Documents uses it first, and Converter and
Transcribe can take it up the same way.

* :func:`default_set_name` and :func:`name_problem` -- the name the field
  starts with ("Set of 34, Nov 24"), and the one plain sentence that says
  why a typed name cannot be used: a character Windows refuses, a name
  Windows keeps for itself (CON, NUL...), a trailing dot or space, or a
  folder that already has the name.
* :func:`create_set_folder` and :func:`member_folder_names` -- the folders.
* :class:`SetLog` -- the log: UTF-8, one line per event, each starting with
  the local time (``2026-11-24 10:42:07``), appended as events happen, so a
  set that carries on after the app was closed keeps one log.
* The log's lines (:func:`set_started_line` and the rest) and the
  :func:`progress_sentence` a list row shows ("Board packet: 12 of 34 done,
  35 percent").
* :class:`BatchSet` -- the record an app keeps for the set: its id, name,
  folder, member job ids and when it started.

Nothing here knows about any one service, and nothing here ever writes a
password, a token or a document's text: the log holds file names, times,
counts and plain reasons only.

wx-free.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = [
    "LOG_NAME",
    "MAX_NAME_LENGTH",
    "BatchSet",
    "SetLog",
    "create_set_folder",
    "default_set_name",
    "document_failed_line",
    "document_finished_line",
    "document_line",
    "duration_words",
    "member_folder_names",
    "name_problem",
    "progress_sentence",
    "retry_line",
    "set_finished_line",
    "set_started_line",
    "stopped_line",
    "timestamp",
]

#: The log's file name, in the set's folder.
LOG_NAME = "Conversion log.txt"
#: Long enough for any real name, short enough to leave room for the
#: document folders and files inside it under Windows' path limit.
MAX_NAME_LENGTH = 100

_ILLEGAL = '<>:"/\\|?*'
_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_SPACES = re.compile(r"\s+")


# ------------------------------------------------------------------ names


def default_set_name(count: int, when: datetime | None = None) -> str:
    """``Set of 34, Nov 24``: what the name field starts with."""
    moment = when or datetime.now()
    return f"Set of {count}, {moment.strftime('%b')} {moment.day}"


def _character_words(char: str) -> str:
    return "a tab or other control character" if ord(char) < 32 else char


def name_problem(name: str, root: Path | str) -> str:
    """Why *name* cannot be a set folder in *root*, in one sentence; ``""``
    when it can. Checked before anything is sent, so nothing uploads with a
    name Windows would refuse."""
    if not name.strip():
        return "Type a name for the set."
    if name != name.rstrip(" ."):
        return "A set name cannot end with a dot or a space. Remove it, or choose another name."
    if name != name.lstrip():
        return "A set name cannot start with a space. Remove it, or choose another name."
    found = [char for char in name if char in _ILLEGAL or ord(char) < 32]
    if found:
        shown = ", ".join(dict.fromkeys(_character_words(char) for char in found))
        return (
            f"A set name cannot contain {shown}. Windows does not allow "
            '< > : " / \\ | ? or * in a folder name. Choose another name.'
        )
    stem = name.split(".", 1)[0].strip().upper()
    if stem in _RESERVED:
        return (
            f"{name} is a name Windows keeps for itself, like CON and NUL, "
            "so it cannot be a folder. Choose another name."
        )
    if len(name) > MAX_NAME_LENGTH:
        return (
            f"That name is {len(name)} characters long; a set name can be up to "
            f"{MAX_NAME_LENGTH}. Choose a shorter name."
        )
    folder = Path(root) / name
    if folder.exists():
        return (
            f"A folder called {name} is already in {Path(root)}. Choose another name, "
            "so nothing in that folder is mixed up with this set."
        )
    return ""


def create_set_folder(name: str, root: Path | str) -> Path:
    """Make the set's folder. Raises :class:`ValueError` with the sentence
    from :func:`name_problem`, or :class:`FileExistsError` when another
    program made the folder between the check and now."""
    problem = name_problem(name, root)
    if problem:
        raise ValueError(problem)
    folder = Path(root) / name
    folder.parent.mkdir(parents=True, exist_ok=True)
    folder.mkdir(exist_ok=False)
    return folder


def _safe_part(name: str) -> str:
    cleaned = "".join("_" if c in _ILLEGAL or ord(c) < 32 else c for c in name)
    cleaned = _SPACES.sub(" ", cleaned).strip().rstrip(". ")
    if not cleaned:
        cleaned = "Document"
    if cleaned.split(".", 1)[0].upper() in _RESERVED:
        cleaned = f"{cleaned}_"
    return cleaned[:MAX_NAME_LENGTH].rstrip(". ")


def member_folder_names(file_names: Iterable[str]) -> list[str]:
    """One folder name per document, from its file name without the
    extension; the same name twice becomes ``Notes (2)``."""
    taken: set[str] = set()
    made: list[str] = []
    for file_name in file_names:
        leaf = str(file_name).replace("\\", "/").rsplit("/", 1)[-1]
        stem, separator, _suffix = leaf.rpartition(".")
        base = _safe_part((stem if separator else leaf) or leaf)
        candidate = base
        number = 2
        while candidate.lower() in taken:
            candidate = f"{base} ({number})"
            number += 1
        taken.add(candidate.lower())
        made.append(candidate)
    return made


# -------------------------------------------------------------------- log


def timestamp(when: float | None = None) -> str:
    """Local time as the log writes it: ``2026-11-24 10:42:07``."""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() if when is None else when))


class SetLog:
    """``Conversion log.txt`` in a set's folder: appended, never rewritten.

    Each line goes in one append-mode write, so a line is whole even when
    the app closes straight after, and an app that carries the set on after
    a restart adds to the same file.
    """

    def __init__(self, folder: Path | str, *, clock: Callable[[], float] = time.time) -> None:
        self.folder = Path(folder)
        self.path = self.folder / LOG_NAME
        self._clock = clock

    def append(self, text: str, *, when: float | None = None) -> str:
        """Add one line for *text*; returns the line written."""
        flat = " ".join(str(text).split())
        line = f"{timestamp(self._clock() if when is None else when)} {flat}\n"
        self.folder.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0)
        handle = os.open(self.path, flags, 0o644)
        try:
            os.write(handle, line.encode("utf-8"))
            os.fsync(handle)
        finally:
            os.close(handle)
        return line.rstrip("\n")

    def read(self) -> str:
        """The whole log so far (``""`` when there is none yet)."""
        try:
            return self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""


# ------------------------------------------------------------------ lines


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def duration_words(seconds: float) -> str:
    """``2 minutes 5 seconds``, ``1 hour 3 minutes``, ``under a second``."""
    total = int(round(max(0.0, seconds)))
    if total < 1:
        return "under a second"
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    parts: list[str] = []
    if hours:
        parts.append(_plural(hours, "hour"))
    if minutes:
        parts.append(_plural(minutes, "minute"))
    if secs and not hours:
        parts.append(_plural(secs, "second"))
    return " ".join(parts)


def _names(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def set_started_line(name: str, count: int, formats: str, *, noun: str = "document") -> str:
    """The first line: the set, how many, and what was asked for."""
    return f"Set {name} started: {_plural(count, noun)}, formats {formats}."


def document_line(event: str, file_name: str) -> str:
    """``Queued: Notes.pdf`` (and Uploaded, Conversion started...)."""
    return f"{event}: {file_name}."


def document_finished_line(file_name: str, seconds: float | None) -> str:
    took = f" in {duration_words(seconds)}" if seconds is not None else ""
    return f"Finished: {file_name}{took}."


def document_failed_line(file_name: str, reason: str) -> str:
    """A failure, with its reason in plain words (never an exception's text)."""
    said = " ".join(reason.split()).rstrip(".") or "no reason was given"
    return f"Failed: {file_name}. Reason: {said}."


def retry_line(names: list[str]) -> str:
    return f"Trying again: {_names(names)}."


def stopped_line(names: list[str], app_name: str) -> str:
    return f"{app_name} stopped waiting for {_names(names)}."


def set_finished_line(
    name: str,
    *,
    done: int,
    failed_names: list[str],
    seconds: float,
    retry_hint: str,
) -> str:
    """The last line: counts, the total time, what failed and how to retry."""
    took = duration_words(seconds)
    head = f"Set {name} finished in {took}: {done} done, {len(failed_names)} failed."
    if not failed_names:
        return head
    return f"{head} Not made: {_names(failed_names)}. {retry_hint}"


def progress_sentence(name: str, *, done: int, failed: int, total: int) -> str:
    """A set's row: ``Board packet: 12 of 34 done, 35 percent``, with
    ``, 1 failed`` when any failed. The percent counts the documents that
    have finished, made or not."""
    finished = min(total, done + failed)
    percent = (finished * 100) // total if total else 0
    sentence = f"{name}: {done} of {total} done, {percent} percent"
    if failed:
        sentence += f", {failed} failed"
    return sentence


# ----------------------------------------------------------------- record


@dataclass(slots=True)
class BatchSet:
    """A set as an app keeps it, beside its jobs. Fields a newer app adds are
    kept in :attr:`extra` and written back unchanged."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    folder: str = ""
    members: list[str] = field(default_factory=list)
    started: float = field(default_factory=time.time)
    #: When the set finished (0 while it is still under way, and again after
    #: Retry Failed sends some of it again).
    finished: float = 0.0
    app: str = ""
    formats: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def log(self, *, clock: Callable[[], float] = time.time) -> SetLog:
        return SetLog(self.folder, clock=clock)

    def to_dict(self) -> dict[str, Any]:
        body = dict(self.extra)
        body.update({
            "id": self.id,
            "name": self.name,
            "folder": self.folder,
            "members": list(self.members),
            "started": self.started,
            "finished": self.finished,
            "app": self.app,
            "formats": list(self.formats),
        })
        return body

    @classmethod
    def from_mapping(cls, data: Any) -> BatchSet | None:
        if not isinstance(data, Mapping) or not data.get("id"):
            return None
        known = {"id", "name", "folder", "members", "started", "finished", "app", "formats"}
        try:
            return cls(
                id=str(data["id"]),
                name=str(data.get("name", "")),
                folder=str(data.get("folder", "")),
                members=[str(m) for m in data.get("members", []) or []],
                started=float(data.get("started", 0.0) or 0.0),
                finished=float(data.get("finished", 0.0) or 0.0),
                app=str(data.get("app", "")),
                formats=[str(f) for f in data.get("formats", []) or []],
                extra={k: v for k, v in data.items() if k not in known},
            )
        except (TypeError, ValueError):
            return None
