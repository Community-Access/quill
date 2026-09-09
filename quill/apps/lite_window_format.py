"""The Format menu: WordPad's, key for key.

Split from :mod:`quill.apps.lite_window_commands` because it is the one menu
with a rule of its own, and the rule runs through every handler here:
**formatting exists only in rich text, and saying so is part of the feature.**

``_require_rich`` is therefore not a guard clause, it is the product: a
formatting key pressed in a plain text document says "Not available in plain
text. Press Control Shift M to switch to rich text." A command that quietly does
nothing is indistinguishable, to a listener, from a key that is not bound at
all -- and they would have no way to find out which.

The keys are WordPad's, deliberately and without improvement: Ctrl+B, I and U;
Ctrl+L, E, R and J for the four alignments; Ctrl+Shift+L for bullets; Ctrl+1,
Ctrl+5 and Ctrl+2 for single, one-and-a-half and double spacing; and
Ctrl+Shift+> and Ctrl+Shift+< to grow and shrink the selection. Somebody moving
from WordPad should not have to learn anything.

Two additions WordPad does not have, both from QUILL: the **heading ladder**
(Ctrl+Alt+1 to 4, Ctrl+Alt+0 for body text), and **Describe Formatting**
(Ctrl+Shift+D), which answers "what am I standing in?" -- the question a
formatted document raises and a screen reader cannot answer on its own.
"""

from __future__ import annotations

import wx

from quill.ui.richedit_editing import (
    LINE_SPACING_DOUBLE,
    LINE_SPACING_ONE_AND_A_HALF,
    LINE_SPACING_SINGLE,
    PLAIN,
    RICH,
)
from quill.ui.richedit_rtf_surface import RichEditRtfError

__all__ = ["DocumentFormatCommandsMixin"]


class DocumentFormatCommandsMixin:
    """The ``cmd_*`` handlers for the Format menu.

    Mixed into :class:`~quill.apps.lite_window.DocumentFrame`, which supplies
    ``control``, ``editor``, ``_announce`` and ``_set_modified``.
    """

    def _require_rich(self) -> bool:
        """True when formatting can run; otherwise say why, and how to fix it."""
        if self.editor.mode != RICH:
            self._announce(
                "Not available in plain text. Press Control Shift M to switch to rich text."
            )
            return False
        if not self.editor.rtf_available():
            self._announce("Rich text formatting is unavailable on this system")
            return False
        return True

    def _toggle_attr(self, attr: str, label: str) -> None:
        if not self._require_rich():
            return
        try:
            state = self.editor.toggle_font_attr(attr)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(f"{label} on" if state else f"{label} off")

    def cmd_bold(self) -> None:
        self._toggle_attr("Bold", "Bold")

    def cmd_italic(self) -> None:
        self._toggle_attr("Italic", "Italic")

    def cmd_underline(self) -> None:
        self._toggle_attr("Underline", "Underline")

    def _heading(self, level: int) -> None:
        if not self._require_rich():
            return
        try:
            self.editor.set_heading(level)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(f"Heading {level}" if level else "Body text")

    def cmd_heading_0(self) -> None:
        self._heading(0)

    def cmd_heading_1(self) -> None:
        self._heading(1)

    def cmd_heading_2(self) -> None:
        self._heading(2)

    def cmd_heading_3(self) -> None:
        self._heading(3)

    def cmd_heading_4(self) -> None:
        self._heading(4)

    def _align(self, how: str, label: str) -> None:
        if not self._require_rich():
            return
        try:
            self.editor.set_alignment(how)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(label)

    def cmd_align_left(self) -> None:
        self._align("left", "Aligned left")

    def cmd_align_center(self) -> None:
        self._align("center", "Centred")

    def cmd_align_right(self) -> None:
        self._align("right", "Aligned right")

    def cmd_align_justify(self) -> None:
        self._align("justify", "Justified")

    def cmd_toggle_bullets(self) -> None:
        """WordPad's bullet button, on WordPad's chord (Ctrl+Shift+L)."""
        if not self._require_rich():
            return
        wanted = not self.editor.bullets_at_caret()
        try:
            self.editor.set_bullets(wanted)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce("Bullets on" if wanted else "Bullets off")

    def _line_spacing(self, rule: int, label: str) -> None:
        if not self._require_rich():
            return
        try:
            self.editor.set_line_spacing(rule)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(label)

    def cmd_spacing_single(self) -> None:
        self._line_spacing(LINE_SPACING_SINGLE, "Single spacing")

    def cmd_spacing_one_half(self) -> None:
        self._line_spacing(LINE_SPACING_ONE_AND_A_HALF, "One and a half spacing")

    def cmd_spacing_double(self) -> None:
        self._line_spacing(LINE_SPACING_DOUBLE, "Double spacing")

    def _step_font(self, *, larger: bool) -> None:
        """WordPad's Ctrl+Shift+> and Ctrl+Shift+<: resize the selection itself.

        Not the same thing as the View menu's text size, and the difference is
        worth knowing: this changes the *document*, so it is an edit and it is
        saved; the View menu changes the *view*, so it is neither.
        """
        if not self._require_rich():
            return
        try:
            size = self.editor.step_font_size(larger=larger)
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(f"{size:g} point")

    def cmd_grow_font(self) -> None:
        self._step_font(larger=True)

    def cmd_shrink_font(self) -> None:
        self._step_font(larger=False)

    def cmd_selection_font(self) -> None:
        """Set the face and size of the selection only (rich mode)."""
        if not self._require_rich():
            return
        with wx.FontDialog(self, wx.FontData()) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            font = dialog.GetFontData().GetChosenFont()
        try:
            self.editor.set_font_name(font.GetFaceName())
            self.editor.set_font_size(font.GetPointSize())
        except RichEditRtfError as exc:
            self._announce(str(exc))
            return
        self._set_modified(True)
        self._announce(f"{font.GetFaceName()}, {font.GetPointSize()} point")

    def cmd_describe(self) -> None:
        """Say what the formatting at the cursor is -- QUILL's Describe Formatting."""
        if self.editor.mode != RICH:
            self._announce("Plain text")
            return
        try:
            self._announce(self.editor.caret_format_description())
        except RichEditRtfError as exc:
            self._announce(str(exc))

    def cmd_switch_mode(self) -> None:
        self.switch_mode(PLAIN if self.editor.mode == RICH else RICH)
