"""Insert Line Break, on QUILL's main frame (#1488).

Shift+Enter, which is the chord Word uses for the same thing, so nobody has to
learn a new one.

Why this needed a command at all: a Markdown hard break is a *marker at the end
of a line*, and both of its spellings are hostile to type by hand. Two trailing
spaces are invisible, inaudible and stripped by half the tools that touch a
file; a backslash is fine to read but nobody remembers it is the syntax. The
novelist who reported this had no way to write one except an HTML tag he
correctly expected to break, and spent two days finding that out.

The command writes whichever spelling
:attr:`~quill.core.settings.Settings.markdown_hard_break_style` names, and says
which one it used -- because the whole difficulty here is that you cannot see
what you just inserted.

Its own module under GATE-11: ``main_frame_power_tools`` is at its ceiling, and
this is inherited from there, so the command id and the method name sit exactly
where the registration table expects them.
"""

from __future__ import annotations

from typing import Any

from quill.core.markdown_breaks import hard_break_suffix

__all__ = ["LineBreakMixin"]

_SPOKEN = {
    "backslash": "Line break inserted, written as a backslash",
    "spaces": "Line break inserted, written as two spaces",
}


class LineBreakMixin:
    """``power.insert_line_break``, on the main frame."""

    # Supplied by MainFrame / PowerToolsActionsMixin.
    settings: Any

    def insert_line_break(self) -> None:
        """End this line and start the next one *without* starting a paragraph.

        The distinction Markdown makes and a plain Enter cannot: a blank line
        between two lines makes them two paragraphs, and a hard break makes them
        two lines of one. In prose that is the difference between a scene-break
        block and four paragraphs with gaps between them.
        """
        style = getattr(self.settings, "markdown_hard_break_style", "backslash")
        self._power_tools_insert_at_cursor(
            hard_break_suffix(style) + "\n",
            _SPOKEN.get(str(style), _SPOKEN["backslash"]),
        )
