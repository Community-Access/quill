"""Rule 1, as a check: what does a Word habit do here?

The keys in somebody's hands were put there by the programs they used before
this one. Rule 1 says Microsoft's key wins where Word, WordPad or Notepad bind
one for a function both our editors have -- and this is that list, checked
against both keymaps rather than believed.

It found the last disagreement on 2026-09-18: QUILL carried Word's ``F12`` for
Save As (and ``Ctrl+F12`` / ``Ctrl+Shift+F12`` for Open and Print) and QuillLite
did not. All three were free there, so rule 5 applied -- adopted as aliases, with
nothing moved and both primaries still working.

The ``--`` rows are as deliberate as the rest, and each says why.
"""

from __future__ import annotations

from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP
from quill.core.lite.commands import COMMANDS
from quill.core.lite.keymap import DEFAULT_ALIASES as LITE_ALIASES

#: ``chord -> what Word, WordPad or Notepad does with it``. Only chords for
#: functions our editors actually have; Word's mail merge is not our problem.
MICROSOFT: dict[str, str] = {
    "Ctrl+N": "New",
    "Ctrl+O": "Open",
    "Ctrl+S": "Save",
    "Ctrl+P": "Print",
    "Ctrl+Z": "Undo",
    "Ctrl+Y": "Redo",
    "Ctrl+F": "Find",
    "Ctrl+H": "Replace",
    "Ctrl+G": "Go To",
    "F3": "Find Next",
    "Shift+F3": "Find Previous",
    "F5": "Date and time (Notepad)",
    "F7": "Spelling (Word)",
    "F12": "Save As (Word)",
    "Ctrl+F12": "Open (Word)",
    "Ctrl+Shift+F12": "Print (Word)",
    "Ctrl+B": "Bold",
    "Ctrl+I": "Italic",
    "Ctrl+L": "Align left",
    "Ctrl+E": "Align centre",
    "Ctrl+R": "Align right",
    "Ctrl+J": "Justify",
    "Ctrl+1": "Single line spacing",
    "Ctrl+2": "Double line spacing",
    "Ctrl+5": "One-and-a-half line spacing",
    "Ctrl+Shift+>": "Grow font",
    "Ctrl+Shift+<": "Shrink font",
    "Ctrl+Shift+F": "Font",
    "Ctrl+K": "Insert hyperlink",
    "Ctrl+W": "Close document",
    "Shift+F7": "Thesaurus (Word)",
}

#: Chords **QUILL** leaves to the control, each with its reason.
#:
#: QuillLite binds the clipboard four itself, and is right to: it plays an
#: earcon for cut, copy, paste and delete, because those change the document
#: and change *nothing a screen reader announces* -- no focus move, no control
#: name -- so the feedback is a sound or it is nothing. QUILL routes them
#: through wx's stock ids and hangs its cues off the control's own events
#: instead. Two routes to the same place, which is why this list is one
#: editor's rather than both.
NOT_OURS: dict[str, str] = {
    "Ctrl+X": "The control's own Cut. wx gives it the platform label, the "
    "accelerator and the handler from wx.ID_CUT, so binding it again would be a "
    "second owner for one key.",
    "Ctrl+C": "As Ctrl+X: the control's own Copy, from wx.ID_COPY.",
    "Ctrl+V": "As Ctrl+X: the control's own Paste, from wx.ID_PASTE.",
    "Ctrl+A": "As Ctrl+X: the control's own Select All, from wx.ID_SELECTALL.",
    "Ctrl+Home": "The control's own navigation, which is what every other edit "
    "field on the machine does with it.",
    "Ctrl+End": "As Ctrl+Home: the control's own navigation.",
}

#: The same rows, normalised, for the rule-2 comparison below.
NOT_OURS_KEYS = frozenset(chord.replace(" ", "").lower() for chord in NOT_OURS)

#: Shifted faces of one physical key: a keyboard has one key for ``.`` and
#: ``>``, and wx spells the unshifted one.
_SHIFTED = {">": ".", "<": ",", "?": "/", "+": "=", "_": "-", ":": ";"}


def _normalise(chord: str) -> str:
    text = chord.replace(" ", "").lower()
    if text and text[-1] in _SHIFTED:
        text = text[:-1] + _SHIFTED[text[-1]]
    return text


def _quill_chords() -> dict[str, str]:
    claimed: dict[str, str] = {}
    for mapping in (DEFAULT_KEYMAP, DEFAULT_ALIASES):
        for command_id, chord in mapping.items():
            if isinstance(chord, str) and chord:
                claimed.setdefault(_normalise(chord), command_id)
    return claimed


def _lite_chords() -> dict[str, str]:
    claimed: dict[str, str] = {}
    for row in COMMANDS:
        chord = str(row[2]) if len(row) > 2 else ""
        handler = str(row[3]) if len(row) > 3 else ""
        if chord and handler:
            claimed.setdefault(_normalise(chord), handler)
    for handler, chord in LITE_ALIASES.items():
        if chord:
            claimed.setdefault(_normalise(chord), handler)
    return claimed


#: Microsoft chords one editor has and the other genuinely cannot, with the
#: reason. Rule 1 only applies to a function **both** editors have.
ONE_EDITOR_ONLY: dict[str, str] = {
    "Shift+F7": "Word's Thesaurus. QUILL has one; QuillLite has no thesaurus at "
    "all, which is the allowed direction under rule 10 -- the big product may be "
    "ahead of the small one.",
}


def test_every_microsoft_habit_lands_somewhere_in_quill() -> None:
    claimed = _quill_chords()
    missing = sorted(
        f"{chord} ({meaning})"
        for chord, meaning in MICROSOFT.items()
        if _normalise(chord) not in claimed
    )
    assert not missing, (
        "chords a Word, WordPad or Notepad habit would press, which QUILL does "
        "not bind (rule 1):\n  " + "\n  ".join(missing)
    )


def test_every_microsoft_habit_lands_somewhere_in_quilllite() -> None:
    claimed = _lite_chords()
    missing = sorted(
        f"{chord} ({meaning})"
        for chord, meaning in MICROSOFT.items()
        if _normalise(chord) not in claimed and chord not in ONE_EDITOR_ONLY
    )
    assert not missing, (
        "chords a Word, WordPad or Notepad habit would press, which QuillLite does "
        "not bind (rule 1):\n  " + "\n  ".join(missing)
    )


def test_quill_leaves_the_controls_own_chords_to_the_control() -> None:
    """Binding Cut again would give one key two owners, and one of them loses."""
    quill = _quill_chords()
    stolen = [
        f"QUILL binds {chord} to {quill[_normalise(chord)]} -- {reason}"
        for chord, reason in sorted(NOT_OURS.items())
        if _normalise(chord) in quill
    ]
    assert not stolen, "\n  ".join(stolen)


def test_the_clipboard_four_still_answer_in_quilllite() -> None:
    """Different mechanism, same keys -- which is what rule 2 actually asks."""
    lite = _lite_chords()
    for chord in ("Ctrl+X", "Ctrl+C", "Ctrl+V", "Ctrl+A"):
        assert _normalise(chord) in lite, f"QuillLite lost {chord}"


def test_the_two_editors_agree_about_every_microsoft_chord() -> None:
    """Rule 2: the command both products have keeps the chord, in both."""
    quill = _quill_chords()
    lite = _lite_chords()
    disagreements: list[str] = []
    for chord in sorted(MICROSOFT):
        if chord in ONE_EDITOR_ONLY:
            continue
        key = _normalise(chord)
        if key in NOT_OURS_KEYS:
            # The control owns it in QUILL and QuillLite binds it for its
            # earcon: the key answers in both, which is the question here.
            continue
        if key in quill and key not in lite:
            disagreements.append(f"{chord}: QUILL has it, QuillLite does not")
        if key in lite and key not in quill:
            disagreements.append(f"{chord}: QuillLite has it, QUILL does not")
    assert not disagreements, "\n  ".join(disagreements)


def test_every_one_editor_exemption_argues_its_case() -> None:
    for chord, reason in sorted(ONE_EDITOR_ONLY.items()):
        assert chord in MICROSOFT, f"{chord} is exempted from a list it is not on"
        assert len(reason) > 40, chord


def test_the_lists_are_actually_being_compared() -> None:
    assert len(MICROSOFT) >= 25
    assert len(_quill_chords()) > 300
    assert len(_lite_chords()) > 100
