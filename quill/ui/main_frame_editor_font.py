"""The face and size QUILL's editor draws in -- the capability it did not have.

Until 2026-09-16 no code in ``quill/ui`` called ``SetFont`` on an editor
control. Every call site was a dialog heading or a print DC, ``Settings`` had no
font name and no font size, and there was no zoom command and no text-size
command: QUILL rendered in whatever font wx picked, forever. For a product whose
audience includes low-vision users that is not a missing preference, it is a
viability failure -- and it is the largest of the sixteen ways QuillLite was
ahead of the editor, which is exactly backwards (bad.md 4.3, P0.6a).

The one thing called "Font" was ``format.font_dialog``, labelled "&More Font
Options...", which refused outside Markdown, wrote hidden Markdown format codes
rather than changing anything you could see, and had no key.

Five commands, on Notepad's and Word's keys:

* **Editor Font** (``Ctrl+Alt+F``) -- the face and size for every tab, through
  the system font chooser.
* **Increase / Decrease / Reset Text Size** (``Ctrl+=``, ``Ctrl+-``,
  ``Ctrl+0``) -- Notepad's three, so the size can be changed without leaving
  the document.
* **Font for Selection** (``Ctrl+Shift+F``) -- Word's key, which QUILL spent on
  Search in Files; that moved to ``Ctrl+Alt+Shift+F`` in the same change.

The rich/plain split is :mod:`quill.core.editor_font` and is the part that is
easy to get wrong: in a rich document the run point sizes *are* the heading
ladder, so ``SetFont`` would flatten a Heading 1 and a body paragraph to one
size and the headings list would follow it down. There the same keys drive the
view zoom instead, which scales what is drawn and writes nothing.
"""

from __future__ import annotations

from typing import Any

from quill.core.editor_font import (
    DEFAULT_FONT_POINTS,
    clamp_font_points,
    editor_points_for,
    sets_font,
    zoom_for,
)
from quill.core.i18n import _

__all__ = ["EditorFontMixin"]


class EditorFontMixin:
    """Editor Font, Font for Selection, and the three text-size keys."""

    # -- wiring ------------------------------------------------------------- #

    def register_editor_font_commands(self) -> None:
        """The five commands, registered by the module that implements them.

        Here rather than in ``main_frame_commands.py`` for the same reason
        :meth:`register_numbered_bookmark_commands` is where it is: the table,
        the menu rows and the handlers stay in one file, so a key that moves
        moves once and nothing is left advertising the old one.
        """
        for command_id, label, handler in (
            ("view.text_size_up", "Increase Text Size", self.increase_text_size),
            ("view.text_size_down", "Decrease Text Size", self.decrease_text_size),
            ("view.text_size_reset", "Reset Text Size", self.reset_text_size),
            ("format.editor_font", "Font...", self.choose_editor_font),
            ("format.selection_font", "Font for Selection...", self.choose_selection_font),
        ):
            self.commands.register(command_id, label, handler, self._binding_for(command_id))

    def add_font_menu_items(self, format_menu: Any) -> None:
        """The two Format-menu rows, appended and bound.

        WordPad and Notepad both put Font on the Format menu and Word puts it
        on Ctrl+Shift+F. QUILL's Format menu had no row saying "Font" at all --
        only "More Font Options...", which refuses outside Markdown and writes
        hidden format codes rather than changing anything you can see, so the
        menu never offered the thing the word means (bad.md M2, 4.3).
        """
        wx = self._wx
        self._id_editor_font = wx.NewIdRef()
        self._id_selection_font = wx.NewIdRef()
        format_menu.Append(
            self._id_editor_font,
            self._menu_label(_("&Font..."), "format.editor_font"),
        )
        format_menu.Append(
            self._id_selection_font,
            self._menu_label(_("Font for Se&lection..."), "format.selection_font"),
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.choose_editor_font(), id=self._id_editor_font)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.choose_selection_font(), id=self._id_selection_font
        )

    # -- applying ----------------------------------------------------------- #

    def apply_editor_font(self) -> None:
        """Put the chosen face and size on every open tab's editor.

        Every tab, not only the active one: the size is a statement about how
        somebody wants to read, and an editor whose text is large in document 2
        and small in document 5 is one nobody can rely on.

        Never raises. A tab mid-teardown, a control that has gone, a face name
        wx does not have -- none of those is worth failing a settings save for,
        and the document is unharmed either way.
        """
        wx = self._wx
        name = str(getattr(self.settings, "font_name", "") or "")
        points = clamp_font_points(getattr(self.settings, "font_size", DEFAULT_FONT_POINTS))
        for editor, rich in self._editors_with_mode():
            try:
                # Never SetFont on a rich control: wxMSW applies it to the whole
                # control, so it would flatten the heading ladder whatever size
                # is passed. There the zoom is the entire answer (bad.md R5).
                if sets_font(rich=rich):
                    editor.SetFont(
                        wx.Font(
                            int(editor_points_for(points, rich=rich)),
                            wx.FONTFAMILY_DEFAULT,
                            wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL,
                            faceName=name,
                        )
                    )
                self._apply_editor_zoom(editor, *zoom_for(points, rich=rich))
                editor.Refresh()
            except Exception:  # noqa: BLE001 - a font is never worth a crash
                continue

    def _editors_with_mode(self) -> list[tuple[Any, bool]]:
        """``(editor, is_rich)`` for every tab, and the bare editor as a fallback.

        A fallback because the setup wizard runs before the first tab exists,
        and a font applied at startup must not depend on a document being open.
        """
        pairs: list[tuple[Any, bool]] = []
        for tab in getattr(self, "_document_tabs", []) or []:
            editor = getattr(tab, "editor", None)
            if editor is not None:
                pairs.append((editor, str(getattr(tab, "editor_mode", "")) == "rich"))
        if pairs:
            return pairs
        editor = getattr(self, "editor", None)
        return [(editor, False)] if editor is not None else []

    def _apply_editor_zoom(self, editor: Any, numerator: int, denominator: int) -> None:
        """Ask a RichEdit surface to zoom, and ignore a control that cannot.

        ``(0, 0)`` is "no zoom", which is what a plain control wants and what a
        rich one needs when the font itself has changed.
        """
        surface = getattr(editor, "quill_richedit", None)
        setter = getattr(surface, "set_zoom", None)
        if callable(setter):
            setter(numerator, denominator)

    # -- the commands ------------------------------------------------------- #

    def _set_editor_text_size(self, points: int) -> None:
        """Change the size everywhere, save it, and say what it became.

        Said, because nothing else will: the text redraws and a screen reader
        announces nothing about a control that changed size. "14 point" is the
        whole of the feedback and it is the fact somebody pressing the key twice
        in a row needs.
        """
        self.settings.font_size = clamp_font_points(points)
        self.apply_editor_font()
        self._save_settings_quietly()
        self._set_status(f"{self.settings.font_size} point")

    def increase_text_size(self) -> None:
        """Ctrl+= -- Notepad's key, and the one a low-vision user reaches for."""
        self._set_editor_text_size(
            clamp_font_points(getattr(self.settings, "font_size", DEFAULT_FONT_POINTS)) + 1
        )

    def decrease_text_size(self) -> None:
        """Ctrl+-."""
        self._set_editor_text_size(
            clamp_font_points(getattr(self.settings, "font_size", DEFAULT_FONT_POINTS)) - 1
        )

    def reset_text_size(self) -> None:
        """Ctrl+0: back to the default, which is the way out of any experiment."""
        self._set_editor_text_size(DEFAULT_FONT_POINTS)

    def choose_editor_font(self) -> None:
        """Ctrl+Alt+F: the face and size for the whole editor.

        The system font chooser, which is the one surface every Windows screen
        reader already knows how to read. It changes what you see and nothing
        about the file -- the face is never written into a document, which is
        the same promise dark mode makes.
        """
        wx = self._wx
        data = wx.FontData()
        data.SetInitialFont(
            wx.Font(
                clamp_font_points(getattr(self.settings, "font_size", DEFAULT_FONT_POINTS)),
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                faceName=str(getattr(self.settings, "font_name", "") or ""),
            )
        )
        with wx.FontDialog(self.frame, data) as dialog:
            if self._show_modal_dialog(dialog, "Editor Font") != wx.ID_OK:
                self._set_status("Editor font unchanged")
                return
            font = dialog.GetFontData().GetChosenFont()
        self.settings.font_name = font.GetFaceName()
        self.settings.font_size = clamp_font_points(font.GetPointSize())
        self.apply_editor_font()
        self._save_settings_quietly()
        self._set_status(
            f"Editor font {self.settings.font_name or 'system default'}, "
            f"{self.settings.font_size} point"
        )

    def choose_selection_font(self) -> None:
        """Ctrl+Shift+F -- Word's key: the font of *this run*, not the editor's.

        Rich text only, and it says so elsewhere rather than silently doing the
        other thing: in a Markdown document a "font" is a hidden format code,
        which is what ``format.font_dialog`` writes and is a different feature
        with a different name.
        """
        surface = getattr(getattr(self, "editor", None), "quill_richedit", None)
        if surface is None or self._current_editor_mode() != "rich":
            self._set_status(
                "Font for Selection applies to Rich Text documents. "
                "Format, Font sets the font the whole editor draws in."
            )
            return
        start, end = self.editor.GetSelection()
        if end <= start:
            self._set_status("Select some text first")
            return
        wx = self._wx
        data = wx.FontData()
        with wx.FontDialog(self.frame, data) as dialog:
            if self._show_modal_dialog(dialog, "Font for Selection") != wx.ID_OK:
                self._set_status("Font unchanged")
                return
            font = dialog.GetFontData().GetChosenFont()
        label = f"{font.GetFaceName()}, {font.GetPointSize()} point"
        # Through the one seam every other rich formatting command uses, so the
        # dirty flag, the error mapping and the single spoken outcome are the
        # ones the rest of the Format menu already has (#728).
        self._rich_format_command("set_font_name", "", font.GetFaceName())
        self._rich_format_command("set_font_size", label, font.GetPointSize())

    def _save_settings_quietly(self) -> None:
        """Write the settings, swallowing a read-only profile.

        A font change that cannot be stored should still apply for this session:
        refusing to resize the text because a settings file is locked would be
        the worst possible trade for the person this feature is for.
        """
        from quill.core.settings import save_settings

        try:
            save_settings(self.settings)
        except Exception:  # noqa: BLE001 - a settings write is never worth a crash
            pass
