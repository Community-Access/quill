"""Mode, theme, and the font: how a document *looks*, and what that must not cost.

Split from :mod:`quill.apps.lite_window` because every method here shares one
constraint that none of the file-handling methods have: **presentation must
never become content.**

That is not a slogan, it is three specific traps this module exists to avoid:

* **The theme must not reach the file.** A dark theme colours the whole story
  through the Text Object Model, and the colour is stripped back to
  ``tomAutoColor`` before every save and restored afterwards -- so dark mode
  cannot leak light grey text into somebody's document, and a *failed* save
  cannot leave the window unreadable.
* **The theme must not become an edit.** Recolouring is done with ``_loading``
  raised, so the resulting ``EVT_TEXT`` is not mistaken for typing and the
  document is not marked modified by a change of theme.
* **The text size must not re-level the headings.** In rich text, run point
  sizes *are* the heading ladder. Making text bigger by rewriting them would
  silently turn every Heading 2 into a Heading 1. So in rich mode the size
  control is a *view zoom* (``EM_SETZOOM``) and the runs are never touched;
  only plain mode, which has no ladder, changes the control's font.

Switching between plain and rich lived here too, while it was a one-line
question. It converts now, in both directions, and moved to
:mod:`quill.apps.lite_window_mode` -- what a document *is* turned out to be a
different question from what it looks like.
"""

from __future__ import annotations

import wx

from quill.core.editor_font import editor_points_for, sets_font, zoom_for
from quill.ui.richedit_editing import PLAIN, RICH
from quill.ui.richedit_rtf_surface import RichEditRtfError

__all__ = ["DocumentAppearanceMixin"]


class DocumentAppearanceMixin:
    """Text mode, theme colours, and the editor font."""

    def _set_mode_internal(self, mode: str) -> None:
        """Switch the control's text mode. The buffer must be empty first."""
        self.control.ChangeValue("")
        self.doc_text.invalidate()  # ChangeValue raises no text event
        self.editor.set_text_mode(mode)
        self._apply_editor_font()
        self._apply_editor_help()
        self._update_title()
        self._touch_status()
        # A new document (or the same one in the other mode) is a new structure.
        # Forgetting the old caret surroundings is what stops the first arrow
        # key in the new buffer from announcing a heading the user never left.
        self.reset_structure_announcer()

    def _apply_editor_font(self) -> None:
        """Apply the chosen face and size, through the rule QUILL now shares.

        In a rich document the size is a **zoom** and ``SetFont`` is not called
        at all. It used to be called with the ladder's body size, on the theory
        that passing the body size was harmless -- but wxMSW applies ``SetFont``
        to the *whole control*, existing runs included, so every ``Ctrl+=``,
        every dark-mode toggle and every font change flattened a Heading 1 and a
        body paragraph to one size, and heading navigation and the headings list
        went with them. Fixed 2026-09-16 (bad.md R5, P1.3).

        The decision itself is :func:`quill.core.editor_font.sets_font`, so both
        editors answer it from one place rather than getting it right twice.
        """
        settings = self.app.settings
        rich = self.editor.mode == RICH
        if sets_font(rich=rich):
            self.control.SetFont(
                wx.Font(
                    int(editor_points_for(settings.font_size, rich=rich)),
                    wx.FONTFAMILY_DEFAULT,
                    wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL,
                    faceName=settings.font_name,
                )
            )
        self.editor.set_zoom(*zoom_for(settings.font_size, rich=rich))

    def theme_colours(self) -> tuple[wx.Colour, wx.Colour, wx.Colour]:
        """``(text, page, chrome)`` for the current theme."""
        if self.app.settings.theme == "dark":
            return wx.Colour(230, 230, 230), wx.Colour(30, 30, 30), wx.Colour(45, 45, 45)
        return (
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT),
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW),
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE),
        )

    def apply_theme(self) -> None:
        text_colour, page, chrome = self.theme_colours()
        self.control.SetBackgroundColour(page)
        self.editor.set_background_color(page.Red(), page.Green(), page.Blue())
        if self.editor.mode == PLAIN:
            self.control.SetForegroundColour(text_colour)
        else:
            self._apply_rich_theme_colour()
        self.SetBackgroundColour(chrome)
        self.status_panel.SetBackgroundColour(chrome)
        for button in self._status_buttons.values():
            button.SetBackgroundColour(chrome)
            button.SetForegroundColour(text_colour)
        self.status_panel.Refresh()
        self.control.Refresh()
        self.Refresh()

    def _apply_rich_theme_colour(self) -> None:
        if self.editor.mode != RICH or not self.editor.rtf_available():
            return
        text_colour, _page, _chrome = self.theme_colours()
        if self.app.settings.theme == "dark":
            self._set_whole_document_colour((
                text_colour.Red(),
                text_colour.Green(),
                text_colour.Blue(),
            ))
        else:
            self._set_whole_document_colour(None)

    def _set_whole_document_colour(self, rgb: tuple[int, int, int] | None) -> None:
        """Recolour the story without the change counting as an edit."""
        if self.editor.mode != RICH or not self.editor.rtf_available():
            return
        was_loading = self._loading
        self._loading = True
        try:
            self.editor.set_document_color(rgb)
        except RichEditRtfError:
            pass  # a theme is presentation; failing to apply it is not fatal
        finally:
            self._loading = was_loading
