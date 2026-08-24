"""Reminders on an ordinary row -- a station, a recording, a saved video (7.1).

The store has taken ``station``, ``episode`` and ``other`` kinds since the day
it was written, and until now only calendar programmes could produce one. That
made three quarters of the vocabulary a promise nothing kept, which is the same
fault list.md logs against a stored priority nothing could set.

What a row reminder means, and how it differs from a programme's:

* **There is no start time**, so there is nothing to be reminded *before*. The
  question becomes "when?" rather than "how long before?", which the shared
  dialog handles by reading the same control differently rather than by being a
  second dialog.
* **The target is the stream address**, not a name. A favourite renamed is the
  same station, and the same station reached through two directories has two
  ids and one address -- the identical argument
  :mod:`quill.core.bookmark_anchors` makes for bookmarks, and deliberately the
  same choice, so a reminder and a bookmark on one station agree about what
  that station is.
* **Going there plays it.** The Upcoming window already knows how to open a
  station reminder; this is the half that creates one.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import reminders


def target_for(station: Any) -> str:
    """The handle that finds this row again, or ``""``.

    The stream address, for the reason above. Empty for a row with none, which
    makes the verb refuse rather than create a reminder pointing at nothing.
    """
    return str(getattr(station, "stream_url", "") or "").strip()


def has_reminder(station: Any) -> bool:
    """Whether this row already carries one. Never raises.

    False on any trouble at all: the only cost of being wrong here is that the
    menu offers Set when it could have offered Remove, and the only cost of
    raising is a context menu that does not open.
    """
    target = target_for(station)
    if not target:
        return False
    try:
        from quill.core.paths import app_data_dir

        return reminders.find_for_target(app_data_dir(), reminders.KIND_STATION, target) is not None
    except Exception:  # noqa: BLE001 - a menu must open whatever the store says
        return False


def set_reminder(dialog: Any, host: Any, station: Any) -> None:
    """Ask for the details and set one on this row."""
    target = target_for(station)
    if not target:
        dialog._announce("That row has no address, so there is nothing to remind you about.")
        return
    from quill.ui.radio import reminder_dialog

    name = str(getattr(station, "name", "") or "this station")
    reminder = reminder_dialog.ask(
        host,
        getattr(dialog, "dialog", None) or getattr(dialog, "frame", None),
        title=name,
        kind=reminders.KIND_STATION,
        target=target,
    )
    if reminder is None:
        return
    dialog._announce(reminder_dialog.spoken_confirmation(reminder))


def remove_reminder(dialog: Any, station: Any) -> None:
    """Forget the reminder on this row."""
    from quill.core.paths import app_data_dir

    target = target_for(station)
    existing = (
        reminders.find_for_target(app_data_dir(), reminders.KIND_STATION, target)
        if target
        else None
    )
    if existing is None:
        dialog._announce("There is no reminder on that row.")
        return
    reminders.remove_reminder(app_data_dir(), existing.reminder_id)
    dialog._announce(f"Reminder removed from {existing.title}.")


__all__ = ["has_reminder", "remove_reminder", "set_reminder", "target_for"]
