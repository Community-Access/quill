"""The status-bar cell description Quill Radio's bar is built from.

Split out of :mod:`quill.ui.radio.status_bar` (GATE-11) on 2026-10-15, when
the Notifications cell would have taken that module past its budget. The bar
re-exports both names, so ``from quill.ui.radio.status_bar import CellSpec``
still works.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = ["CellSpec", "clamp_index"]


@dataclass(frozen=True)
class CellSpec:
    """One status-bar cell: its stable key, spoken name, and behaviour.

    ``text`` returns the live value (``""`` for "nothing to say"), ``activate``
    is what Enter/Space does, ``help`` is the one-line hint, and ``build_menu``
    (if set) populates a right-click context menu with extra actions.
    """

    key: str
    name: str
    text: Callable[[], str]
    activate: Callable[[], None]
    help: str
    build_menu: Callable[[Any], None] | None = None
    #: An *action* cell supplies its live button label here -- "Play"/"Stop",
    #: "Mute"/"Unmute" -- and leaves ``text`` returning "". The label is the
    #: action because the control is a button, and a button whose label is a
    #: readout promises an action it does not perform.
    action_label: Callable[[], str] | None = None
    #: The keyboard shortcut an action cell teaches ("Ctrl+P"), folded into
    #: its accessible name so the bar quietly teaches the key.
    key_hint: str = ""
    #: A cell whose hint depends on live state supplies it here, and ``refresh``
    #: keeps it current. The Recording cell needs this because "12 min left" and
    #: "18 min so far" are two different measurements sharing one cell, and
    #: which one is on screen depends on how the capture was started -- a
    #: distinction the number alone cannot carry. A cell with a fixed hint
    #: leaves this ``None`` and ``help`` stands.
    live_help: Callable[[], str] | None = None


def clamp_index(index: int, count: int) -> int:
    """Clamp *index* into ``[0, count - 1]`` (or 0 when the bar is empty)."""
    if count <= 0:
        return 0
    return max(0, min(index, count - 1))
