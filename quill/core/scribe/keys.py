"""Every QUILL Scribe for Documents command id, for the keymap (PRD 12).

QUILL registers these from :data:`quill.ui.main_frame_scribe.ROWS` when its
menus are built; listing them here puts each in ``DEFAULT_KEYMAP`` so the
Keymap Editor offers it, the keyboard reference names it, and QUILL Lite's
parity table (``commands_scribe.SCRIBE_EQUIVALENTS``) maps onto ids QUILL has.
None has a default chord, in either editor: every one is a once-in-a-while
command reached from its menu and the Command Palette (rule 9), and the
family gate records why.

wx-free; a test asserts this list and ``ROWS`` agree.
"""

from __future__ import annotations

COMMAND_IDS: tuple[str, ...] = (
    "scribe.convert_file",
    "scribe.convert_this",
    "scribe.convert_link",
    "scribe.my_documents",
    "scribe.conversions",
    "scribe.status",
    "scribe.repeat",
    "scribe.replace_finished",
    "scribe.sign_in",
    "scribe.sign_out",
    "scribe.account",
    "scribe.options",
    "scribe.about",
    "scribe.file_documents",
    "scribe.import",
    "scribe.export",
    "scribe.braille",
    "scribe.window",
)


def default_bindings() -> dict[str, str]:
    """``{command id: ""}``: in the keymap, with no default chord."""
    return dict.fromkeys(COMMAND_IDS, "")


__all__ = ["COMMAND_IDS", "default_bindings"]
