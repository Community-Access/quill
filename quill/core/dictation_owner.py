"""One owner of Dictate Anywhere at a time: QUILL Transcribe first, then Inkwell.

QUILL Transcribe's spec (section 10.3): one microphone session and one program
typing into other programs, per person signed in to Windows. Two apps can type
what you say into another program -- QUILL Transcribe, whose whole job it is,
and Quill Inkwell, which has hosted Dictate Anywhere since 2026-10-05 -- and
they must never both be listening, or both hold the same key, or type the same
words twice.

This is the 1.0 arrangement, the spec's fallback rather than its full IPC
service, and it is deliberately small:

* **An owner lock.** :class:`OwnerLock` is an operating-system file lock in the
  family's own data folder, so only programs running as the same Windows user
  can reach it, and the kernel lets go of it when its holder exits for any
  reason. QUILL Transcribe holds it for as long as it runs. Inkwell takes it
  only for the length of one dictation session, and only when nobody else has
  it.
* **Inkwell defers.** When QUILL Transcribe holds the lock, Inkwell's Dictate
  Anywhere key does not start Inkwell's own microphone: it passes the request
  on (:func:`send_request`) and QUILL Transcribe answers it.
* **Requests, never words.** A request is one word from :data:`COMMANDS` and
  the name of the app that sent it. No transcript, no audio and no settings
  value ever goes through it; anything else in the file is ignored.

wx-free.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from quill.core.ipc import _acquire_os_lock, _release_os_lock

__all__ = [
    "APPS",
    "COMMANDS",
    "OwnerLock",
    "Request",
    "current_owner",
    "send_request",
    "take_requests",
]

#: The programs that may own Dictate Anywhere.
APPS: frozenset[str] = frozenset({"transcribe", "inkwell"})

#: Everything a request may ask. ``toggle`` is the start/stop key; ``show``
#: brings the owner's window forward.
COMMANDS: frozenset[str] = frozenset({"toggle", "start", "stop", "show"})

_LOCK_NAME = "dictate-anywhere-owner.lock"
_OWNER_NAME = "dictate-anywhere-owner.json"
_REQUESTS_NAME = "dictate-anywhere-requests.jsonl"
#: A request file bigger than this is somebody else's mischief, not ours.
_MAX_REQUEST_BYTES = 16_384


def _folder(folder: Path | None) -> Path:
    if folder is not None:
        return folder
    from quill.core.paths import app_data_dir

    return app_data_dir() / "ipc"


class OwnerLock:
    """The Dictate Anywhere owner lock, held by one app at a time."""

    def __init__(self, app: str, *, folder: Path | None = None) -> None:
        if app not in APPS:
            raise ValueError(f"unknown Dictate Anywhere owner: {app!r}")
        self.app = app
        self._folder = folder
        self._handle: IO[str] | None = None

    @property
    def held(self) -> bool:
        return self._handle is not None

    def claim(self) -> bool:
        """Take the lock. ``True`` if this app owns Dictate Anywhere now."""
        if self._handle is not None:
            return True
        folder = _folder(self._folder)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(folder / _LOCK_NAME), os.O_RDWR | os.O_CREAT, 0o600)
            handle = os.fdopen(fd, "r+", encoding="utf-8")
        except OSError:
            return False
        if not _acquire_os_lock(handle):
            handle.close()
            return False
        self._handle = handle
        try:
            from quill.core.storage import write_json_atomic

            write_json_atomic(folder / _OWNER_NAME, {"app": self.app, "pid": os.getpid()})
        except OSError:
            pass  # the lock, not this note, is what counts
        return True

    def release(self) -> None:
        """Let go: the next app to ask may own it."""
        handle, self._handle = self._handle, None
        if handle is None:
            return
        try:
            _release_os_lock(handle)
        finally:
            try:
                handle.close()
            except OSError:
                pass
        try:
            (_folder(self._folder) / _OWNER_NAME).unlink(missing_ok=True)
        except OSError:
            pass


def current_owner(*, folder: Path | None = None) -> str:
    """The app that owns Dictate Anywhere now, or ``""`` when none does.

    The note of who holds the lock is only believed while the lock is really
    held: a note left by a program that crashed names nobody.
    """
    where = _folder(folder)
    probe = OwnerLock("transcribe", folder=where)
    if probe.claim():
        # Nobody holds it. Let go at once, without disturbing the note of a
        # holder (there is none to disturb).
        handle, probe._handle = probe._handle, None
        if handle is not None:
            _release_os_lock(handle)
            handle.close()
        try:
            (where / _OWNER_NAME).unlink(missing_ok=True)
        except OSError:
            pass
        return ""
    try:
        data = json.loads((where / _OWNER_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    app = data.get("app") if isinstance(data, dict) else None
    return app if isinstance(app, str) and app in APPS else ""


@dataclass(frozen=True, slots=True)
class Request:
    """One request to the owner: what to do, and which app asked."""

    command: str
    sender: str


def send_request(command: str, *, sender: str, folder: Path | None = None) -> bool:
    """Ask the owner to do *command*. ``False`` when it could not be asked."""
    if command not in COMMANDS or sender not in APPS:
        return False
    where = _folder(folder)
    try:
        where.mkdir(parents=True, exist_ok=True)
        with (where / _REQUESTS_NAME).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"command": command, "sender": sender}) + "\n")
    except OSError:
        return False
    return True


def take_requests(*, folder: Path | None = None) -> list[Request]:
    """Every waiting request that is well formed, oldest first; the file is emptied."""
    path = _folder(folder) / _REQUESTS_NAME
    try:
        if path.stat().st_size > _MAX_REQUEST_BYTES:
            path.unlink(missing_ok=True)
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        path.unlink(missing_ok=True)
    except OSError:
        return []
    requests: list[Request] = []
    for line in lines:
        try:
            raw = json.loads(line)
        except ValueError:
            continue
        if not isinstance(raw, dict):
            continue
        command, sender = raw.get("command"), raw.get("sender")
        if command in COMMANDS and sender in APPS:
            requests.append(Request(str(command), str(sender)))
    return requests
