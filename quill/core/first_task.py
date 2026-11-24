"""The first useful task, named where a new person meets nothing (FUX-09).

An empty list, queue or library is the first thing somebody new meets, and
it is where they decide whether the app can do anything for them. FUX-09 asks
that place to name the one or two actions that fill it, by the label the menu
uses and the key that runs it, so a person can finish something useful before
learning the product's vocabulary:

    No podcasts yet. Add Podcast (Ctrl+N) finds one by name or by its address.

:func:`first_task_line` builds that sentence from the app's *live* bindings,
so a rebound key is the key that is said; an unbound command is named by its
label alone, never with a key that does nothing. It is a line, said once or
shown on one focusable control -- never a tour, a welcome or a modal, which
the family interaction contracts forbid ("What a feature must not add").

wx-free and strict-typed; the wx side is :mod:`quill.ui.empty_state_line`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

__all__ = ["KeyFor", "NextAction", "first_task_line", "named"]

#: Answers the key bound to a command id now, or "" when it has none.
KeyFor = Callable[[str], str]


@dataclass(frozen=True)
class NextAction:
    """One action that fills an empty place.

    *label* is the menu's own wording without its access-key ampersand
    ("Add Podcast"); *command_id* is looked up for the key at the moment the
    line is built; *does* is the short clause after it ("finds one by name").
    *key* is a fixed key for an action with no rebindable command (a button's
    Alt+letter); a live binding for *command_id* wins over it.
    """

    label: str
    command_id: str = ""
    does: str = ""
    key: str = ""


def _key(action: NextAction, key_for: KeyFor | None) -> str:
    if action.command_id and key_for is not None:
        try:
            bound = str(key_for(action.command_id) or "").strip()
        except Exception:  # noqa: BLE001 - a broken lookup names the label alone
            bound = ""
        if bound:
            return bound
    return action.key.strip()


def named(action: NextAction, key_for: KeyFor | None = None) -> str:
    """``"Add Podcast (Ctrl+N) finds one by name"``: label, key, what it does."""
    label = action.label.replace("&", "").rstrip(".").strip()
    key = _key(action, key_for)
    text = f"{label} ({key})" if key else label
    return f"{text} {action.does.strip()}" if action.does.strip() else text


def first_task_line(
    situation: str,
    actions: Sequence[NextAction],
    key_for: KeyFor | None = None,
) -> str:
    """*situation* ("No podcasts yet.") followed by its next actions.

    One action reads "A."; two read "A, or B."; more than two is a menu, not a
    beginning, so only the first two are named.
    """
    head = situation.strip()
    if head and head[-1] not in ".!?":
        head += "."
    parts = [named(action, key_for) for action in actions[:2]]
    parts = [part for part in parts if part]
    if not parts:
        return head
    tail = parts[0] if len(parts) == 1 else f"{parts[0]}, or {parts[1]}"
    tail = tail[0].upper() + tail[1:]
    return f"{head} {tail}." if head else f"{tail}."
