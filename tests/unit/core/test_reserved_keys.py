"""Keys no editor in the family may bind, and why (bad.md H9, P1.18).

A screen reader takes some keys for itself before any application sees them.
Binding one is not a conflict the app can win: the reader intercepts it, the
binding never fires, and nothing says so -- the user assigned a key, the
Keyboard Manager showed it assigned, and pressing it does the reader's thing.
Every visible surface agrees it should have worked, which is what makes it the
worst shape a keymap bug takes.

QUILL Lite refused these at assign time and QUILL refused nothing. Both do now,
from one list.
"""

from __future__ import annotations

import pytest

from quill.core.reserved_keys import RESERVED_KEYS, reservation_for


def test_the_readers_modifier_is_reserved() -> None:
    assert "Insert" in RESERVED_KEYS
    assert "NVDA" in RESERVED_KEYS["Insert"]


@pytest.mark.parametrize(
    "binding",
    ["Insert", "insert", "INSERT", "Shift+Insert", "Ctrl+Alt+Insert", "Ctrl+Shift+Grave, Insert"],
)
def test_every_combination_of_a_reserved_key_is_refused(binding: str) -> None:
    """Matched on the main key, ignoring modifiers, because a reader's modifier
    is claimed in every combination it appears in -- there is no Shift+Insert
    the app gets to keep."""
    assert reservation_for(binding)


@pytest.mark.parametrize("binding", ["Ctrl+K", "F7", "Alt+Shift+F9", "Ctrl+Shift+Grave, S", ""])
def test_an_ordinary_binding_is_allowed(binding: str) -> None:
    """The list is short on purpose. A long one would be the app deciding on the
    user's behalf which keys their reader wants, and readers are configurable."""
    assert reservation_for(binding) == ""


def test_a_chord_is_judged_by_the_key_it_ends_on() -> None:
    """The last step of a multi-step chord is the key that finally fires, so it
    is the one that has to be free."""
    assert reservation_for("Ctrl+Shift+Grave, Insert")
    assert reservation_for("Insert, S") == ""  # not a chord QUILL can start anyway


def test_the_reason_is_a_sentence_somebody_can_act_on() -> None:
    """A refusal that says only "reserved" sends somebody to the issue tracker."""
    for reason in RESERVED_KEYS.values():
        assert reason.endswith(".")
        assert len(reason.split()) >= 10


def test_quilllite_reads_the_same_list() -> None:
    """It had its own until 2026-09-17, which is how "which keys belong to the
    screen reader" came to have two answers."""
    from quill.core.lite.keymap import RESERVED_KEYS as LITE

    assert LITE is RESERVED_KEYS
