"""The reminder verb a row offers, paired (list.md 7.1).

Two lines of menu, in their own module for the reason GATE-11 asks for -- and
because the pairing is a rule rather than a detail: a row offers **Set a
Reminder** or **Remove Reminder**, never both and never the wrong one. A menu
that cannot tell you what you already did is a menu you have to remember for,
which is exactly the job a reminder exists to take off somebody.

Here rather than inline in ``row_actions`` so QUILL Cast's episode rows can
offer the identical pair when they grow one: the store already takes an
``episode`` kind, and two apps spelling this differently is how the same verb
ends up meaning two things.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from typing import Any

SET_REMINDER = "reminder.set"
REMOVE_REMINDER = "reminder.remove"

SET_LABEL = "Set a Re&minder..."
REMOVE_LABEL = "Remove Re&minder"


def reminder_action(row_action: Any, *, has_reminder: bool) -> Any:
    """The one reminder verb this row should show.

    *row_action* is the ``RowAction`` class, passed in rather than imported, so
    this module stays below ``row_actions`` in the import order and neither has
    to know about the other's dataclass.
    """
    return (
        row_action(REMOVE_REMINDER, REMOVE_LABEL)
        if has_reminder
        else row_action(SET_REMINDER, SET_LABEL)
    )


__all__ = ["REMOVE_LABEL", "REMOVE_REMINDER", "SET_LABEL", "SET_REMINDER", "reminder_action"]
