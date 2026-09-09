"""The View menu: how the document looks, and how big it is.

Split from :mod:`quill.apps.lite_window_commands` because it is a different
question. That module is about the document -- open it, save it, search it,
format it. This one changes nothing in the document at all: theme, wrap, text
size, the editor font, the status bar, and the Preferences window that gathers
them. A change here is never an edit and never marks the file modified.

Two rules the whole menu obeys:

* **Every window, at once.** A setting is the app's, not the window's, so each
  change is saved and then pushed through
  :meth:`~quill.apps.lite.QuillLiteApp.reapply_settings` to every open document.
  A theme that applied only to the window you were in would be a bug people
  reported as "it forgets".
* **The view, not the text.** In rich text the size control is a *zoom*: run
  point sizes are the heading ladder, so enlarging by rewriting them would
  silently re-level every heading in the document.
"""

from __future__ import annotations

import wx

from quill.apps.lite_preferences import edit_preferences
from quill.core.lite import APP_NAME
from quill.core.metrics import compute_document_stats
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentViewCommandsMixin"]

#: What Reset Text Size resets to -- the settings default, stated once.
_DEFAULT_POINTS = 12


class DocumentViewCommandsMixin:
    """The ``cmd_*`` handlers for the View menu.

    Mixed into :class:`~quill.apps.lite_window.DocumentFrame`, which supplies
    ``app``, ``control``, ``_announce`` and the status-bar methods.
    """

    def cmd_toggle_dark(self) -> None:
        settings = self.app.settings
        settings.theme = "system" if settings.theme == "dark" else "dark"
        self.app.save_settings()
        self.app.reapply_settings()
        self._announce("Dark mode on" if settings.theme == "dark" else "Dark mode off")

    def cmd_toggle_wrap(self) -> None:
        settings = self.app.settings
        settings.word_wrap = not settings.word_wrap
        self.app.save_settings()
        self.app.reapply_settings()
        self._announce("Word wrap on" if settings.word_wrap else "Word wrap off")

    def _set_text_size(self, points: int) -> None:
        """Change the text size in every window, and say what it became."""
        settings = self.app.settings
        settings.font_size = points
        settings.normalized()  # clamps into range, so 4 and 400 both land somewhere legible
        self.app.save_settings()
        self.app.reapply_settings()
        self._announce(f"{settings.font_size} point")

    def cmd_zoom_in(self) -> None:
        self._set_text_size(self.app.settings.font_size + 1)

    def cmd_zoom_out(self) -> None:
        self._set_text_size(self.app.settings.font_size - 1)

    def cmd_zoom_reset(self) -> None:
        self._set_text_size(_DEFAULT_POINTS)

    def cmd_editor_font(self) -> None:
        """Choose the editor's face and size for every window."""
        settings = self.app.settings
        data = wx.FontData()
        data.SetInitialFont(
            wx.Font(
                settings.font_size,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                faceName=settings.font_name,
            )
        )
        with wx.FontDialog(self, data) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            font = dialog.GetFontData().GetChosenFont()
        settings.font_name = font.GetFaceName()
        settings.font_size = font.GetPointSize()
        settings.normalized()
        self.app.save_settings()
        self.app.reapply_settings()
        self._announce(f"Editor font {settings.font_name}, {settings.font_size} point")

    def cmd_preferences(self) -> None:
        """Every setting in one window, including the two with no menu item."""
        changed = edit_preferences(self, self.app.settings, announce=self._announce)
        self.control.SetFocus()
        if not changed:
            return
        self.app.save_settings()
        self.app.reapply_settings()
        self._announce("Preferences saved")

    def cmd_statistics(self) -> None:
        """Speak the document's size. The same numbers the status bar carries,
        said out loud, because a listener is not watching it."""
        stats = compute_document_stats(self.control.GetValue())
        self._announce(
            f"{stats.words:,} words, {stats.characters:,} characters, {stats.lines:,} lines"
        )

    def cmd_focus_status_bar(self) -> None:
        """F6: move into the status bar. Escape there comes back here."""
        self.focus_status_bar()

    # ------------------------------------------------------------------ #
    # Which features exist at all
    # ------------------------------------------------------------------ #

    def cmd_customize_features(self) -> None:
        """Turn whole areas of QuillLite on or off.

        The way QuillLite stays small is not that it does little -- it is that
        somebody who does not want rich text can remove the Format menu
        *entirely* rather than learn to ignore it. This is also where the three
        areas that ship switched off are found, which is the difference between
        "off by default" and "hidden".
        """
        from quill.core.lite.features import AREAS
        from quill.ui.app_features_dialog import AppFeaturesDialog

        dialog = AppFeaturesDialog(
            self,
            app_title=APP_NAME,
            areas=AREAS,
            settings=self.app.features,
            announce_cb=self._announce,
        )
        if not dialog.show_modal():
            self.control.SetFocus()
            return
        self.app.save_features()
        self.app.rebuild_all_menus()
        self.control.SetFocus()
        self._announce("Features saved. The menus have been rebuilt.")

    # ------------------------------------------------------------------ #
    # Finding a command without knowing its key
    # ------------------------------------------------------------------ #

    def cmd_command_palette(self) -> None:
        """Every command QuillLite has, searchable, with its key beside it.

        A menu bar answers "what is under Format?"; a palette answers "how do I
        sort lines?", which is the question somebody actually has. It is also
        the only surface that shows a command's key *next to its name* while you
        are looking for the command -- which is how a key gets learned.
        """
        from quill.ui.palette import CommandPaletteDialog

        palette = CommandPaletteDialog(
            self,
            self.app.command_registry(self),
            announce_fn=self._announce,
            binding_for=self.app.binding_for,
        )
        palette.show_modal_and_run()
        self.control.SetFocus()

    def cmd_go_to_anything(self) -> None:
        """One box for commands, headings and bookmarks together.

        Off by default: the palette, the headings list and the bookmark list each
        already answer their own part of this, and a second front door before
        anybody asked for one is a second thing to explain.
        """
        from quill.ui.palette import GoToAnythingDialog

        # The dialog speaks in line numbers and calls back through
        # go_to_line_number, so headings are converted on the way in rather than
        # the dialog being taught about offsets.
        headings: list[tuple[str, int]] = []
        if self.editor.mode == RICH:
            text = self.control.GetValue()
            headings = [
                (heading, text.count("\n", 0, min(offset, len(text))) + 1)
                for offset, _level, heading in self.editor.all_headings()
            ]
        dialog = GoToAnythingDialog(
            self,
            self.app.command_registry(self),
            headings=headings,
            announce_fn=self._announce,
            binding_for=self.app.binding_for,
        )
        dialog.show_modal_and_run(self)
        self.control.SetFocus()
