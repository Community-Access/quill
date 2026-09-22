"""What to do with the unsaved work a previous session left behind.

The recovery store is a copy of every modified window, written on a timer and
removed the moment the document is saved or closed cleanly. That is the right
promise, and for years it had no housekeeping at all: **every launch that ended
badly left one slot per modified window, and nothing ever collected them.** On
2026-09-21 a QuillLite user opened the app and was asked, in one yes-or-no
question, whether to open sixty-nine documents. Sixty-seven of them were the same
four characters, typed into an untitled window by an automated run that was then
killed; two were real. The only answers were "open all sixty-nine" and "no", and
"no" offered them again the next time.

Three things are wrong there, and this module answers all three before anybody is
asked anything:

* **The same text, sixty-seven times, is one piece of work.** :func:`fingerprint`
  hashes what the slot actually holds, and identical copies of an identical
  document collapse to the newest one. Nothing is lost -- the survivor *is* the
  other sixty-six, byte for byte.
* **Unsaved work has a shelf life.** A copy nobody has come back for in a month
  is not work in progress, it is litter that makes the real thing harder to find.
  ``keep_days`` expires it; ``0`` turns expiry off for somebody who wants the old
  behaviour back.
* **An untitled scratch window is not the same promise as a named file.** A file
  has somewhere to go back to; an untitled window is the thing people open to
  paste something into and then abandon. ``offer_untitled`` lets a user say they
  never want those back, which is a real preference and not a safety valve --
  see the setting's own wording, which says plainly that they are discarded.

Everything here is wx-free and side-effect-free: it *decides*, and the caller
deletes. That split is deliberate. A triage that deleted as it classified could
not be tested without a recovery store to sacrifice, and this is precisely the
code where "I thought it only marked them" is the expensive kind of wrong.

The buckets are exhaustive: every slot handed in comes back in exactly one of
``offer``, ``duplicates``, ``stale`` or ``untitled``, so a caller that restores
the first and discards the rest can never silently drop one on the floor --
:func:`triage` guarantees it and the tests assert it.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

__all__ = [
    "DEFAULT_KEEP_DAYS",
    "Recoverable",
    "Triage",
    "age_days",
    "describe_plan",
    "describe_restored",
    "describe_tidy",
    "fingerprint",
    "is_untitled",
    "row_label",
    "size_phrase",
    "summarise_recovery",
    "triage",
    "when_phrase",
]

#: How long a copy of unsaved work is kept before it stops being offered.
#: A month: long enough that a fortnight's holiday cannot lose anything, short
#: enough that the store does not become an archive nobody ever reads. Word
#: deletes its own recovery files after four days, which is the other defensible
#: answer; this is the generous one, because the cost of keeping a slot is a row
#: in a list and the cost of dropping one is somebody's afternoon.
DEFAULT_KEEP_DAYS = 30


class Recoverable(Protocol):
    """The part of a recovery slot this module reads. Both editors' slots fit."""

    @property
    def title(self) -> str: ...

    mode: str
    original_path: str
    content_path: Path


def is_untitled(slot: Recoverable) -> bool:
    """Whether this slot's window never had a file behind it."""
    return not slot.original_path.strip()


def fingerprint(slot: Recoverable) -> str:
    """What this slot *is*, as one string. Equal fingerprints are one document.

    The file it came from and the mode are part of the identity, not just the
    bytes: the same paragraph in a rich window and a plain one restores two
    different ways, and two files that happen to hold identical text are two
    documents whatever their contents say.

    A slot whose content cannot be read gets a fingerprint unique to itself, so
    an unreadable copy is never folded into a readable one. Failing towards
    "these are different" keeps a slot that might be work; failing the other way
    would delete it.
    """
    digest = hashlib.sha256()
    digest.update(slot.mode.encode("utf-8", errors="replace"))
    digest.update(b"\x00")
    digest.update(slot.original_path.encode("utf-8", errors="replace"))
    digest.update(b"\x00")
    try:
        digest.update(slot.content_path.read_bytes())
    except OSError:
        return f"unreadable:{slot.content_path}"
    return digest.hexdigest()


def age_days(slot: Recoverable, now: float | None = None) -> float:
    """How long ago the copy was last written, in days.

    A slot whose content file cannot be stat'ed is reported as brand new rather
    than ancient: expiry deletes, and a filesystem that will not answer a
    question is not a reason to throw work away.
    """
    moment = time.time() if now is None else now
    try:
        written = slot.content_path.stat().st_mtime
    except OSError:
        return 0.0
    return max(0.0, (moment - written) / 86400.0)


@dataclass(frozen=True, slots=True)
class Triage:
    """The four buckets, and how many copies each offered slot stands for."""

    #: What to put in front of the user, newest first.
    offer: tuple[Recoverable, ...] = ()
    #: Byte-identical copies of something already in ``offer``.
    duplicates: tuple[Recoverable, ...] = ()
    #: Older than the keep window.
    stale: tuple[Recoverable, ...] = ()
    #: Untitled, when the user has said they do not want those back.
    untitled: tuple[Recoverable, ...] = ()
    #: Fingerprint -> how many slots that fingerprint covered, including the one
    #: in ``offer``. 1 for the ordinary case; 67 for the case that prompted this.
    copies: dict[str, int] = field(default_factory=dict)

    @property
    def tidied(self) -> tuple[Recoverable, ...]:
        """Everything the caller may delete. Never overlaps ``offer``."""
        return self.duplicates + self.stale + self.untitled

    @property
    def total(self) -> int:
        """How many slots went in."""
        return len(self.offer) + len(self.tidied)

    def copies_of(self, slot: Recoverable) -> int:
        """How many identical copies the offered *slot* stands for, itself included."""
        return self.copies.get(fingerprint(slot), 1)


def triage[S: Recoverable](
    slots: list[S] | tuple[S, ...],
    *,
    now: float | None = None,
    keep_days: int = DEFAULT_KEEP_DAYS,
    offer_untitled: bool = True,
) -> Triage:
    """Sort *slots* into what to offer and what to tidy away.

    In this order, and the order is the argument:

    1. **Expiry** first, because an expired slot should not earn a place in the
       list by being the newest of sixty-seven identical expired ones.
    2. **The untitled preference** next, so a user who has switched it off is not
       offered an untitled document merely because it is recent.
    3. **Duplicates** last, over whatever is left, keeping the newest -- the
       newest copy is the one whose age a person would recognise.

    ``keep_days`` of 0 or less disables expiry entirely.
    """
    moment = time.time() if now is None else now
    live: list[S] = []
    stale: list[S] = []
    untitled: list[S] = []

    for slot in slots:
        if keep_days > 0 and age_days(slot, moment) > keep_days:
            stale.append(slot)
        elif not offer_untitled and is_untitled(slot):
            untitled.append(slot)
        else:
            live.append(slot)

    # Newest first, so the survivor of a duplicate group is the newest one and
    # the offered list reads in the order a person thinks about it.
    live.sort(key=lambda slot: age_days(slot, moment))

    offer: list[S] = []
    duplicates: list[S] = []
    copies: dict[str, int] = {}
    for slot in live:
        mark = fingerprint(slot)
        if mark in copies:
            copies[mark] += 1
            duplicates.append(slot)
            continue
        copies[mark] = 1
        offer.append(slot)

    return Triage(
        offer=tuple(offer),
        duplicates=tuple(duplicates),
        stale=tuple(stale),
        untitled=tuple(untitled),
        copies=copies,
    )


def size_phrase(slot: Recoverable) -> str:
    """How much is in this slot, in words somebody can judge it by.

    A count is the one thing that separates "the paste I abandoned" from "the
    letter I was writing", and it is invisible until the document is open. Rich
    text is measured in bytes and says so, because an RTF file is mostly
    envelope and quoting its size as characters would overstate it several-fold.
    """
    try:
        size = slot.content_path.stat().st_size
    except OSError:
        return "size unknown"
    if slot.mode == "rich":
        if size < 1024:
            return f"{size} bytes of rich text"
        return f"{size // 1024} KB of rich text"
    if size == 1:
        return "1 character"
    if size < 1000:
        return f"{size} characters"
    if size < 1_000_000:
        return f"about {size // 1000},000 characters"
    return f"about {size // 1_000_000} million characters"


def when_phrase(slot: Recoverable, now: float | None = None) -> str:
    """When the copy was last written, relatively -- "yesterday", not a timestamp.

    Relative because that is the form the question is asked in. Nobody knows
    whether they were working at 16:30 on the 21st; everybody knows whether they
    were working yesterday.
    """
    days = age_days(slot, now)
    hours = days * 24
    if hours < 1:
        return "in the last hour"
    if hours < 2:
        return "about an hour ago"
    if days < 1:
        return f"{int(hours)} hours ago"
    if days < 2:
        return "yesterday"
    if days < 14:
        return f"{int(days)} days ago"
    if days < 60:
        return f"{int(days / 7)} weeks ago"
    return f"{int(days / 30)} months ago"


def row_label(slot: Recoverable, copies: int = 1, now: float | None = None) -> str:
    """One row of the chooser: what it is, how much of it, and when.

    The name leads because that is what somebody is looking for. The copy count
    is last and only when there is one, because "67 identical copies" is the
    fact that turns an alarming list into an obvious decision -- and saying it
    where the list can be heard is the whole difference between this window and
    the yes-or-no it replaces.
    """
    where = "" if is_untitled(slot) else f"  --  {slot.original_path}"
    label = f"{slot.title}{where}  --  {size_phrase(slot)}, {when_phrase(slot, now)}"
    if copies > 1:
        label += f"  ({copies} identical copies, kept as one)"
    return label


def summarise_recovery(result: Triage) -> str:
    """The sentence that opens the chooser. Counts first, then what was tidied."""
    offered = len(result.offer)
    if not offered:
        return "There is no unsaved work to come back to."
    noun = "document" if offered == 1 else "documents"
    sentence = f"Unsaved work from {offered} {noun}."
    tidy = describe_tidy(result)
    return f"{sentence} {tidy}" if tidy else sentence


def describe_tidy(result: Triage) -> str:
    """What was folded away before the list was shown, or "" when nothing was.

    Said rather than silently done. Tidying that happens without a word is
    indistinguishable from work that has gone missing, and this is exactly the
    store where that suspicion is expensive.
    """
    parts: list[str] = []
    if result.duplicates:
        count = len(result.duplicates)
        copy = "copy" if count == 1 else "copies"
        parts.append(f"{count} identical {copy} folded into the rows above")
    if result.stale:
        count = len(result.stale)
        noun = "copy" if count == 1 else "copies"
        parts.append(f"{count} {noun} older than a month dropped")
    if result.untitled:
        count = len(result.untitled)
        noun = "document" if count == 1 else "documents"
        parts.append(f"{count} untitled {noun} dropped, as your settings ask")
    if not parts:
        return ""
    if len(parts) == 1:
        return f"{parts[0][0].upper()}{parts[0][1:]}."
    return f"{'; '.join(parts)}."


def describe_plan(
    result: Triage,
    checked: tuple[bool, ...],
    *,
    now: float | None = None,
) -> str:
    """The whole window as a paragraph, kept in step with the checkboxes.

    Asked for by name: *"a read-only edit field ... that describes the state of
    restorable items in significant detail ... maintained to show what actions
    would or would not be performed after making selections so that the user can
    see this."*

    A list of checkboxes answers "what is here" one row at a time and never
    answers "what happens when I press the button" at all -- and that second
    question is the one somebody is actually asking, because the buttons are
    the irreversible part. Sighted users assemble the answer by glancing down
    the list; assembling it by ear costs a pass through every row, and the pass
    has to be repeated after every tick. So it is written out, in one place, and
    rewritten whenever a box changes.

    Three sections, in the order somebody needs them: what was tidied before the
    list existed, what each row is, and what each button would do right now.
    """
    lines: list[str] = []
    ticked = [slot for slot, on in zip(result.offer, checked, strict=False) if on]
    unticked = [slot for slot, on in zip(result.offer, checked, strict=False) if not on]

    tidy = describe_tidy(result)
    if tidy:
        lines.append(f"Before this list was built: {tidy}")
        lines.append("")

    total = len(result.offer)
    noun = "document" if total == 1 else "documents"
    lines.append(f"{total} {noun} of unsaved work, {len(ticked)} ticked.")
    lines.append("")
    for index, slot in enumerate(result.offer, start=1):
        on = checked[index - 1] if index - 1 < len(checked) else False
        mark = "Ticked" if on else "Not ticked"
        lines.append(f"{index}. {mark}. {row_label(slot, result.copies_of(slot), now)}")
    lines.append("")

    lines.append("If you press a button now:")
    if ticked:
        names = ", ".join(slot.title for slot in ticked)
        lines.append(f"  Restore Checked opens {_count(len(ticked), 'document')}: {names}.")
        lines.append(
            f"  Discard Checked permanently deletes {_count(len(ticked), 'ticked document')}. "
            "Nothing else has a copy."
        )
    else:
        lines.append("  Restore Checked does nothing: no rows are ticked.")
        lines.append("  Discard Checked does nothing: no rows are ticked.")
    lines.append(f"  Restore All opens all {total}, ticked or not.")
    lines.append(f"  Discard Everything permanently deletes all {total}. It asks first.")
    if unticked:
        kept = ", ".join(slot.title for slot in unticked)
        stays = "stays" if len(unticked) == 1 else "stay"
        lines.append(
            f"  Either way, {_count(len(unticked), 'unticked document')} {stays} "
            f"saved aside: {kept}."
        )
    lines.append("  Not Now changes nothing. Everything here is offered again next time.")
    return "\n".join(lines)


def _count(number: int, noun: str) -> str:
    """``3 documents`` / ``1 document``. Agreement written once, not eight times."""
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def describe_restored(restored: int, total: int) -> str:
    """What to say after restoring. Never silent, even when nothing was taken."""
    if total <= 0:
        return "Nothing was restored."
    if restored <= 0:
        return f"Restored none of the {total}. The work is still saved aside."
    noun = "document" if restored == 1 else "documents"
    if restored == total:
        return f"Restored {restored} unsaved {noun}. Save each one to keep it."
    return f"Restored {restored} of {total}. Save each one to keep it."
