"""Hidden-codes run/paragraph formatting commands for ``MainFrame``.

Implements the editor commands for the rich-text "hidden codes" feature
(``the QUILL PRD hidden-codes appendix``): font family, point size,
text color, highlight, and paragraph alignment, plus the "describe formatting at
cursor" interrogation hotkey. Each command materializes an *invisible* Pandoc
attribute span (``[text]{...}``) or alignment fenced div (``::: {align=...}``)
into the canonical Markdown buffer; the codes are realized only at export
(Word/RTF/HTML) and are spoken on demand for screen-reader users.

Extracted from ``main_frame.py`` to keep that module within the size budget
(GATE-11). ``FormatCodesMixin`` is mixed into ``MainFrame``; every method resolves
through the MRO and relies on helpers that stay on ``MainFrame``
(``_feature_enabled``, ``_active_markup_surface``, ``_apply_insertion_result``,
``_set_status``) and on the live ``editor`` surface.
"""

from __future__ import annotations

from typing import Any

from quill.core.format_speech import describe_format_transition, describe_inline_format
from quill.core.i18n import _
from quill.core.tagging import (
    build_block_alignment,
    build_block_attributes,
    build_clear_formatting,
    build_page_break,
    build_span_insertion,
)
from quill.io.rtf_model import format_at_markdown_offset
from quill.platform.sr_announce import announce

# Menu presets. Leaf items use plain Append (no keymap command), so they stay
# clear of the menu_lint binding/label gate while remaining keyboard-navigable.
_FONT_PRESETS = ("Arial", "Calibri", "Times New Roman", "Courier New", "Verdana", "Georgia")
_SIZE_PRESETS = (8, 9, 10, 11, 12, 14, 16, 18, 24, 36, 48, 72)
_COLOR_PRESETS = (
    ("Black", "#000000"),
    ("Red", "#C00000"),
    ("Green", "#008000"),
    ("Blue", "#0000FF"),
    ("Orange", "#FF8C00"),
    ("Purple", "#800080"),
)
_HIGHLIGHT_PRESETS = (
    ("Yellow", "yellow"),
    ("Green", "green"),
    ("Turquoise", "turquoise"),
    ("Pink", "pink"),
    ("Gray", "gray"),
)
_LINE_SPACING_PRESETS = (("Single", "1"), ("1.5 lines", "1.5"), ("Double", "2"))
_NAMED_STYLE_PRESETS = (
    ("Quote", "quote"),
    ("Title", "title"),
    ("Subtitle", "subtitle"),
    ("Caption", "caption"),
)
# (label, kind, points) for the flattened Paragraph Spacing submenu.
_SPACING_PRESETS = (
    ("Space before: 6 points", "before", 6),
    ("Space before: 12 points", "before", 12),
    ("Space after: 6 points", "after", 6),
    ("Space after: 12 points", "after", 12),
)
# (label, kind, points) for the flattened Indent submenu.
_INDENT_PRESETS = (
    ("Left indent: 18 points", "indent", 18),
    ("Left indent: 36 points", "indent", 36),
    ("Left indent: 54 points", "indent", 54),
    ("First-line indent: 18 points", "first", 18),
    ("First-line indent: 36 points", "first", 36),
)


class FormatCodesMixin:
    # -- Command registration ----------------------------------------------- #
    def register_format_codes_commands(self) -> None:
        """Register the hidden-codes commands so they are remappable/searchable.

        Only Describe Formatting carries a default binding (the QUILL Key chord in
        the keymap); the rest are bindingless until a user assigns one. Called from
        ``MainFrame``'s command-registration sequence (one line, GATE-11).
        """
        specs: tuple[tuple[str, str, object], ...] = (
            (
                "format.describe_formatting",
                "Describe Formatting at Cursor",
                self.describe_formatting_at_cursor,
            ),
            ("format.clear_formatting", "Clear Formatting", self.format_clear_formatting),
            ("format.insert_page_break", "Insert Page Break", self.insert_page_break),
            ("format.font_dialog", "Font...", self.open_font_dialog),
            (
                "format.toggle_announce_formatting",
                "Announce Formatting on Cursor Move",
                self.toggle_announce_formatting_on_move,
            ),
        )
        for command_id, label, handler in specs:
            self.commands.register(command_id, label, handler, self._binding_for(command_id))

    # -- Format menu wiring ------------------------------------------------- #
    def build_format_codes_submenus(self, format_menu: Any, wx: Any) -> None:
        """Append Font / Size / Align / Color / Highlight submenus + interrogation.

        Called from the Format-menu builder (``main_frame_menu.py``) so the bulk of
        the wiring stays out of that monolith (GATE-11). Id maps are stored on
        ``self`` for :meth:`bind_format_codes` to bind.
        """
        self._font_menu_ids: dict[int, str] = {}
        font_menu = wx.Menu()
        for family in _FONT_PRESETS:
            font_id = wx.NewIdRef()
            self._font_menu_ids[int(font_id)] = family
            font_menu.Append(font_id, family)
        format_menu.AppendSubMenu(font_menu, _("&Font"))

        self._size_menu_ids: dict[int, int] = {}
        size_menu = wx.Menu()
        for points in _SIZE_PRESETS:
            size_id = wx.NewIdRef()
            self._size_menu_ids[int(size_id)] = points
            size_menu.Append(size_id, _("{n} point").format(n=points))
        format_menu.AppendSubMenu(size_menu, _("Font &Size"))

        self._id_align_left = wx.NewIdRef()
        self._id_align_center = wx.NewIdRef()
        self._id_align_right = wx.NewIdRef()
        self._id_align_justify = wx.NewIdRef()
        align_menu = wx.Menu()
        align_menu.Append(self._id_align_left, _("&Left"))
        align_menu.Append(self._id_align_center, _("&Center"))
        align_menu.Append(self._id_align_right, _("&Right"))
        align_menu.Append(self._id_align_justify, _("&Justify"))
        format_menu.AppendSubMenu(align_menu, _("&Align"))

        self._color_menu_ids: dict[int, tuple[str, str]] = {}
        color_menu = wx.Menu()
        for color_name, color_value in _COLOR_PRESETS:
            color_id = wx.NewIdRef()
            self._color_menu_ids[int(color_id)] = (color_value, color_name)
            color_menu.Append(color_id, color_name)
        format_menu.AppendSubMenu(color_menu, _("Text &Color"))

        self._highlight_menu_ids: dict[int, tuple[str, str]] = {}
        highlight_menu = wx.Menu()
        for hl_name, hl_value in _HIGHLIGHT_PRESETS:
            hl_id = wx.NewIdRef()
            self._highlight_menu_ids[int(hl_id)] = (hl_value, hl_name)
            highlight_menu.Append(hl_id, hl_name)
        format_menu.AppendSubMenu(highlight_menu, _("&Highlight"))

        self._id_font_dialog = wx.NewIdRef()
        format_menu.Append(self._id_font_dialog, _("&More Font Options..."))

        # Inline weight/decoration toggles + clear.
        self._id_strikethrough = wx.NewIdRef()
        self._id_superscript = wx.NewIdRef()
        self._id_subscript = wx.NewIdRef()
        self._id_clear_formatting = wx.NewIdRef()
        format_menu.Append(self._id_strikethrough, _("Stri&kethrough"))
        format_menu.Append(self._id_superscript, _("Su&perscript"))
        format_menu.Append(self._id_subscript, _("Su&bscript"))
        format_menu.Append(self._id_clear_formatting, _("Clear &Formatting"))

        # Paragraph (block) formatting.
        self._line_spacing_ids: dict[int, str] = {}
        line_menu = wx.Menu()
        for ls_label, ls_value in _LINE_SPACING_PRESETS:
            ls_id = wx.NewIdRef()
            self._line_spacing_ids[int(ls_id)] = ls_value
            line_menu.Append(ls_id, ls_label)
        format_menu.AppendSubMenu(line_menu, _("Line &Spacing"))

        self._spacing_ids: dict[int, tuple[str, int]] = {}
        spacing_menu = wx.Menu()
        for sp_label, sp_kind, sp_pts in _SPACING_PRESETS:
            sp_id = wx.NewIdRef()
            self._spacing_ids[int(sp_id)] = (sp_kind, sp_pts)
            spacing_menu.Append(sp_id, sp_label)
        format_menu.AppendSubMenu(spacing_menu, _("Paragraph Spa&cing"))

        self._indent_ids: dict[int, tuple[str, int]] = {}
        indent_menu = wx.Menu()
        for in_label, in_kind, in_pts in _INDENT_PRESETS:
            in_id = wx.NewIdRef()
            self._indent_ids[int(in_id)] = (in_kind, in_pts)
            indent_menu.Append(in_id, in_label)
        format_menu.AppendSubMenu(indent_menu, _("Paragraph &Indent"))

        self._named_style_ids: dict[int, str] = {}
        style_menu = wx.Menu()
        for st_label, st_value in _NAMED_STYLE_PRESETS:
            st_id = wx.NewIdRef()
            self._named_style_ids[int(st_id)] = st_value
            style_menu.Append(st_id, st_label)
        format_menu.AppendSubMenu(style_menu, _("Paragraph St&yle"))

        self._id_page_break = wx.NewIdRef()
        format_menu.Append(self._id_page_break, _("Insert Page Brea&k"))

        self._id_describe_formatting = wx.NewIdRef()
        format_menu.Append(
            self._id_describe_formatting,
            self._menu_label(_("&Describe Formatting at Cursor"), "format.describe_formatting"),
        )
        self._id_announce_move = wx.NewIdRef()
        format_menu.AppendCheckItem(
            self._id_announce_move, _("Announce Formatting on Cursor &Move")
        )
        format_menu.Check(
            self._id_announce_move,
            bool(getattr(self.settings, "announce_formatting_on_move", False)),
        )

    def bind_format_codes(self, wx: Any) -> None:
        """Bind every Format-menu hidden-codes item to its command."""
        for font_id, family in self._font_menu_ids.items():
            self.frame.Bind(
                wx.EVT_MENU, lambda _e, fam=family: self.format_set_font(fam), id=font_id
            )
        for size_id, points in self._size_menu_ids.items():
            self.frame.Bind(wx.EVT_MENU, lambda _e, pt=points: self.format_set_size(pt), id=size_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_align("left"), id=self._id_align_left)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.format_align("center"), id=self._id_align_center
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_align("right"), id=self._id_align_right)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.format_align("justify"), id=self._id_align_justify
        )
        for color_id, (color_value, color_name) in self._color_menu_ids.items():
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e, val=color_value, name=color_name: self.format_set_color(val, name),
                id=color_id,
            )
        for hl_id, (hl_value, hl_name) in self._highlight_menu_ids.items():
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e, val=hl_value, name=hl_name: self.format_set_highlight(val, name),
                id=hl_id,
            )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_font_dialog(), id=self._id_font_dialog)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.format_strikethrough(), id=self._id_strikethrough
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_superscript(), id=self._id_superscript)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.format_subscript(), id=self._id_subscript)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.format_clear_formatting(), id=self._id_clear_formatting
        )
        for ls_id, ls_value in self._line_spacing_ids.items():
            self.frame.Bind(
                wx.EVT_MENU, lambda _e, val=ls_value: self.format_set_line_spacing(val), id=ls_id
            )
        for sp_id, (sp_kind, sp_pts) in self._spacing_ids.items():
            handler = (
                self.format_set_space_before if sp_kind == "before" else self.format_set_space_after
            )
            self.frame.Bind(wx.EVT_MENU, lambda _e, fn=handler, pt=sp_pts: fn(pt), id=sp_id)
        for in_id, (in_kind, in_pts) in self._indent_ids.items():
            handler = (
                self.format_set_indent if in_kind == "indent" else self.format_set_first_line_indent
            )
            self.frame.Bind(wx.EVT_MENU, lambda _e, fn=handler, pt=in_pts: fn(pt), id=in_id)
        for st_id, st_value in self._named_style_ids.items():
            self.frame.Bind(
                wx.EVT_MENU, lambda _e, val=st_value: self.format_set_named_style(val), id=st_id
            )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.insert_page_break(), id=self._id_page_break)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.describe_formatting_at_cursor(),
            id=self._id_describe_formatting,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.toggle_announce_formatting_on_move(),
            id=self._id_announce_move,
        )

    # These materialize a Pandoc attribute span ``[text]{...}`` that stays
    # invisible in the editor and is realized only at export. They apply to the
    # Markdown surface; the span grammar has no HTML-surface equivalent here.
    def _apply_run_attribute(self, attrs: dict[str, str], status: str, *, label: str) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status(f"{label} is unavailable in this profile")
            return
        # Rich mode: the same commands apply *real* formatting via the TOM
        # instead of inserting hidden-code spans (mode-polymorphic contract).
        if self._current_editor_mode() == "rich":
            if not self._rich_apply_run_attrs(attrs, status, label):
                self._set_status(f"{label} is not available in Rich Text yet")
            return
        if self._active_markup_surface() != "markdown":
            self._set_status(f"{label} is only available in Markdown documents")
            return
        selected_text = self.editor.GetStringSelection()
        result = build_span_insertion(selected_text, attrs)
        self._apply_insertion_result(result)
        self._set_status(status)
        announce(status)

    def format_set_font(self, family: str) -> None:
        self._apply_run_attribute({"font-family": family}, f"{family} font applied", label="Font")

    def format_set_size(self, points: int) -> None:
        self._apply_run_attribute(
            {"font-size": str(points)}, f"{points} point applied", label="Font size"
        )

    def format_set_color(self, color: str, name: str = "") -> None:
        self._apply_run_attribute(
            {"color": color}, f"{name or color} text color applied", label="Color"
        )

    def format_set_highlight(self, color: str, name: str = "") -> None:
        self._apply_run_attribute(
            {"highlight": color}, f"{name or color} highlight applied", label="Highlight"
        )

    def format_strikethrough(self) -> None:
        self._apply_run_attribute({"strike": "1"}, "Strikethrough applied", label="Strikethrough")

    def format_superscript(self) -> None:
        self._apply_run_attribute({"superscript": "1"}, "Superscript applied", label="Superscript")

    def format_subscript(self) -> None:
        self._apply_run_attribute({"subscript": "1"}, "Subscript applied", label="Subscript")

    def format_clear_formatting(self) -> None:
        """Strip run formatting from the selection (or current paragraph)."""
        if not self._feature_enabled("core.format"):
            self._set_status("Clear formatting is unavailable in this profile")
            return
        if self._active_markup_surface() != "markdown":
            self._set_status("Clear formatting is only available in Markdown documents")
            return
        self._select_paragraph_if_empty()
        result = build_clear_formatting(self.editor.GetStringSelection())
        self._apply_insertion_result(result)
        status = "Formatting cleared"
        self._set_status(status)
        announce(status)

    def open_font_dialog(self) -> None:
        """The accessible "Font..." surface for arbitrary font/size/color values."""
        if not self._feature_enabled("core.format"):
            self._set_status("Font tools are unavailable in this profile")
            return
        if self._active_markup_surface() != "markdown":
            self._set_status("Font is only available in Markdown documents")
            return
        from quill.ui.dialog_contract import apply_modal_ids
        from quill.ui.font_format_dialog import FontFormatDialog

        wx = self._wx
        panel = FontFormatDialog(wx)
        dialog = wx.Dialog(self.frame, title="Font", style=wx.DEFAULT_DIALOG_STYLE)
        outer = panel.populate(dialog)
        buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        panel.finalize()
        apply_modal_ids(
            dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="&Apply",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        try:
            if self._show_modal_dialog(dialog, "Font") != wx.ID_OK:
                self._set_status("Font unchanged")
                return
            attrs = panel.result
        finally:
            dialog.Destroy()
        if not attrs:
            self._set_status("No font changes selected")
            return
        result = build_span_insertion(self.editor.GetStringSelection(), attrs)
        self._apply_insertion_result(result)
        status = "Font applied"
        self._set_status(status)
        announce(status)

    # -- Block (paragraph) formatting --------------------------------------- #
    def _select_paragraph_if_empty(self) -> None:
        """Expand an empty selection to cover the current source line."""
        start, end = self.editor.GetSelection()
        if start != end:
            return
        text = self.editor.GetValue()
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", start)
        if line_end == -1:
            line_end = len(text)
        self.editor.SetSelection(line_start, line_end)

    def _apply_block_attribute(self, attrs: dict[str, str], status: str, *, label: str) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status(f"{label} is unavailable in this profile")
            return
        if self._current_editor_mode() == "rich":
            # No TOM mapping for these paragraph attributes yet; an honest
            # message beats hidden codes silently landing in rich plain text.
            self._set_status(f"{label} is not available in Rich Text yet")
            return
        if self._active_markup_surface() != "markdown":
            self._set_status(f"{label} is only available in Markdown documents")
            return
        self._select_paragraph_if_empty()
        result = build_block_attributes(self.editor.GetStringSelection(), attrs)
        self._apply_insertion_result(result)
        self._set_status(status)
        announce(status)

    def format_align(self, which: str) -> None:
        """Wrap the selection (or current paragraph) in an alignment fenced div."""
        if not self._feature_enabled("core.format"):
            self._set_status("Alignment is unavailable in this profile")
            return
        if self._rich_format_command("set_alignment", f"{which.capitalize()} alignment", which):
            return
        if self._active_markup_surface() != "markdown":
            self._set_status("Alignment is only available in Markdown documents")
            return
        self._select_paragraph_if_empty()
        result = build_block_alignment(self.editor.GetStringSelection(), which)
        self._apply_insertion_result(result)
        status = f"{which.capitalize()} alignment applied"
        self._set_status(status)
        announce(status)

    def format_set_line_spacing(self, value: str) -> None:
        self._apply_block_attribute(
            {"line-spacing": value}, f"{value} line spacing applied", label="Line spacing"
        )

    def format_set_space_before(self, points: int) -> None:
        self._apply_block_attribute(
            {"space-before": str(points)}, f"{points} point space before applied", label="Spacing"
        )

    def format_set_space_after(self, points: int) -> None:
        self._apply_block_attribute(
            {"space-after": str(points)}, f"{points} point space after applied", label="Spacing"
        )

    def format_set_indent(self, points: int) -> None:
        self._apply_block_attribute(
            {"indent": str(points)}, f"{points} point indent applied", label="Indent"
        )

    def format_set_first_line_indent(self, points: int) -> None:
        self._apply_block_attribute(
            {"first-line-indent": str(points)},
            f"{points} point first-line indent applied",
            label="Indent",
        )

    def format_set_named_style(self, style: str) -> None:
        self._apply_block_attribute(
            {"pstyle": style}, f"{style.capitalize()} style applied", label="Paragraph style"
        )

    def insert_page_break(self) -> None:
        """Insert a page break (materialized only at export) on its own line."""
        if not self._feature_enabled("core.format"):
            self._set_status("Page break is unavailable in this profile")
            return
        if self._active_markup_surface() != "markdown":
            self._set_status("Page break is only available in Markdown documents")
            return
        marker = build_page_break().inserted_text
        start, end = self.editor.GetSelection()
        self.editor.Replace(start, end, f"\n{marker}\n")
        self.editor.SetInsertionPoint(start + len(marker) + 2)
        self.editor.SetFocus()
        status = "Page break inserted"
        self._set_status(status)
        announce(status)

    def describe_formatting_at_cursor(self) -> None:
        """Speak the formatting in effect at the caret (the interrogation hotkey).

        The primary "interrogate the document" affordance: explicit and quiet, so
        navigation does not chatter. Reads the run/paragraph context at the caret in
        the canonical markup and announces the spoken phrase.
        """
        # Rich mode answers from the live control (ITextFont/ITextPara), not
        # from parsing markup: "Arial, 14 point, bold, centered".
        rich_phrase = self.describe_caret_formatting_rich()
        if rich_phrase is not None:
            self._set_status(f"Formatting: {rich_phrase}")
            announce(rich_phrase)
            return
        if self._active_markup_surface() != "markdown":
            self._set_status("Formatting description is available in Markdown documents")
            return
        markdown = self.editor.GetValue()
        offset = self.editor.GetInsertionPoint()
        fmt = format_at_markdown_offset(markdown, offset)
        phrase = describe_inline_format(
            bold=fmt.bold,
            italic=fmt.italic,
            href=fmt.href,
            heading_level=fmt.heading_level,
            bullet=fmt.bullet,
            underline=fmt.underline,
            strike=fmt.strike,
            superscript=fmt.superscript,
            subscript=fmt.subscript,
            font_family=fmt.font_family,
            font_size_pt=fmt.font_size_pt,
            color=fmt.color,
            highlight=fmt.highlight,
            align=fmt.align,
            named_style=fmt.named_style,
            line_spacing=fmt.line_spacing,
            space_before=fmt.space_before,
            space_after=fmt.space_after,
            indent=fmt.indent,
            first_line_indent=fmt.first_line_indent,
        )
        message = phrase or "plain text, no formatting"
        self._set_status(f"Formatting: {message}")
        announce(message)

    # -- Optional on-caret-move formatting announcements -------------------- #
    def _caret_format_phrase(self) -> str:
        markdown = self.editor.GetValue()
        offset = self.editor.GetInsertionPoint()
        fmt = format_at_markdown_offset(markdown, offset)
        return describe_inline_format(
            bold=fmt.bold,
            italic=fmt.italic,
            href=fmt.href,
            heading_level=fmt.heading_level,
            bullet=fmt.bullet,
            underline=fmt.underline,
            strike=fmt.strike,
            superscript=fmt.superscript,
            subscript=fmt.subscript,
            font_family=fmt.font_family,
            font_size_pt=fmt.font_size_pt,
            color=fmt.color,
            highlight=fmt.highlight,
            align=fmt.align,
            named_style=fmt.named_style,
            line_spacing=fmt.line_spacing,
            space_before=fmt.space_before,
            space_after=fmt.space_after,
            indent=fmt.indent,
            first_line_indent=fmt.first_line_indent,
        )

    def _maybe_announce_format_transition(self) -> None:
        """Announce only the *delta* in formatting as the caret moves, when enabled.

        Off by default (``settings.announce_formatting_on_move``); when on, speaks
        just the change (``"bold"`` entering bold, ``"plain"`` leaving it) so
        navigation stays terse. Called from the editor caret-activity handler.
        """
        if not getattr(self.settings, "announce_formatting_on_move", False):
            return
        if self._active_markup_surface() != "markdown":
            return
        current = self._caret_format_phrase()
        delta = describe_format_transition(getattr(self, "_last_format_move_phrase", ""), current)
        self._last_format_move_phrase = current
        if delta:
            announce(delta)

    def toggle_announce_formatting_on_move(self) -> None:
        """Toggle continuous on-caret-move formatting announcements."""
        new_value = not getattr(self.settings, "announce_formatting_on_move", False)
        self.settings.announce_formatting_on_move = new_value
        try:
            from quill.core.settings import save_settings

            save_settings(self.settings)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            pass
        self._last_format_move_phrase = ""
        status = (
            "Formatting announcements on cursor move: on"
            if new_value
            else "Formatting announcements on cursor move: off"
        )
        self._set_status(status)
        announce(status)
