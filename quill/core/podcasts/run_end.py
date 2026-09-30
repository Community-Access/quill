"""What happens when a listening run ends: one choice, not two booleans (R7).

Cast stored two independent switches -- ``continue_after_queue`` and
``continue_after_group`` -- and asked the listener to hold the four combinations
in their head. Two of the four are the same thing (both off, and group-only with
an empty queue both mean "stop"), and the pair cannot express the one thing
people actually want to say, which is *which* of the two should carry on.

So it is one choice with three answers, and the booleans become how it is
**stored** rather than how it is asked:

``"stop"``
    An episode ending is the end. Nothing follows.
``"queue"``
    Carry on with the rest of the Play Queue. The default, and what
    auto-advance has always done.
``"folder"``
    Carry on with the rest of the folder the episode came from -- the show's own
    next unplayed episode.

**Existing settings keep working, and that is the whole reason this module is a
translation rather than a new field.** A settings file written before this change
has the two booleans and no choice; :func:`from_settings` reads them, and
:func:`to_settings` writes both back, so a listener who downgrades does not lose
their answer and nothing has to migrate on disk.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from typing import Any

__all__ = ["CHOICES", "LABELS", "default_choice", "describe", "from_settings", "to_settings"]

#: The three answers, in the order a chooser should offer them: the default in
#: the middle is a worse list than the default first.
CHOICES: tuple[str, ...] = ("queue", "folder", "stop")

#: What each one is called where a listener meets it. One sentence each, because
#: "Continue" on its own does not say *with what*.
LABELS: dict[str, str] = {
    "queue": "Carry on with the rest of the queue",
    "folder": "Carry on with the rest of this folder",
    "stop": "Stop when the episode ends",
}


def default_choice() -> str:
    """``"queue"`` -- what auto-advance has always done."""
    return "queue"


def from_settings(settings: Any) -> str:
    """The choice a settings record means, reading the two stored booleans.

    The queue wins when both are set, because that is what the old code did:
    ``continue_after_queue`` was tried first and ``continue_after_group`` was
    only reached when the queue had nothing. Reading it any other way would
    change behaviour for somebody who never touched the setting.
    """
    stored = str(getattr(settings, "run_end_action", "") or "").strip().lower()
    if stored in CHOICES:
        return stored
    if bool(getattr(settings, "continue_after_queue", True)):
        return "queue"
    if bool(getattr(settings, "continue_after_group", False)):
        return "folder"
    return "stop"


def to_settings(settings: Any, choice: str) -> str:
    """Store *choice* on *settings*, in both shapes. Returns what was stored.

    Both shapes on purpose: the new field is what this module reads back, and
    the two booleans are what an older build reads, so a listener moving between
    versions keeps their answer either way.
    """
    resolved = choice if choice in CHOICES else default_choice()
    settings.run_end_action = resolved
    settings.continue_after_queue = resolved == "queue"
    settings.continue_after_group = resolved == "folder"
    return resolved


def describe(choice: str) -> str:
    """The sentence for a status field or a settings summary."""
    return LABELS.get(choice, LABELS[default_choice()])
