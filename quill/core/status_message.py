"""When a status message has outlived the moment it described.

The message cell is the one cell whose content is not a *fact about the
document*. Every other cell answers a question that is still true a minute
later -- how many words, which line, what encoding -- and the message cell
holds the last thing the app said, which stops being true almost immediately.

Nothing expired it. "String not found" sat in the bar through a page of
editing, and a cell that is right at the moment it is written and wrong for the
next ten minutes is worse than an empty one: somebody who arrows to it to check
what happened is told about something that happened before lunch, with nothing
in the wording to say so. Reported exactly that way -- "if I go do a bunch of
edits and still see Find not found, that is a problem".

Two rules, and the first is the one that matters:

* **The next edit clears it.** A message describes the document as it was; once
  the document has moved on, the description is stale by definition. The
  revision is recorded at the moment the message is set -- which is *after* the
  edit that prompted it -- so a message survives its own edit and dies on the
  next one. Switching documents counts as a move too: the comparison is
  inequality, not order, so a per-tab revision going backwards expires the
  message rather than resurrecting it.

* **Otherwise it ages out.** Somebody who never edits -- reading, arrowing,
  searching -- would keep the message forever under the first rule alone.
  :data:`MESSAGE_TTL_SECONDS` is long enough to arrow to the cell and read the
  exact wording of an error, short enough that it is gone by the time it could
  mislead.

Expiring is *silent*. The cell's label changes on an unfocused control, which
is precisely what a screen reader does not announce (GATE-13), and a message
that announced itself again on the way out would be the over-announcement the
gate exists to stop.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "IDLE_MESSAGE",
    "MESSAGE_TTL_SECONDS",
    "StatusMessage",
    "current_message",
]

#: What the message cell reads when there is nothing to say. Not an empty
#: string: a cell with no text is a button with no name, and a reader walking
#: the row announces the silence as an unlabelled control rather than as "there
#: is nothing here".
IDLE_MESSAGE = "Ready"

#: How long a message stays after it was said, absent an edit. A minute is
#: several times longer than the "what did it just say?" it exists for, and
#: well short of the "this has been here all afternoon" it is a bug for.
MESSAGE_TTL_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class StatusMessage:
    """A message, and the two facts that decide when it stops being true.

    *set_at* is a monotonic clock reading, not a wall clock: the bar must not
    expire everything at once because the machine woke from sleep or crossed a
    daylight-saving boundary.
    """

    text: str
    set_at: float
    revision: int


def current_message(
    message: StatusMessage | None,
    *,
    now: float,
    revision: int,
    ttl: float = MESSAGE_TTL_SECONDS,
    idle: str = IDLE_MESSAGE,
) -> str:
    """What the message cell should read, given the message and the moment.

    Returns *idle* rather than an empty string for every expired case, so the
    caller never has to decide what "no message" looks like.
    """
    if message is None or not message.text:
        return idle
    if revision != message.revision:
        return idle
    if now - message.set_at >= ttl:
        return idle
    return message.text
