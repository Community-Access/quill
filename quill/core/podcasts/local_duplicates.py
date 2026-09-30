"""Is this file already in Personal Audio? (ear.md R10)

Two rules from Earshot's Personal Audio PRD, and both of them are about refusing
to be clever:

**A filename is never a duplicate.** ``recording.m4a`` is what a dozen devices
call a dozen different recordings, and two lectures exported on two days share a
name far more often than they share content. Matching on names would refuse the
second thing somebody actually wanted.

**And nothing is ever silently deduplicated or silently refused.** A match is a
*question* -- "This audio appears to already be in Personal Audio" with **Add
Anyway** and **Cancel** -- because the app cannot know whether two identical files
are a mistake or a deliberate second copy, and guessing either way loses
something. Refusing silently loses the import; deduplicating silently loses the
listener's belief that what they added is there.

So the test is the bytes. SHA-256 of the file, read in bounded chunks so a
two-hour recording does not arrive in memory, and stored on the episode so the
next import compares against a number rather than re-reading the whole library.

An unreadable file answers ``""`` and therefore matches nothing: a file Cast
cannot hash is a file it should let through and let validation reject with a
better sentence than "duplicate".

wx-free, strict-typed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["CHUNK", "DuplicateMatch", "content_hash", "find_duplicate", "prompt_for"]

#: Bytes per read. 1 MiB is large enough that hashing a long recording is not a
#: million syscalls, and small enough that it never shows up as memory.
CHUNK = 1024 * 1024


@dataclass(frozen=True, slots=True)
class DuplicateMatch:
    """The item whose bytes match, and where it lives."""

    show: Any
    episode: Any

    @property
    def title(self) -> str:
        return str(getattr(self.episode, "title", "") or "an untitled item")


def content_hash(path: Path | str) -> str:
    """SHA-256 of the file at *path*, or ``""`` when it cannot be read.

    ``""`` rather than an exception, and ``""`` deliberately matches nothing: a
    file Cast cannot hash should be let through and rejected -- if it must be -- by
    the validation step, which can say "this file cannot be read" instead of the
    actively misleading "this looks like a duplicate".
    """
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            while True:
                block = handle.read(CHUNK)
                if not block:
                    break
                digest.update(block)
    except OSError:
        return ""
    return digest.hexdigest()


def find_duplicate(library: Any, digest: str) -> DuplicateMatch | None:
    """The first Personal Audio item whose stored hash equals *digest*.

    An empty *digest* never matches, so a file that could not be hashed is never
    reported as a duplicate of anything.
    """
    if not digest:
        return None
    for show in getattr(library, "shows", []) or []:
        if not bool(getattr(show, "is_local", False)):
            continue
        for episode in getattr(show, "episodes", []) or []:
            if str(getattr(episode, "content_hash", "") or "") == digest:
                return DuplicateMatch(show=show, episode=episode)
    return None


def prompt_for(match: DuplicateMatch, filename: str = "") -> str:
    """The question to ask, naming both sides of the match.

    Both sides, because "this appears to be a duplicate" on its own leaves the
    listener to guess *of what* -- and the answer decides whether they meant it.
    """
    what = f'"{filename}"' if filename else "This audio"
    return (
        f"{what} appears to already be in Personal Audio, as "
        f'"{match.title}".\n\n'
        "The two files have exactly the same contents. Add it anyway, or cancel?"
    )
