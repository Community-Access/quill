"""Handing an episode's audio to the rest of the computer (list.md 2.2).

Save Episode Audio As already existed, and it had one shape problem: an
episode that was not downloaded yet got a "download it now? then run this
command again" prompt. That is honest -- it refuses to block a UI thread on a
download of unknown length -- but it makes the listener the scheduler. Earshot
says **"Preparing audio file for export"** and then opens the save dialog when
the bytes arrive, and that is the right shape: one keystroke, one wait, one
outcome.

This module is the wx-free half of that: what state the export is in, and what
to say about it. The waiting itself is a timer in
:mod:`quill.ui.podcasts.export_audio`, because a wait needs a UI thread.

**Why a state machine at all**, for what looks like one `if`: the wait has four
endings, not two -- the file arrives, the download fails, the listener cancels
it from the Downloads window, or nothing happens for long enough that
continuing to wait is its own kind of silence. Each of those has to say
something different, and a chain of ``if`` in the timer callback is where that
kind of thing goes wrong quietly.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from typing import Any

#: Said the moment the verb is used on an episode whose bytes are not here
#: yet. Earshot's words, deliberately: the wait is otherwise entirely silent,
#: and silence after a keystroke reads as "nothing happened".
PREPARING = "Preparing audio file for export"

#: How long to wait for a download before saying so and stopping. Not a
#: failure -- the download carries on in the Downloads window, and Save
#: Episode Audio As will find the file when it lands. This only ends the
#: *waiting*, because a progress-free wait past a few minutes is indis-
#: tinguishable from a hang.
WAIT_CEILING_SECONDS = 300

#: How often to look. A local queue, so this is cheap; a second is short
#: enough that the save dialog opens as the download finishes rather than
#: noticeably after it.
POLL_SECONDS = 1

READY = "ready"
WAITING = "waiting"
FAILED = "failed"
CANCELLED = "cancelled"
GAVE_UP = "gave-up"


def has_audio(episode: Any) -> bool:
    """Whether this episode's bytes are on this computer (pure).

    The path being *recorded* is not the same as the file being *there*: a
    downloaded copy removed from outside the app leaves the record behind, and
    exporting a file that is gone is the one outcome worse than refusing.
    The caller supplies the existence check, so this stays pure -- it answers
    only whether there is a path to check at all.
    """
    return bool(str(getattr(episode, "downloaded_path", "") or "").strip())


def poll_state(item: Any, waited_seconds: float) -> str:
    """What the wait should do next, given the download's own row (pure).

    *item* is the queue's ``DownloadItem`` for this episode, or ``None`` --
    which means the row is gone, and a row that vanishes without completing
    was cancelled. Treating "gone" as "still waiting" is how a wait becomes
    forever.
    """
    status = str(getattr(item, "status", "") or "") if item is not None else ""
    if status == "completed":
        return READY
    if status == "failed":
        return FAILED
    if item is None or status == "cancelled":
        return CANCELLED
    if waited_seconds >= WAIT_CEILING_SECONDS:
        return GAVE_UP
    return WAITING


def preparing(title: str) -> str:
    """What to say when the wait starts."""
    return f"{PREPARING}. Downloading {title}."


def failed(title: str, reason: str = "") -> str:
    detail = f" {reason.rstrip('.')}." if reason.strip() else ""
    return f"{title} could not be downloaded, so there is nothing to export.{detail}"


def cancelled(title: str) -> str:
    return f"The download of {title} was cancelled, so there is nothing to export."


def gave_up(title: str) -> str:
    """Ends the waiting, not the download -- and says which."""
    return (
        f"{title} is still downloading. It will carry on in the Downloads "
        "window; use Save Episode Audio As again once it has finished."
    )


def missing_file(title: str) -> str:
    """The recorded copy is not on disk. Said instead of failing silently."""
    return f"The downloaded copy of {title} is no longer on this computer."


#: Characters Windows will not accept in a filename. Replaced rather than
#: stripped so two episodes whose titles differ only by punctuation do not
#: collapse onto the same suggested name.
_UNSAFE_FILENAME_CHARS = '<>:"/\\|?*'


def suggested_filename(show: Any, episode: Any, suffix: str) -> str:
    """A "Show - Episode.ext" name the operating system will actually accept.

    Bounded, because a podcast title plus an episode title can easily exceed
    the path limit -- and a Save dialog that opens pre-filled with a name the
    system rejects is worse than one that opens with a shorter name.
    """
    raw = f"{getattr(show, 'title', '')} - {getattr(episode, 'title', '')}".strip(" -")
    cleaned = "".join(
        " " if character in _UNSAFE_FILENAME_CHARS else character for character in raw
    )
    cleaned = " ".join(cleaned.split()).strip(". ")
    return f"{cleaned[:120] or 'episode'}{suffix}"


def copied_path(path: str) -> str:
    """Copy Path's answer. The folder, because that is what gets read out.

    A full path spoken by a screen reader is a long string of separators; the
    file name is what identifies it, and the folder is what somebody is about
    to paste. Both, named, beats one line of punctuation.
    """
    from pathlib import PurePath

    parts = PurePath(path)
    return f"Copied the path to {parts.name}, in {parts.parent}."


__all__ = [
    "CANCELLED",
    "FAILED",
    "GAVE_UP",
    "POLL_SECONDS",
    "PREPARING",
    "READY",
    "WAITING",
    "WAIT_CEILING_SECONDS",
    "cancelled",
    "copied_path",
    "failed",
    "gave_up",
    "has_audio",
    "missing_file",
    "poll_state",
    "preparing",
    "suggested_filename",
]
