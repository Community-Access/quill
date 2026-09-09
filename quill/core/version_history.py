"""How a saved version is described out loud -- one phrasing, both products.

QUILL keeps restore points (:mod:`quill.core.restore_points`) and QuillLite
keeps timestamped backups (:mod:`quill.core.lite.backups`). Two stores, and
deliberately two: they were written for different products with different
retention rules, and QuillLite keeps nothing in QUILL's data folder. But a
listener choosing between eleven versions of their own file is doing the same
thing in both, and hearing it described two different ways would be a difference
with no reason behind it.

So the *phrasing* is shared even though the storage is not, and it is here
rather than in either store because neither may own it.

The wording is built for listening rather than for reading, which is why it is
not ``strftime``:

* **Front-loaded.** "Today at 4:12 PM", not "4:12 PM today". Arrowing down a
  list, the first syllable is the one that has to distinguish the row -- and
  today-versus-yesterday is what somebody is actually choosing between.
* **Relative where relative is what is meant.** A version from this morning is
  "Today"; nobody thinks of it by date. Beyond yesterday the date is the fact,
  because "eleven days ago" is arithmetic the listener has to do.
* **No seconds and no leading zero.** "4:12 PM" rather than "04:12:07 PM": two
  extra digits per row, read aloud, eleven times, to distinguish saves that were
  never a minute apart.

wx-free and directly tested.
"""

from __future__ import annotations

from datetime import datetime

__all__ = ["speakable_when", "version_label"]


def speakable_when(saved: datetime, now: datetime | None = None) -> str:
    """A short, front-loaded time label for a saved version.

    *saved* is expected in local time; *now* defaults to the local moment and is
    a parameter so this can be tested without waiting for midnight.
    """
    today = (now or datetime.now().astimezone()).date()
    day_delta = (today - saved.date()).days
    clock = saved.strftime("%I:%M %p").lstrip("0")
    if day_delta == 0:
        return f"Today at {clock}"
    if day_delta == 1:
        return f"Yesterday at {clock}"
    return f"{saved.strftime('%B %d, %Y')} at {clock}"


def version_label(saved: datetime, *, words: int, note: str = "") -> str:
    """One row of a version list: when it was saved, and how big it was.

    The size is there to be *compared*, not read: it is usually the only thing
    that tells two saves a minute apart apart, and a version that is suddenly
    two thousand words shorter is the one somebody is hunting for.
    """
    counted = f"{words:,} word" + ("" if words == 1 else "s")
    return f"{speakable_when(saved)} - {counted}{note}"
