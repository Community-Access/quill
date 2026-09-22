"""Paragraph and run formatting QUILL's rich mode was missing.

Six commands, and all six arrived the same way: QuillLite needed them to be a
credible WordPad replacement, and a feature the small product has and the
editor does not is exactly backwards. So the capability lives in the shared
surface (:mod:`quill.ui.richedit_editing`) and both products reach it -- this
module is QUILL's half.

* **Justify** (Ctrl+Alt+J), completing the four alignments. ``ITextPara.Alignment``
  has always supported it; nothing was bound to it.
* **Bullets** in *rich* mode. QUILL's existing Ctrl+Alt+B toggles a Markdown
  ``-`` list, which is the right answer in a Markdown document and no answer at
  all in a Rich Text one. In rich mode the same key now drives
  ``ITextPara.ListType``, so one key means one idea in both.
* **Line spacing** -- single, one-and-a-half, double (Ctrl+1, Ctrl+5, Ctrl+2).
  WordPad's chords, because those are the ones in people's hands.
* **Grow and shrink font** (Ctrl+Shift+> and Ctrl+Shift+<), stepping a ladder of
  real point sizes rather than drifting one point at a time. The ladder includes
  the heading sizes, so growing a heading stays *on* the heading ladder instead
  of falling off it into a paragraph that merely looks large.
* **Paste Text Only** (Ctrl+Alt+V), which is not a QUILL feature, not a
  WordPad feature, and the thing everybody reaches for anyway when a web page
  arrives in a document wearing its own fonts.

QUILL takes Ctrl+Alt+J and Ctrl+Alt+V where QuillLite uses WordPad's Ctrl+J and
Ctrl+Shift+V: Ctrl+J has been Set Temporary Bookmark and Ctrl+Shift+V has been
Preview here for far longer, and an existing binding somebody's hands already
know outranks a new command's convention.

Everything here routes through ``_rich_format_command`` where it can, so the
mode check, the dirty flag, the error mapping and the single spoken outcome are
the ones every other rich command already uses -- including the #728 rule that
``_set_status`` already speaks, so the same words must never be handed to
``_announce`` as well. Where a message differs between the two, this uses
``_set_status_quiet`` plus ``_announce``; where it does not, ``_set_status``
alone, which already speaks.

Paste Text Only is the one exception to the routing: it is an edit rather than a
formatting change, so it goes in through the control's own replace and marks the
document dirty by doing so.
"""

from __future__ import annotations

from typing import Any

from quill.ui.atomic_edit import replace_as_one_undo

__all__ = ["RichParagraphMixin"]

#: ``ITextPara.SetLineSpacing`` rules, named. Imported lazily with the rest of
#: the surface so this module stays importable with no wx and no Windows.
_SPACING_LABELS: dict[str, str] = {
    "single": "Single spacing",
    "one_and_a_half": "One and a half spacing",
    "double": "Double spacing",
}


class RichParagraphMixin:
    """Alignment, lists, line spacing, font stepping, and plain paste."""

    # -- alignment ---------------------------------------------------------- #

    def format_justify(self) -> None:
        """Justify the paragraph. Word's Ctrl+J since 2026-09-16.

        Delegates to :meth:`format_align` rather than repeating it. The two
        were separate implementations of one verb until now -- ``format.justify``
        went through here and the Format > Align submenu's Justify row went
        through ``format_align("justify")``, which also knows how to write a
        Markdown alignment div. One of them was better and it was not this one
        (bad.md 7.1: one verb, one registration).
        """
        self.format_align("justify")

    def _organize_rich_headings(self, wrapper: object, organize: object) -> None:
        """The rich half of :meth:`open_heading_organizer`.

        Separate because the two halves share only the dialog: one hands a
        string in and puts a string back through the undo-aware apply, the
        other hands the control in and lets formatted ranges move inside it.
        """
        from quill.ui.richedit_rtf_surface import RichEditRtfError

        try:
            changed = organize(  # type: ignore[operator]
                self.frame,
                wrapper=wrapper,
                text=self.editor.GetValue(),
                show_modal=self._show_modal_dialog,
                say=self._set_status,
                warn_duplicate_h1=bool(
                    getattr(self.settings, "heading_organizer_warn_duplicate_h1", False)
                ),
            )
        except RichEditRtfError as error:
            self._set_status(f"Heading Organizer failed: {error}")
            return
        if not changed:
            return
        self._mark_rich_formatting_dirty()
        self._announce_result("Applied heading organizer changes")

    # -- lists -------------------------------------------------------------- #

    _LIST_STYLE_WORDS = {
        "none": "No list",
        "bullet": "Bulleted list",
        "numbered": "Numbered list",
    }

    def format_rich_list_style(self) -> bool:
        """Step the caret's paragraphs to the next list style. True when handled.

        WordPad's Ctrl+Shift+L and QuillLite's: bulleted, numbered, none, round
        again. A toggle can only say yes or no, which is why a numbered list was
        unreachable from the keyboard in a rich QUILL document (bad.md P1.5).

        ``ITextPara.ListType`` is the whole implementation -- in a rich document
        a list is a paragraph property the control draws and renumbers, not
        characters in the text.
        """
        from quill.core.list_style import LIST_STYLES

        wrapper = self._active_richedit()
        if self._current_editor_mode() != "rich" or wrapper is None:
            return False
        at_caret = getattr(wrapper, "list_style_at_caret", lambda: "none")()
        if at_caret not in LIST_STYLES:
            at_caret = "none"
        style = LIST_STYLES[(LIST_STYLES.index(at_caret) + 1) % len(LIST_STYLES)]
        return bool(
            self._rich_format_command("set_list_style", self._LIST_STYLE_WORDS[style], style)
        )

    def format_rich_bullets(self) -> bool:
        """Toggle a real bullet list in rich mode. ``True`` when handled.

        Returns rather than announces so the existing Markdown bullet command
        can call it first and fall through untouched in every other mode -- one
        key, one idea, two implementations that never both run.

        **And it is called, since 2026-09-16.** It was written to be called from
        ``toggle_bullet_list`` and nothing ever called it, so a bulleted list was
        unreachable in a rich document and Ctrl+Shift+L said "Bullet List is only
        available in Markdown or HTML documents" about the one kind of document
        that has real lists (bad.md R1). The module docstring above promised the
        opposite for a year.
        """
        wrapper = self._active_richedit()
        if self._current_editor_mode() != "rich" or wrapper is None:
            return False
        toggle_to = not bool(getattr(wrapper, "bullets_at_caret", lambda: False)())
        return bool(
            self._rich_format_command(
                "set_bullets", "Bullets on" if toggle_to else "Bullets off", toggle_to
            )
        )

    # -- line spacing ------------------------------------------------------- #

    def format_line_spacing(self, rule: str) -> None:
        """Set single, one-and-a-half or double spacing on the selection."""
        if not self._feature_enabled("core.format"):
            self._set_status("Line spacing is unavailable in this profile")
            return
        from quill.ui.richedit_editing import (
            LINE_SPACING_DOUBLE,
            LINE_SPACING_ONE_AND_A_HALF,
            LINE_SPACING_SINGLE,
        )

        values = {
            "single": LINE_SPACING_SINGLE,
            "one_and_a_half": LINE_SPACING_ONE_AND_A_HALF,
            "double": LINE_SPACING_DOUBLE,
        }
        label = _SPACING_LABELS.get(rule, "Line spacing")
        if self._rich_format_command("set_line_spacing", label, values.get(rule, 0)):
            return
        self._set_status("Line spacing applies to Rich Text documents")

    # -- font size ---------------------------------------------------------- #

    def format_step_font(self, *, larger: bool) -> None:
        """Move the selection one step along the point-size ladder.

        Not the same thing as the view's text size, and the difference matters:
        this changes the *document*, so it is an edit and it is saved.
        """
        if not self._feature_enabled("core.format"):
            self._set_status("Font size is unavailable in this profile")
            return
        wrapper: Any = self._active_richedit()
        if self._current_editor_mode() != "rich" or wrapper is None:
            self._set_status("Changing the font size applies to Rich Text documents")
            return
        from quill.ui.richedit_rtf_surface import RichEditRtfError

        try:
            size = wrapper.step_font_size(larger=larger)
        except (AttributeError, RichEditRtfError) as error:
            self._set_status(f"Could not change the font size: {error}")
            return
        self._mark_rich_formatting_dirty()
        self._set_status_quiet(f"{size:g} point")
        self._announce(f"{size:g} point")

    def format_grow_font(self) -> None:
        self.format_step_font(larger=True)

    def format_shrink_font(self) -> None:
        self.format_step_font(larger=False)

    # -- paste ---------------------------------------------------------------- #

    def edit_paste_plain_text(self) -> None:
        """Paste the clipboard's text with none of its formatting.

        Reads the clipboard defensively: it is a shared, single-owner OS
        resource, and a read that fails must degrade to "nothing to paste"
        rather than to an error.
        """
        import wx

        data = wx.TextDataObject()
        got = False
        try:
            if wx.TheClipboard.Open():
                try:
                    got = wx.TheClipboard.GetData(data)
                finally:
                    wx.TheClipboard.Close()
        except Exception:  # noqa: BLE001 - a clipboard read must never raise
            got = False
        text = str(data.GetText()) if got else ""
        if not text:
            self._set_status("The clipboard has no text")
            return
        editor = self.editor
        start, end = editor.GetSelection()
        if end > start:
            # Not Replace: one Ctrl+Z has to take the paste back whole, and
            # over a selection Replace leaves undo on an intermediate state
            # (bad.md C6).
            replace_as_one_undo(editor, start, end, text)
        else:
            editor.WriteText(text)
        self._set_status_quiet(f"Pasted {len(text):,} characters as plain text")
        self._announce(f"Pasted {len(text):,} characters as plain text")
