"""What has to be true before an imported file becomes an item (ear.md R9).

Earshot's Personal Audio PRD is unusually specific about the order of operations,
and the order is the whole point: **copy, verify, then create the record.** Get it
the other way round and a failed import leaves a visible row pointing at nothing,
which is worse than no import at all because the listener now has to work out what
it is and how to get rid of it.

So, in order:

1. **Check there is room**, against the source's actual size plus a margin. Not
   against an arbitrary maximum -- the PRD is explicit that there is no size cap,
   and it is right: a four-hour lecture recording is a perfectly ordinary thing to
   import and a cap would exist only to make the code simpler.
2. **Copy**, which the importer already does.
3. **Verify the copy**, by size and then by hash. A truncated copy is the failure
   mode that matters here, because it plays -- for a while -- and then stops, which
   reads as a broken file rather than a broken import.
4. **Only then** create the record.
5. **And if anything failed, remove the staged copy**, so the next launch does not
   find an orphan.

Every function answers with a :class:`Check` carrying a sentence written for a
person to hear. None of them raises, because an import that fails has to *say* why
-- "it did not work" is the one answer this feature cannot give, since the listener
has no other way to find out what happened to their file.

wx-free, strict-typed.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

__all__ = ["HEADROOM_BYTES", "Check", "discard", "enough_room", "verify_copy"]

#: Spare room demanded beyond the file itself. A copy that exactly fills the disk
#: leaves no space for the library file that has to be written immediately after
#: it, and failing *that* write is how a successful import becomes an invisible
#: one.
HEADROOM_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class Check:
    """Whether to go on, and what to say when not."""

    ok: bool
    message: str = ""

    def __bool__(self) -> bool:
        return self.ok


def _readable_size(size: int) -> str:
    """A byte count as a person says it."""
    if size >= 1024**3:
        return f"{size / 1024**3:.1f} GB"
    if size >= 1024**2:
        return f"{size / 1024**2:.0f} MB"
    return f"{max(1, size // 1024)} KB"


def enough_room(source: Path, destination_folder: Path) -> Check:
    """Whether *destination_folder* can hold a copy of *source*.

    Checked before a single byte is copied, because the alternative is a
    half-written file and a disk with nothing left to clean it up with.

    A source or a folder Cast cannot measure answers **ok**: refusing an import
    because a size could not be read would block a perfectly good file on a network
    share, and the copy itself will fail honestly if it must.
    """
    try:
        needed = source.stat().st_size
    except OSError:
        return Check(True)
    try:
        free = shutil.disk_usage(destination_folder).free
    except OSError:
        return Check(True)
    if free >= needed + HEADROOM_BYTES:
        return Check(True)
    return Check(
        False,
        f"There is not enough room to copy {source.name}. It needs "
        f"{_readable_size(needed)} and there is {_readable_size(free)} free. "
        "Nothing has been changed; free some space and try again.",
    )


def verify_copy(source: Path, copied: Path, *, expect_hash: str = "") -> Check:
    """Whether *copied* is a faithful copy of *source*.

    Size first, because it is nearly free and catches the truncation that matters.
    Then the hash, when the caller has already computed the source's -- a truncated
    copy is the failure worth catching here, since it plays for a while and then
    stops, which the listener reads as a broken file rather than a broken import.
    """
    if not copied.is_file():
        return Check(False, f"{source.name} could not be copied into Cast's folder.")
    try:
        source_size = source.stat().st_size
        copied_size = copied.stat().st_size
    except OSError:
        return Check(False, f"Cast could not check its copy of {source.name}.")
    if source_size != copied_size:
        return Check(
            False,
            f"Cast's copy of {source.name} is incomplete "
            f"({_readable_size(copied_size)} of {_readable_size(source_size)}). "
            "It has been removed; your original file is untouched.",
        )
    if expect_hash:
        from quill.core.podcasts.local_duplicates import content_hash

        if content_hash(copied) != expect_hash:
            return Check(
                False,
                f"Cast's copy of {source.name} does not match the original. "
                "It has been removed; your original file is untouched.",
            )
    return Check(True)


def discard(copied: Path) -> None:
    """Remove a staged copy after a failed import. Never raises.

    Called on every failure path, so the next launch does not find an orphan --
    and swallowing its own failure because the alternative is an exception raised
    while already reporting an exception, which loses the message that mattered.
    """
    try:
        if copied.is_file():
            copied.unlink()
    except OSError:
        pass
