"""Insert Special Character, on QUILL's main frame.

Its own module rather than another method on
:class:`~quill.ui.main_frame_power_tools.PowerToolsActionsMixin`, because that
module is at its GATE-11 ceiling and the rule there is to extract rather than to
raise the number. ``PowerToolsActionsMixin`` inherits this, so the method name
and the ``power.insert_special_character`` command id are exactly where they
were.

What changed underneath them (2026-09-13): this command was a prompt asking for
a Unicode code point, and a code point is the right *escape hatch* and the wrong
front door -- knowing that an em dash is 2014 is a thing you look up. It now
opens the shared picker (:mod:`quill.ui.special_character_dialog`) over the
shared catalogue (:mod:`quill.core.special_characters`), whose search box takes
a code point as readily as a name, so nothing was lost by dropping the prompt.
QuillLite's Edit > Insert > Special Character opens the same dialog.
"""

from __future__ import annotations

from typing import Any

from quill.core.special_characters import inserted_message
from quill.ui.special_character_dialog import choose_special_character

__all__ = ["SpecialCharacterMixin"]


class SpecialCharacterMixin:
    """``power.insert_special_character``, on the main frame."""

    # Supplied by MainFrame / PowerToolsActionsMixin.
    frame: Any

    def insert_special_character(self) -> None:
        """Pick a character by name, by group, or by code point, and insert it."""
        character = choose_special_character(self.frame, announce_cb=self._announce)
        if character is None:
            return
        # The status line rather than silence: nothing else says what landed,
        # and half of this catalogue is invisible on the page.
        self._power_tools_insert_at_cursor(character, inserted_message(character))
