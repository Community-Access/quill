"""Keys no editor in the family may bind, and why -- decided once.

A screen reader takes some keys for itself before any application sees them.
Binding one of those is not a conflict the app can win: the reader intercepts
it, the binding never fires, and nothing anywhere says so. The user assigned a
key, the Keyboard Manager showed it assigned, and pressing it does the reader's
thing instead -- which is the worst shape a keymap bug can take, because every
visible surface agrees that it should have worked.

QUILL Lite refused these at assign time and QUILL refused nothing; QUILL checked
for conflicts and QUILL Lite had no assign-time check at all. Both guards now
exist in both, and the list itself lives here rather than in either product, so
"which keys are the reader's" is answered in one place (bad.md H9, P1.18).

Keys are matched on the **main key**, ignoring modifiers, and that is
deliberate: a reader's modifier is claimed in every combination it appears in.
``Insert``, ``Shift+Insert`` and ``Ctrl+Alt+Insert`` are all the reader's.
"""

from __future__ import annotations

__all__ = ["RESERVED_KEYS", "reservation_for"]

#: Main key -> why it is reserved, in a sentence somebody can act on.
#:
#: One entry, and it should stay short. A long list here would be an app
#: deciding on the user's behalf which keys their reader wants, and readers are
#: configurable -- what belongs here is only what is true of *every* reader in
#: its default configuration.
RESERVED_KEYS: dict[str, str] = {
    "Insert": (
        "Insert is the key NVDA and JAWS use as their own modifier, so it never "
        "reaches the app. Watching it go past is what the Typing Mode status "
        "cell does instead."
    ),
}


def reservation_for(binding: str) -> str:
    """Why *binding* cannot be assigned, or ``""`` when it can.

    The main key is taken from the last ``+``-separated segment of the last
    chord segment, so a chord (``Ctrl+Shift+Grave, Insert``) is judged by the
    key it actually ends on. Case and modifier order do not matter.
    """
    text = str(binding or "").strip()
    if not text:
        return ""
    # The last segment of a multi-step chord is the key that finally fires.
    last_step = text.split(",")[-1].strip()
    parts = [part.strip() for part in last_step.split("+") if part.strip()]
    if not parts:
        return ""
    main = parts[-1]
    for key, reason in RESERVED_KEYS.items():
        if main.lower() == key.lower():
            return reason
    return ""
