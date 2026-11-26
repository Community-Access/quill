"""What to say when a command fails (bad.md P0.9).

"Command failed: file.save" was QUILL's whole report. It named the command the
person had just pressed -- which they knew -- and said nothing about the fault,
so a full disk, a read-only folder, a character the encoding cannot hold and a
bug inside a Quillin all produced the same sentence. A listener cannot open a
log to find the rest, so that sentence was the end of the road.

The exception's own words are usually the only clue there is. They are not
beautiful, and they are enormously better than nothing.

wx-free so both editors can say the same thing, and directly tested.

FUX-16 ("turn a problem into a recoverable next step") added the other half.
The exception's words are a clue for whoever fixes the fault, and they belong
in the details a person can copy, not in the sentence they hear first.
:func:`plain_failure` says what kind of thing went wrong in plain words, and
tells an unsupported feature, a denied permission, a missing part and a passing
failure apart, so a box can offer the one next step that fits.
:func:`failure_details` is the copyable text: versions and the error, redacted,
and never the document.
"""

from __future__ import annotations

import errno
import platform
from dataclasses import dataclass

from quill.core.error_codes import USER_HINTS, CodedError

__all__ = [
    "DENIED",
    "DEVICE",
    "DISK_FULL",
    "MISSING",
    "OFFLINE",
    "OTHER",
    "SIGNED_OUT",
    "UNAVAILABLE",
    "UNSUPPORTED",
    "FailureWords",
    "describe_command_failure",
    "failure_details",
    "plain_failure",
    "save_failure_sentence",
]

#: What kind of failure it was. Stable ids for tests and logs; the sentences
#: are for people.
DISK_FULL = "disk_full"
DENIED = "denied"
MISSING = "missing"
DEVICE = "device"
OFFLINE = "offline"
SIGNED_OUT = "signed_out"
UNAVAILABLE = "unavailable"
UNSUPPORTED = "unsupported"
OTHER = "other"

_SENTENCES: dict[str, str] = {
    DISK_FULL: "The disk is full.",
    DENIED: (
        "Windows did not allow it: the file may be open in another program, "
        "or the folder may be protected."
    ),
    MISSING: "The file or folder is not there any more.",
    DEVICE: "The device is not connected or not ready.",
    OFFLINE: "The connection failed or timed out.",
    SIGNED_OUT: "The sign-in was not accepted, or it has expired.",
    UNAVAILABLE: "A part this needs is not installed.",
    UNSUPPORTED: "This file or request is not one it can handle.",
    OTHER: "Something unexpected went wrong. Copy Details has the technical text.",
}

#: Windows error numbers that arrive with an unhelpful ``errno``.
_WIN_DISK_FULL = {112, 39}
#: Access denied, sharing and lock violations, write protected.
_WIN_DENIED = {5, 32, 33, 19}
_WIN_MISSING = {2, 3, 15, 53, 67}
#: Device not ready, device not connected.
_WIN_DEVICE = {21, 1167}

#: Class names from libraries core does not import (requests, httpx, urllib3,
#: PyGithub), matched by name so core stays free of them.
_OFFLINE_NAMES = ("ConnectionError", "Timeout", "URLError")


@dataclass(frozen=True, slots=True)
class FailureWords:
    """What went wrong, in words a person can act on."""

    kind: str
    #: One plain sentence. Never the exception's raw text, unless a QUILL
    #: raiser wrote it for people (a coded error's own message).
    reason: str
    #: Trying the same thing again, unchanged, may well work.
    transient: bool


def _status(error: BaseException) -> int:
    for owner in (error, getattr(error, "response", None)):
        for name in ("status", "status_code"):
            value = getattr(owner, name, None)
            if isinstance(value, int) and 100 <= value <= 599:
                return value
    return 0


def _os_kind(error: OSError) -> str:
    code = getattr(error, "errno", None)
    win = getattr(error, "winerror", None)
    if code in (errno.ENOSPC, getattr(errno, "EDQUOT", -1)) or win in _WIN_DISK_FULL:
        return DISK_FULL
    if (
        isinstance(error, PermissionError)
        or code in (errno.EACCES, errno.EPERM, errno.EROFS)
        or win in _WIN_DENIED
    ):
        return DENIED
    if code in (errno.ENODEV, errno.ENXIO) or win in _WIN_DEVICE:
        return DEVICE
    if isinstance(error, (ConnectionError, TimeoutError)) or code in (
        errno.ETIMEDOUT,
        errno.ECONNREFUSED,
        errno.ECONNRESET,
        errno.ENETUNREACH,
        errno.EHOSTUNREACH,
    ):
        return OFFLINE
    if isinstance(error, FileNotFoundError) or code == errno.ENOENT or win in _WIN_MISSING:
        return MISSING
    return OTHER


def _kind(error: BaseException) -> str:
    status = _status(error)
    if status == 401:
        return SIGNED_OUT
    if status == 403:
        return DENIED
    if status == 429 or status >= 500:
        return OFFLINE
    if any(part in type(error).__name__ for part in _OFFLINE_NAMES):
        return OFFLINE
    if isinstance(error, OSError):
        return _os_kind(error)
    if isinstance(error, ImportError):
        return UNAVAILABLE
    if isinstance(error, (NotImplementedError, UnicodeDecodeError)):
        return UNSUPPORTED
    return OTHER


def _coded_text(error: CodedError) -> str:
    """A coded error's own message without the bracketed code, plus its hint."""
    message = str(error.args[0]).strip() if error.args else ""
    hint = error.user_hint.strip() or USER_HINTS.get(error.code, "")
    if hint and hint not in message:
        message = f"{message.rstrip()} {hint}".strip()
    return message


def plain_failure(error: BaseException) -> FailureWords:
    """Say what kind of failure *error* is, without its raw text.

    A coded error wrapping an operating-system error is judged by the cause
    when the cause is one of the known kinds (a full disk is a full disk
    whatever raised it); otherwise its own authored message is kept, since a
    QUILL raiser wrote that for people.
    """
    kind = _kind(error)
    cause = error.__cause__ or error.__context__
    if kind == OTHER and cause is not None and cause is not error:
        kind = _kind(cause)
    if kind == OTHER and isinstance(error, CodedError):
        text = _coded_text(error)
        if text:
            return FailureWords(OTHER, text, transient=False)
    return FailureWords(kind, _SENTENCES[kind], transient=kind == OFFLINE)


def failure_details(error: BaseException, *, app: str, version: str = "", context: str = "") -> str:
    """The text Copy Details puts on the clipboard: versions and the error.

    Nothing is sent anywhere. Secrets, tokens and the Windows user name are
    redacted; the person can read and edit the text before copying it, and
    the document itself is never included.
    """
    from quill.stability.redaction import redact_text_for_bundle, redact_user_name

    if not version:
        from quill import __version__

        version = __version__
    lines = [f"App: {app} {version}".rstrip(), f"Windows: {platform.platform()}"]
    if context:
        lines.append(f"What was happening: {context}")
    lines.append(f"Kind: {plain_failure(error).kind}")
    lines.append(f"Error: {type(error).__name__}: {error}".rstrip(": "))
    cause = error.__cause__
    if cause is not None:
        lines.append(f"Caused by: {type(cause).__name__}: {cause}".rstrip(": "))
    return redact_user_name(redact_text_for_bundle("\n".join(lines)))


def save_failure_sentence(
    name: str, error: OSError | UnicodeEncodeError, *, app: str = "QUILL", codec: str = ""
) -> str:
    """The words for a failed save, shared by both editors (#1390, FUX-16).

    Every case says the text is still open and unsaved, because that is the
    one fact that decides whether the person panics. The unencodable
    character is named, since "position 1462" is a number nobody can act on.
    """
    kept = " -- your text is still open and unsaved."
    if isinstance(error, UnicodeEncodeError):
        character = error.object[error.start : error.end]
        where = f" as {codec}" if codec else " in its current encoding"
        return (
            f"{app} could not save {name}{where}: it cannot hold {character!r}. "
            f"Save As and choose UTF-8, or take that character out{kept}"
        )
    words = plain_failure(error)
    if words.kind == DISK_FULL:
        return f"The disk is full. {app} could not save {name}. Free some space and try again{kept}"
    if words.kind == DENIED:
        return (
            f"{app} could not save {name}: the file or folder is read-only, or another "
            f"program has it open. Try Save As to a different location{kept}"
        )
    if words.kind == MISSING:
        return (
            f"{app} could not save {name}: the folder it was going to is not there any "
            f"more. Try Save As to a different location{kept}"
        )
    return f"{app} could not save {name}. {words.reason} Try Save As{kept}"


#: Exception types whose class name says nothing a person can act on, so the
#: message alone is clearer than "ValueError: ...".
_SILENT_CLASS_NAMES = frozenset({"Exception", "RuntimeError", "ValueError", "CodedError"})


def describe_command_failure(command_id: str, error: BaseException) -> str:
    """One sentence naming the command *and* what went wrong with it.

    The command id stays because it is what a bug report needs and what the
    Keyboard Manager and the palette both show; the fault is added because it
    is the only part the person did not already know.
    """
    detail = str(error).strip()
    name = type(error).__name__
    if not detail:
        detail = name
    elif name not in _SILENT_CLASS_NAMES:
        detail = f"{name}: {detail}"
    code = getattr(error, "code", "")
    if isinstance(code, str) and code:
        detail = f"{detail} ({code})"
    return f"{command_id} failed -- {detail}"
