"""Word's four alignment keys, in QUILL.

The first pass of bad.md said QUILL had no alignment but Justify. That was
wrong, and the truth is a different defect: ``format_align`` has handled all
four since the hidden-codes work, in rich text *and* Markdown -- but only
Justify was a registered command. Left, Centre and Right lived in the
Format > Align submenu and nowhere else, so they had no key, no palette entry,
no row in the generated keyboard reference, and no way to be rebound. The same
shape as Underline's hard-coded ``Ctrl+U``: a capability that exists and cannot
be reached.

So this is a registration change, not a new feature. What it buys is Word's
four keys -- ``Ctrl+L``, ``Ctrl+E``, ``Ctrl+R``, ``Ctrl+J`` -- which QUILL Lite
has always had and QUILL spent on nothing, a media command and a temporary
bookmark.

Justify also stopped being two implementations of one verb: ``format.justify``
had its own handler while the Align submenu's Justify row called
``format_align("justify")``, and only the second knew how to write a Markdown
alignment div (bad.md 7.1).
"""

from __future__ import annotations

import pytest

# -- the keys, which is what actually changed ------------------------------------


def test_the_four_chords_are_word_s_and_quilllite_s() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    lite = {handler: key for _m, _label, key, handler, _flag in COMMANDS if key}
    for command_id, handler, chord in (
        ("format.align_left", "cmd_align_left", "Ctrl+L"),
        ("format.align_center", "cmd_align_center", "Ctrl+E"),
        ("format.align_right", "cmd_align_right", "Ctrl+R"),
        ("format.justify", "cmd_align_justify", "Ctrl+J"),
    ):
        assert DEFAULT_KEYMAP[command_id] == chord
        assert lite[handler] == chord, "one alignment, two habits"


def test_the_chords_they_displaced_landed_somewhere_real() -> None:
    # A moved command that quietly becomes keyless is the failure this whole
    # exercise exists to prevent, so the two displaced ones are asserted too.
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["navigate.set_temp_bookmark"] == "Ctrl+Alt+J"
    assert DEFAULT_KEYMAP["media.sound_enhancements"] == "Ctrl+Shift+Grave, 1"


def test_no_alignment_chord_is_claimed_twice() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    for chord in ("Ctrl+L", "Ctrl+E", "Ctrl+R", "Ctrl+J"):
        owners = [cmd for cmd, bound in DEFAULT_KEYMAP.items() if bound == chord]
        assert len(owners) == 1, f"{chord} is claimed by {owners}"


# -- the registration, which is the defect that was fixed ------------------------


def test_all_four_are_registered_commands_not_menu_rows() -> None:
    """Left, Centre and Right were menu-only: no key, no palette, no reference."""
    from quill.core.keymap import DEFAULT_KEYMAP

    for command_id in (
        "format.align_left",
        "format.align_center",
        "format.align_right",
        "format.justify",
    ):
        assert command_id in DEFAULT_KEYMAP
        assert DEFAULT_KEYMAP[command_id], f"{command_id} is registered but keyless"


def test_all_four_appear_in_the_generated_keyboard_reference() -> None:
    from pathlib import Path

    reference = Path("docs/keyboard-reference.md").read_text(encoding="utf-8")
    for command_id in (
        "format.align_left",
        "format.align_center",
        "format.align_right",
        "format.justify",
    ):
        assert command_id in reference, f"{command_id} is missing from the keyboard reference"


def test_justify_is_one_implementation_not_two() -> None:
    """``format_justify`` delegates; it does not re-implement ``format_align``.

    The two were separate until 2026-09-16, and only ``format_align`` knew how
    to write a Markdown alignment div -- so the registered command was the
    weaker of the pair (bad.md 7.1).
    """
    from quill.ui.main_frame_rich_paragraph import RichParagraphMixin

    names = RichParagraphMixin.format_justify.__code__.co_names
    assert "format_align" in names


def test_alignment_has_one_handler_for_all_four() -> None:
    from quill.ui.main_frame_format_codes import FormatCodesMixin
    from quill.ui.main_frame_rich_paragraph import RichParagraphMixin

    assert callable(FormatCodesMixin.format_align)
    # And no second family of per-direction handlers grew back beside it.
    for gone in ("format_align_left", "format_align_center", "format_align_right"):
        assert not hasattr(RichParagraphMixin, gone), (
            f"{gone} is a second implementation of a verb format_align already owns"
        )


@pytest.mark.parametrize(
    ("command_id", "how"),
    (
        ("format.align_left", "left"),
        ("format.align_center", "center"),
        ("format.align_right", "right"),
    ),
)
def test_each_direction_is_registered_against_the_shared_handler(command_id: str, how: str) -> None:
    # The registration passes `how` through to format_align by default argument;
    # a lambda that captured the loop variable by reference would bind all three
    # to "right", which is the classic version of this bug.
    import inspect

    from quill.ui import main_frame_commands

    source = inspect.getsource(main_frame_commands)
    assert f'("{command_id}", ' in source
    assert f'"{how}"' in source
