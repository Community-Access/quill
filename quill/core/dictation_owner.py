"""One owner of Dictate Anywhere, and one microphone, at a time.

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

**One microphone** (D-11, 2026-10-13). The owner lock says who types into other
programs; it never stopped QUILL or QUILL Lite opening a second microphone with
Ctrl+F11 while QUILL Transcribe was listening, and then the same words were
written twice. :class:`MicrophoneLock` is a second lock of the same kind, taken
by *whichever* of QUILL, QUILL Lite, QUILL Transcribe and Quill Inkwell opens
the microphone, for exactly as long as it is open. The shared controller takes
it before the recogniser starts and lets go of it on every path out of a
session (:mod:`quill.core.windows_dictation.microphone_owner`); the kernel lets
go when the program exits. A second start is refused with a sentence that names
the program already listening (:func:`busy_sentence`). It is a separate lock
because QUILL Transcribe holds the owner lock for as long as it runs: one lock
for both would stop the editors dictating whenever QUILL Transcribe sat in the
tray.

wx-free.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from quill.core.ipc import _acquire_os_lock, _release_os_lock

__all__ = [
    "APPS",
    "APP_NAMES",
    "COMMANDS",
    "MICROPHONE_APPS",
    "MicrophoneLock",
    "OwnerLock",
    "Request",
    "SENDERS",
    "busy_sentence",
    "spoken_key",
    "current_owner",
    "microphone_holder",
    "send_request",
    "take_requests",
]

#: The programs that may own Dictate Anywhere.
APPS: frozenset[str] = frozenset({"transcribe", "inkwell"})
#: The programs that may hold the microphone: the two that type into other
#: programs, and the two editors' Ctrl+F11 dictation.
MICROPHONE_APPS: frozenset[str] = frozenset({"transcribe", "inkwell", "quill", "lite"})
#: Each one's name, as a refusal says it.
APP_NAMES: dict[str, str] = {
    "transcribe": "QUILL Transcribe",
    "inkwell": "Quill Inkwell",
    "quill": "QUILL",
    "lite": "QUILL Lite",
}

#: The programs that may *send* a request: the two owners, and Quill Cast and
#: Quill Radio, whose Dictate Here (dict.md D-16) has no engine of its own and
#: asks QUILL Transcribe to start in the field that has the focus.
SENDERS: frozenset[str] = APPS | frozenset({"cast", "radio"})

#: Everything a request may ask. ``toggle`` is the start/stop key; ``show``
#: brings the owner's window forward.
COMMANDS: frozenset[str] = frozenset({"toggle", "start", "stop", "show"})

_LOCK_NAME = "dictate-anywhere-owner.lock"
_OWNER_NAME = "dictate-anywhere-owner.json"
_MICROPHONE_LOCK_NAME = "dictation-microphone.lock"
_MICROPHONE_NOTE_NAME = "dictation-microphone.json"
_REQUESTS_NAME = "dictate-anywhere-requests.jsonl"
#: A request file bigger than this is somebody else's mischief, not ours.
_MAX_REQUEST_BYTES = 16_384


def _default_folder() -> Path:
    """The family's own data folder: every app signed in as this user reaches
    the same one. The test suite points this at a folder of each test's own."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / "ipc"


def _folder(folder: Path | None) -> Path:
    return folder if folder is not None else _default_folder()


class _AppLock:
    """An operating-system file lock held by one app at a time, with a note of
    which app holds it. The kernel lets go of it when its holder exits."""

    _lock_name = _LOCK_NAME
    _note_name = _OWNER_NAME
    _apps = APPS
    _what = "Dictate Anywhere owner"

    def __init__(self, app: str, *, folder: Path | None = None) -> None:
        if app not in self._apps:
            raise ValueError(f"unknown {self._what}: {app!r}")
        self.app = app
        self._folder = folder
        self._handle: IO[str] | None = None

    @property
    def held(self) -> bool:
        return self._handle is not None

    def claim(self) -> bool:
        """Take the lock. ``True`` if this app holds it now."""
        if self._handle is not None:
            return True
        folder = _folder(self._folder)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(folder / self._lock_name), os.O_RDWR | os.O_CREAT, 0o600)
            handle = os.fdopen(fd, "r+", encoding="utf-8")
        except OSError:
            return False
        if not _acquire_os_lock(handle):
            handle.close()
            return False
        self._handle = handle
        try:
            from quill.core.storage import write_json_atomic

            write_json_atomic(folder / self._note_name, self._note())
        except OSError:
            pass  # the lock, not this note, is what counts
        return True

    def _note(self) -> dict[str, object]:
        return {"app": self.app, "pid": os.getpid()}

    def release(self) -> None:
        """Let go: the next app to ask may have it."""
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
            (_folder(self._folder) / self._note_name).unlink(missing_ok=True)
        except OSError:
            pass


class OwnerLock(_AppLock):
    """The Dictate Anywhere owner lock, held by one app at a time."""


class MicrophoneLock(_AppLock):
    """The microphone, held by one app at a time while its dictation listens."""

    _lock_name = _MICROPHONE_LOCK_NAME
    _note_name = _MICROPHONE_NOTE_NAME
    _apps = MICROPHONE_APPS
    _what = "microphone holder"

    def __init__(
        self,
        app: str,
        *,
        folder: Path | None = None,
        key: str | Callable[[], str] = "",
    ) -> None:
        super().__init__(app, folder=folder)
        #: The key that stops this app's dictation, as bound right now (a
        #: callable is asked at the moment the lock is taken). Written into
        #: the note, so another program's refusal can name it.
        self._key = key

    def _note(self) -> dict[str, object]:
        try:
            key = self._key() if callable(self._key) else self._key
        except Exception:  # noqa: BLE001 - a key that cannot be read is left unnamed
            key = ""
        return {**super()._note(), "key": str(key or "")}

    def busy(self) -> str:
        """Why this app cannot have the microphone now, or ``""`` when it can."""
        if self.held:
            return ""
        holder = microphone_holder(folder=self._folder)
        if holder is None:
            return ""
        note = self._read_note()
        same = holder == self.app
        return busy_sentence(
            holder,
            asker=self.app,
            key=str(note.get("key", "") or ""),
            same_process=same and note.get("pid") == os.getpid(),
            other_window=same and note.get("pid") != os.getpid(),
        )

    def _read_note(self) -> dict[str, object]:
        try:
            data = json.loads((_folder(self._folder) / self._note_name).read_text("utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def take(self) -> str:
        """Take the microphone: ``""`` when this app has it, else the refusal."""
        if self.claim():
            return ""
        return self.busy() or busy_sentence("", asker=self.app)


def _holder(lock: _AppLock) -> str | None:
    """Who holds *lock*'s file: ``None`` when nobody does, ``""`` when somebody
    does and left no note that can be read. Asking never takes it.

    The note is only believed while the lock is really held: a note left by a
    program that crashed names nobody.
    """
    where = _folder(lock._folder)
    if lock.claim():
        # Nobody holds it. Let go at once, without disturbing the note of a
        # holder (there is none to disturb).
        handle, lock._handle = lock._handle, None
        if handle is not None:
            _release_os_lock(handle)
            handle.close()
        try:
            (where / lock._note_name).unlink(missing_ok=True)
        except OSError:
            pass
        return None
    try:
        data = json.loads((where / lock._note_name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    app = data.get("app") if isinstance(data, dict) else None
    return app if isinstance(app, str) and app in lock._apps else ""


def current_owner(*, folder: Path | None = None) -> str:
    """The app that owns Dictate Anywhere now, or ``""`` when none does."""
    return _holder(OwnerLock("transcribe", folder=folder)) or ""


def microphone_holder(*, folder: Path | None = None) -> str | None:
    """The app listening now: ``None`` when the microphone is free, ``""`` when
    something holds it and its note cannot be read."""
    return _holder(MicrophoneLock("transcribe", folder=folder))


#: How a key that is a symbol is said, the way the guides and Record Key say it.
_SPOKEN_KEYS: dict[str, str] = {
    "\\": "Backslash",
    "/": "Slash",
    ",": "Comma",
    ".": "Period",
    ";": "Semicolon",
    "'": "Apostrophe",
    "[": "Left Bracket",
    "]": "Right Bracket",
    "-": "Minus",
    "=": "Equals",
    "`": "Grave",
}


def spoken_key(key: str) -> str:
    """*key* as a screen reader user hears it named: ``Alt+Shift+\\`` is
    ``Alt+Shift+Backslash``."""
    key = key.strip()
    if not key:
        return ""
    head, plus, last = key.rpartition("+")
    if not last and plus:  # "Ctrl++": the key is the plus sign itself
        return f"{head[:-1] if head.endswith('+') else head}+Plus"
    return f"{head}{plus}{_SPOKEN_KEYS.get(last, last)}"


def busy_sentence(
    holder: str,
    *,
    asker: str,
    key: str = "",
    same_process: bool = False,
    other_window: bool = False,
) -> str:
    """What *asker* says when *holder* already has the microphone.

    It names the program that is listening, because that is the one thing the
    person cannot tell from where they are, and the key that stops it, as the
    holder has it bound right now (*key*, from the holder's note). Every
    sentence ends the same way, "then try again". Inkwell and a program that
    left no note have no key to name, so they get "Stop it there".
    """
    key = spoken_key(key)
    name = APP_NAMES.get(holder, "")
    if not name:
        return "Another program is dictating. Stop it there, then try again."
    if holder == "transcribe":
        if key:
            return f"QUILL Transcribe is listening. Press {key} to stop it, then try again."
        return "QUILL Transcribe is listening. Stop it from its tray icon, then try again."
    if holder == "inkwell" or not key:
        return f"{name} is dictating. Stop it there, then try again."
    if same_process:
        return f"{name} is already dictating. Press {key} to stop it, then try again."
    if other_window:
        return (
            f"{name} is dictating in another window. Press {key} there to stop it, then try again."
        )
    return f"{name} is dictating. Press {key} in {name} to stop it, then try again."


@dataclass(frozen=True, slots=True)
class Request:
    """One request to the owner: what to do, and which app asked."""

    command: str
    sender: str


def send_request(command: str, *, sender: str, folder: Path | None = None) -> bool:
    """Ask the owner to do *command*. ``False`` when it could not be asked."""
    if command not in COMMANDS or sender not in SENDERS:
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
        if command in COMMANDS and sender in SENDERS:
            requests.append(Request(str(command), str(sender)))
    return requests
