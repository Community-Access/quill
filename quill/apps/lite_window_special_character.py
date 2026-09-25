"""Insert Special Character, on a QUILL Lite document window.

Its own module for the reason QUILL's half of this feature has one
(:mod:`quill.ui.main_frame_special_character`): the module it grew out of is at
its GATE-11 ceiling, and the rule there is to extract rather than to raise the
number. :class:`~quill.apps.lite_window_commands.DocumentCommandsMixin` inherits
this, so the command table's ``cmd_insert_special_character`` resolves exactly
where it did.

The dialog and the catalogue are both shared with QUILL
(:mod:`quill.ui.special_character_dialog`,
:mod:`quill.core.special_characters`), so neither editor can offer a character
the other cannot reach, and neither can arrange the same list differently.
"""

from __future__ import annotations

from quill.core.markdown_breaks import hard_break_suffix
from quill.core.special_characters import inserted_message
from quill.ui.special_character_dialog import choose_special_character

__all__ = ["DocumentSpecialCharacterMixin"]

_BREAK_SPOKEN = {
    "backslash": "Line break inserted, written as a backslash",
    "spaces": "Line break inserted, written as two spaces",
}


class DocumentSpecialCharacterMixin:
    """``Edit > Insert > Special Character...``, on a document window."""

    def cmd_insert_special_character(self) -> None:
        """Put in a character the keyboard has no key for.

        Search by name, code point or keyword, or browse one of fifteen groups.
        The read-back is the whole accessibility of the command: a screen reader
        says nothing when an app writes text on its own behalf, and most of this
        catalogue is invisible on the page, so without it this is a keystroke
        after which something you cannot see may or may not have appeared.
        """
        character = choose_special_character(self, announce_cb=self._announce)
        if character is None:
            self.control.SetFocus()
            return
        self.control.WriteText(character)
        self._set_modified(True)
        self._announce(inserted_message(character))
        self._touch_status()
        self.control.SetFocus()

    def cmd_insert_line_break(self) -> None:
        """End the line without starting a paragraph (#1488).

        Shift+Enter, as in Word. A blank line between two lines makes them two
        paragraphs; a hard break makes them two lines of one, which in prose is
        the difference between a scene-break block and four paragraphs with gaps
        between them.

        It needs a command because both spellings of a Markdown hard break are
        impossible to type with confidence: two trailing spaces are invisible
        and inaudible and get stripped by half the tools that touch a file, and
        the backslash is syntax nobody remembers. The announcement names which
        one went in, because that is precisely what you cannot check.
        """
        style = getattr(self.app.settings, "markdown_hard_break_style", "backslash")
        self.control.WriteText(hard_break_suffix(style) + chr(10))
        self._set_modified(True)
        self._announce(_BREAK_SPOKEN.get(str(style), _BREAK_SPOKEN["backslash"]))
        self._touch_status()
