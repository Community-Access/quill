"""Gate 6: a chord written in a user guide must be a chord that exists.

The 2026-09-18 documentation pass found **46 stale chords** in QUILL's user
guide -- keys the guide taught confidently that the product had moved months
earlier. Several were worse than merely absent: the old spelling had since been
taken by a *different* command, so following the guide did something unexpected
rather than nothing. That is the failure mode this gate exists for, because
"nothing happened" is a guess a person can recover from and "something else
happened" is one they have to undo.

A guide is not generated -- ``docs/keyboard-reference.md`` is, and is drift-gated
already -- because prose has to explain, not tabulate. What can be checked is
that every chord the prose *names* is a chord something is actually bound to.

Two things deliberately pass:

* **Chords nothing in QUILL binds, because Windows or the reader binds them.**
  ``Alt+F4``, ``Win+V``, ``Ctrl+Home``, a JAWS layer key: the guide is right to
  mention them and QUILL would be wrong to claim them.
* **Halves of a chord sequence and prose placeholders.** ``Shift+9`` inside a
  QUILL-key chord, or ``Shift+digit`` in a sentence about a family of keys.

Both are allowlisted by shape rather than one at a time, so the list does not
grow with every paragraph somebody writes.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]

GUIDES: tuple[Path, ...] = (
    _ROOT / "docs" / "user guide" / "userguide.md",
    _ROOT / "standalone" / "quilllite" / "docs" / "userguide.md",
)

#: A chord as the guides write it. QUILL's guide uses backticks and QuillLite's
#: uses bold, so both count -- a gate that only read one would have left the
#: other guide unchecked while reporting success, which is the worse failure.
_CHORD = re.compile(
    r"`((?:Ctrl|Alt|Shift|Win)\+[^`]{0,40}?)`"
    r"|\*\*((?:Ctrl|Alt|Shift|Win)\+[^*]{0,40}?)\*\*"
)

#: Keys the operating system or the screen reader owns. QUILL does not bind them
#: and the guides are right to name them.
_NOT_OURS: frozenset[str] = frozenset({
    "alt+f4",
    "ctrl+alt+f4",
    "win+v",
    "ctrl+home",
    "ctrl+end",
    "shift+tab",
    "alt+tab",
    "ctrl+alt+delete",
})

#: Prose that is not a chord at all: a placeholder, or a modifier with nothing
#: after it because the sentence continues.
_PLACEHOLDER = re.compile(
    r"^(?:ctrl|alt|shift|win)(?:\+(?:ctrl|alt|shift|win))*\+?$|digit|letter|key>|<|n$|number",
    re.IGNORECASE,
)

#: The leader itself. ``Ctrl+Shift+Grave`` is a prefix, not a binding: nothing is
#: bound to it, and everything after it is.
_LEADER = "ctrl+shift+grave"

#: The second half of a leader chord, written on its own where the prose has
#: already said which leader it follows -- "QUILL Key, then Shift+O". Never a
#: QUILL binding by itself; the ones that ARE (Shift+F3) are live and never reach
#: here.
_CHORD_TAIL = re.compile(r"^shift\+.{1,4}$", re.IGNORECASE)

#: A menu-bar Alt mnemonic: Alt and one letter, which opens a menu rather than
#: running a command. The menu-item access-key gate is what checks those.
_MENU_MNEMONIC = re.compile(r"^alt\+[a-z]$", re.IGNORECASE)

#: A chord naming the screen reader's own modifier, which by definition QUILL
#: cannot bind and the reader's own documentation owns.
_READER_KEY = re.compile(r"jaws|nvda|insert|capslock", re.IGNORECASE)

#: Bold emphasis that ran past the chord into the sentence -- "**Ctrl+N makes a
#: rich text document**". The chord is real; the match is not a chord.
_RUNS_INTO_PROSE = re.compile(r"\s(?:to|and|or|makes?|opens?|rings?|comes?|sets?|is|the)\b")

#: A family written as one token: a slash pair (``Ctrl+Left/Right``) or a plural
#: (``Alt+arrows``). Each names two or more bindings, so neither is one.
_A_FAMILY = re.compile(r"/|arrows|keys|digits|numbers", re.IGNORECASE)

#: Navigation the control itself handles: QUILL binds none of these and should
#: not, because the native behaviour is what every other edit field does.
_NATIVE_NAVIGATION = re.compile(
    r"^(?:ctrl|shift|ctrl\+shift)\+(?:up|down|left|right|home|end|pageup|pagedown|"
    r"backspace|delete)$",
    re.IGNORECASE,
)


#: ``>`` and ``<`` are the SHIFTED faces of the ``.`` and ``,`` keys, and the
#: guides write whichever one a reader's fingers think of. wx spells the physical
#: key, so the keymap says ``Ctrl+Shift+.`` and the prose says ``Ctrl+Shift+>``;
#: both are the same keystroke and neither is wrong.
_SHIFTED_FACES = {">": ".", "<": ",", "?": "/", "+": "=", "_": "-", ":": ";", '"': "'"}


def _normalise(chord: str) -> str:
    text = chord.replace(" ", "").lower()
    # Only the final character can be a shifted face; "Ctrl+Shift+" is a modifier.
    if text and text[-1] in _SHIFTED_FACES:
        text = text[:-1] + _SHIFTED_FACES[text[-1]]
    return text


def _live_chords() -> set[str]:
    """Every chord anything in the family binds."""
    from quill.core.app_keymaps import APP_KEYMAPS, SIBLING_APP_ACCELERATORS
    from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    live: set[str] = set()
    for mapping in (DEFAULT_KEYMAP, DEFAULT_ALIASES):
        live |= {_normalise(str(v)) for v in mapping.values() if isinstance(v, str) and v}
    for mapping in APP_KEYMAPS.values():
        live |= {_normalise(str(v)) for v in mapping.values() if isinstance(v, str) and v}
    live |= {_normalise(chord) for chord in SIBLING_APP_ACCELERATORS}
    for row in COMMANDS:
        for cell in row:
            if isinstance(cell, str) and "+" in cell:
                live |= {_normalise(cell)}
    return {chord for chord in live if chord}


def _is_a_single_chord(chord: str) -> bool:
    """False for anything that is not one binding QUILL could hold."""
    # A range or a sequence: "Ctrl+Shift+1 through Ctrl+Shift+9", "Alt+Shift+1 to
    # Alt+Shift+9", "Ctrl+Shift+Grave, X". Each names more than one binding.
    if any(part in chord for part in (",", " through ", " to ", " or ", "–")):
        return False
    if _RUNS_INTO_PROSE.search(chord) or _A_FAMILY.search(chord):
        return False
    key = _normalise(chord)
    if key == _LEADER or _NATIVE_NAVIGATION.match(key):
        return False
    if _CHORD_TAIL.match(key) or _MENU_MNEMONIC.match(key) or _READER_KEY.search(key):
        return False
    return not _PLACEHOLDER.search(chord)


#: Words that join two chords into one range: "Alt+Shift+1 **to** Alt+Shift+9".
#: Each endpoint matches on its own, so the range has to be seen in the text
#: around the match rather than inside it.
_RANGE_JOINERS: tuple[str, ...] = (" to ", " through ", "-", "\u2013", "/")


def _joins(fragment: str, *, leading: bool) -> bool:
    """Does this fragment start (or end) with a word that joins two chords?"""
    trimmed = fragment.lstrip("*` ") if leading else fragment.rstrip("*` ")
    for joiner in _RANGE_JOINERS:
        bare = joiner.strip()
        if leading and (fragment.startswith(joiner) or trimmed.startswith(bare)):
            return True
        if not leading and (fragment.endswith(joiner) or trimmed.endswith(bare)):
            return True
    return False


def _is_a_range_endpoint(text: str, match: object) -> bool:
    """True when this chord is one end of a range written as two chords.

    Looked at in both directions, because only the FIRST endpoint is followed by
    the joining word -- the second is followed by the rest of the sentence. A
    one-directional check reports every range's upper bound as a stale chord,
    which is how this was wrong on the first attempt.
    """
    start: int = match.start()  # type: ignore[attr-defined]
    end: int = match.end()  # type: ignore[attr-defined]

    after = text[end : end + 24]
    if _joins(after, leading=True) and _CHORD.search(after):
        return True

    before = text[max(0, start - 28) : start]
    return bool(_joins(before, leading=False) and _CHORD.search(before))


def _stale_chords(guide: Path, live: set[str]) -> list[str]:
    text = guide.read_text(encoding="utf-8")
    stale: list[str] = []
    for match in _CHORD.finditer(text):
        chord = (match.group(1) or match.group(2) or "").strip()
        if not _is_a_single_chord(chord):
            continue
        if _is_a_range_endpoint(text, match):
            continue
        key = _normalise(chord)
        if key in live or key in _NOT_OURS:
            continue
        line = text.count("\n", 0, match.start()) + 1
        stale.append(f"{guide.name}:{line} `{chord}`")
    return stale


def test_every_chord_the_guides_teach_is_a_chord_that_exists() -> None:
    live = _live_chords()
    stale = [entry for guide in GUIDES for entry in _stale_chords(guide, live)]
    assert not stale, (
        "chords taught by a user guide that nothing binds. Several of the 46 found in "
        "2026-09 had since been taken by a different command, so following the guide "
        "did the wrong thing rather than nothing:\n  " + "\n  ".join(stale)
    )


def test_the_gate_is_actually_reading_the_guides() -> None:
    """A scan that finds no chords passes every stale table ever written."""
    live = _live_chords()
    assert len(live) > 300, f"only {len(live)} live chords found"
    for guide in GUIDES:
        text = guide.read_text(encoding="utf-8")
        found = [m.group(1) or m.group(2) for m in _CHORD.finditer(text)]
        assert len(found) > 20, f"{guide.name}: only {len(found)} chords seen"


def test_a_chord_the_product_moved_would_be_caught() -> None:
    """The gate's own failure mode, proved rather than assumed."""
    live = _live_chords()
    assert _normalise("Ctrl+Alt+7") not in live  # the real 2026-09 stale chord
    assert _normalise("Ctrl+S") in live


def test_the_shapes_that_are_allowed_through_are_still_recognised() -> None:
    for not_a_binding in (
        "Ctrl+Shift+Grave, X",  # a chord sequence
        "Ctrl+Shift+1 through Ctrl+Shift+9",  # a range
        "Alt+Shift+1 to Alt+Shift+9",  # the same range, spelled "to"
        "Shift+digit",  # a placeholder
        "Ctrl+Shift+",  # a sentence that continues
        "Ctrl+Shift+Grave",  # the leader itself
        "Shift+O",  # the second half of a leader chord
        "Alt+F",  # a menu mnemonic
        "Ctrl+JAWSKey+V",  # the reader's own modifier
        "Ctrl+N makes a rich text document.",  # bold that ran into the sentence
        "Ctrl+Left/Right",  # a slash pair is two bindings
        "Alt+arrows",  # a family, not a binding
        "Ctrl+Up",  # the control's own navigation
    ):
        assert not _is_a_single_chord(not_a_binding), not_a_binding
    for binding in ("Ctrl+Alt+V", "Alt+Shift+F1", "Ctrl+Shift+."):
        assert _is_a_single_chord(binding), binding


def test_the_shifted_face_of_a_key_is_the_same_key() -> None:
    """A guide may write either, because a keyboard has one key for both."""
    assert _normalise("Ctrl+Shift+>") == _normalise("Ctrl+Shift+.")
    assert _normalise("Ctrl+Shift+<") == _normalise("Ctrl+Shift+,")
    # And a modifier that merely ends in Shift is not a shifted face.
    assert _normalise("Ctrl+Shift+F1") == "ctrl+shift+f1"
