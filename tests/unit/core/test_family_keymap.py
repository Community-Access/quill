"""The family parity gate (bad.md P1.15, section 9 item 1).

Fifty-three chords meant different things in the two editors when the family
audit started, and nothing in the build could say so: each editor's keymap was
internally consistent, and the *pair* was nobody's test. Every convergence this
plan has made since is one somebody could undo by touching one file.

So: every QuillLite handler maps to the QUILL command id that means the same
thing (`quill/core/lite/parity.py`), and the two must resolve to the same chord
unless the pair is in `DIVERGENCES` with a reason. A chord counts as matching
if it is QUILL's primary *or* one of its documented aliases, because an alias
is how rule 5 says "both keys work here".

**The table is the review.** A new QuillLite command fails this until somebody
writes its row, and writing the row is where they have to decide whether QUILL
has that verb at all -- which is the question rule 10 exists to ask.
"""

from __future__ import annotations

import pytest

from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP
from quill.core.keymap_query import canonical_binding
from quill.core.lite.commands import COMMANDS
from quill.core.lite.parity import (
    COMMAND_EQUIVALENTS,
    DIVERGENCES,
    LITE_ONLY,
    NATIVE_IN_BOTH,
)


def _lite_chords() -> dict[str, str]:
    return {
        handler: key
        for _menu, _label, key, handler, kind in COMMANDS
        if kind != "sep" and handler and key
    }


def _same_chord(lite_key: str, command_id: str) -> bool:
    """Whether *lite_key* reaches *command_id* in QUILL, primary or alias."""
    wanted = canonical_binding(lite_key) or lite_key.upper()
    for candidate in (DEFAULT_KEYMAP.get(command_id, ""), DEFAULT_ALIASES.get(command_id, "")):
        if candidate and (canonical_binding(candidate) or candidate.upper()) == wanted:
            return True
    return False


def test_every_quilllite_command_is_accounted_for() -> None:
    """Mapped, native in both, or named as a QUILL gap. No fourth answer."""
    unaccounted = sorted(
        handler
        for handler in _lite_chords()
        if handler not in COMMAND_EQUIVALENTS
        and handler not in NATIVE_IN_BOTH
        and handler not in LITE_ONLY
    )
    assert unaccounted == [], (
        "QuillLite handlers with no row in quill/core/lite/parity.py: "
        + ", ".join(unaccounted)
        + ". Map it to QUILL's command id, or add it to LITE_ONLY -- which is "
        "a statement that QUILL cannot do this, and therefore a P1."
    )


def test_every_mapped_command_id_exists() -> None:
    missing = sorted({cid for cid in COMMAND_EQUIVALENTS.values() if cid not in DEFAULT_KEYMAP})
    assert missing == [], f"mapped to command ids QUILL does not have: {missing}"


@pytest.mark.parametrize(
    ("handler", "command_id"),
    sorted(COMMAND_EQUIVALENTS.items()),
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_two_editors_agree_about_this_chord(handler: str, command_id: str) -> None:
    lite_key = _lite_chords().get(handler, "")
    if not lite_key:
        return
    if handler in DIVERGENCES:
        return
    assert _same_chord(lite_key, command_id), (
        f"{handler} is {lite_key!r} in QuillLite and "
        f"{DEFAULT_KEYMAP.get(command_id)!r} in QUILL ({command_id}). "
        "Move one, add a QUILL alias, or put the pair in DIVERGENCES with the "
        "reason -- a chord that means two things is a key somebody presses "
        "expecting one and gets the other."
    )


def test_every_divergence_names_a_real_pair_and_gives_a_reason() -> None:
    """A stale exception is worse than none: it hides a pair that has converged."""
    lite = _lite_chords()
    for handler, reason in sorted(DIVERGENCES.items()):
        assert handler in COMMAND_EQUIVALENTS, f"{handler} is not a mapped pair"
        assert len(reason) > 40, f"{handler}'s reason is too short to be one"
        command_id = COMMAND_EQUIVALENTS[handler]
        if _same_chord(lite.get(handler, ""), command_id):
            raise AssertionError(
                f"{handler} and {command_id} agree now; delete the DIVERGENCES row"
            )


def test_no_chord_means_two_different_things_across_the_editors() -> None:
    """The failure the audit actually found, stated as a property.

    Ctrl+Alt+J was Set Temporary Bookmark in QUILL and Justify in QuillLite;
    Ctrl+Alt+V was Open Copy Tray here and Paste from Tray there. Each editor
    was internally consistent and the pair was nobody's test.
    """
    lite = _lite_chords()
    offenders: list[str] = []
    for handler, lite_key in sorted(lite.items()):
        canonical = canonical_binding(lite_key) or lite_key.upper()
        mapped = COMMAND_EQUIVALENTS.get(handler)
        for command_id, quill_key in DEFAULT_KEYMAP.items():
            if not quill_key:
                continue
            if (canonical_binding(quill_key) or quill_key.upper()) != canonical:
                continue
            if mapped == command_id or handler in DIVERGENCES:
                continue
            if handler in NATIVE_IN_BOTH or handler in LITE_ONLY:
                continue
            offenders.append(f"{lite_key}: {handler} in QuillLite, {command_id} in QUILL")
    assert offenders == [], "one chord, two meanings:\n  " + "\n  ".join(offenders)


def test_the_gap_list_is_a_backlog_not_a_shrug() -> None:
    """Everything in LITE_ONLY is QuillLite ahead of QUILL, which rule 10 forbids.

    The set is allowed to exist -- the work is scheduled -- but it must stay
    small and it must be *read* when it changes, which is what a named constant
    with a comment per entry buys.
    """
    assert len(LITE_ONLY) <= 8, (
        "QuillLite is ahead of QUILL in more places than the plan accounts for"
    )
