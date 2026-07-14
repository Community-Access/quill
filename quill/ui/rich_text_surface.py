"""The native rich-text editing surface (rtf.md Part One, Stages 3-5).

``RichTextSurface`` is the opt-in "Rich text lens": a dual-pane surface that pairs a
faithful ``wx.RichTextCtrl`` rendering of the document with the canonical
plain-text Markdown editor. The Markdown lens stays the source of truth, so every
existing ``core`` feature (search, metrics, outline, autosave, persistent undo)
keeps working unchanged and switching lenses is lossless within a session.

Why this shape:

* The rich pane shows bold, italic, headings, bullets and links as *formatting*
  rather than markup, and announces the formatting under the caret out loud
  (``docs/QUILL-PRD.md`` "a spoken formatting model"). It is a navigable, read-only view;
  writers edit in the Markdown lens, where QUILL's offset-based commands are exact.
* Fully bidirectional rich editing with cross-session undo is the proposal's
  explicitly hardest problem; it is tracked honestly as in-progress rather than
  faked here. The view/navigate/switch half of the experience ships now.

The wx-touching code is confined to ``_apply_render_plan`` /
``_extract_caret_offset``; the rendering decisions live in the pure, tested
:func:`build_render_plan` so the logic is verifiable on wx-free CI.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.format_speech import describe_inline_format
from quill.io.rtf_model import format_at_markdown_offset, markdown_to_rich

__all__ = ["RichTextSurface", "build_render_plan", "RenderOp"]

# A render op is a (kind, *args) tuple consumed by the wx adapter. Keeping the plan
# as plain tuples makes the rendering logic testable without importing wx.
RenderOp = tuple[object, ...]


def build_render_plan(markdown: str) -> list[RenderOp]:
    """Translate canonical markup into an ordered list of rendering ops.

    Ops:
      ``("heading", level)``   begin a heading paragraph (level 1-6)
      ``("bullet",)``          begin a bullet paragraph
      ``("paragraph",)``       begin a body paragraph
      ``("bold_on"|"bold_off")`` / ``("italic_on"|"italic_off")``
      ``("url_on", href)`` / ``("url_off",)``
      ``("text", value)``      write visible text
      ``("newline",)``         end the current paragraph
    """
    document = markdown_to_rich(markdown)
    plan: list[RenderOp] = []
    for index, paragraph in enumerate(document.paragraphs):
        if index > 0:
            plan.append(("newline",))
        if paragraph.style == "heading":
            plan.append(("heading", min(max(paragraph.level, 1), 6)))
        elif paragraph.style == "bullet":
            plan.append(("bullet",))
        else:
            plan.append(("paragraph",))
        for span in paragraph.spans:
            if span.href:
                plan.append(("url_on", span.href))
            if span.bold:
                plan.append(("bold_on",))
            if span.italic:
                plan.append(("italic_on",))
            plan.append(("text", span.text))
            if span.italic:
                plan.append(("italic_off",))
            if span.bold:
                plan.append(("bold_off",))
            if span.href:
                plan.append(("url_off",))
    return plan


# Heading point sizes, largest (H1) to smallest (H6), for the rich rendering.
_HEADING_SIZES = {1: 22, 2: 18, 3: 16, 4: 14, 5: 13, 6: 12}


class RichTextSurface:
    """A dual-lens surface: a rich rendering plus the canonical Markdown editor."""

    def __init__(
        self,
        wx_module: object,
        parent: object,
        document: object,
        on_change: Callable[[], None],
    ) -> None:
        self._wx = wx_module
        self._document = document
        self._on_change = on_change
        self._suspend_sync = False
        self._last_format_phrase = ""

        wx = self._wx
        self.panel = wx.Panel(parent)
        root = wx.BoxSizer(wx.VERTICAL)

        header = wx.BoxSizer(wx.HORIZONTAL)
        self._mode_button = wx.Button(self.panel, label="Edit as Markdown")
        self._mode_button.SetName("Toggle rich text edit mode")
        self._mode_button.Bind(wx.EVT_BUTTON, self._toggle_mode)
        header.Add(self._mode_button, 0, wx.RIGHT, 8)
        self._mode_label = wx.StaticText(self.panel, label="Rich text lens")
        self._mode_label.SetName("Rich text mode indicator")
        header.Add(self._mode_label, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(header, 0, wx.ALL, 6)

        self._notebook = wx.Notebook(self.panel)
        self._notebook.SetName("Rich text view")
        self._rich_page = wx.Panel(self._notebook)
        self._text_page = wx.Panel(self._notebook)

        rich_ctrl = getattr(wx, "richtext", None)
        if rich_ctrl is not None and hasattr(rich_ctrl, "RichTextCtrl"):
            self.rich = rich_ctrl.RichTextCtrl(
                self._rich_page, style=wx.TE_MULTILINE | wx.TE_READONLY
            )
        else:  # pragma: no cover - fallback when richtext is unavailable
            self.rich = wx.TextCtrl(
                self._rich_page, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
            )
        self.text_ctrl = wx.TextCtrl(
            self._text_page,
            style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_NOHIDESEL,
        )

        rich_sizer = wx.BoxSizer(wx.VERTICAL)
        rich_sizer.Add(self.rich, 1, wx.EXPAND)
        self._rich_page.SetSizer(rich_sizer)
        text_sizer = wx.BoxSizer(wx.VERTICAL)
        text_sizer.Add(self.text_ctrl, 1, wx.EXPAND)
        self._text_page.SetSizer(text_sizer)

        self._notebook.AddPage(self._rich_page, "Rich")
        self._notebook.AddPage(self._text_page, "Markdown")
        self._notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_page_changed)
        root.Add(self._notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self.panel.SetSizer(root)

        self.ChangeValue(getattr(document, "text", "") or "")
        self.show_rich_mode()

    # -- surface identity --------------------------------------------------- #
    def surface_kind(self) -> str:
        return "rich"

    def __getattr__(self, name: str) -> object:
        active = self._active_control()
        if hasattr(active, name):
            return getattr(active, name)
        if hasattr(self.panel, name):
            return getattr(self.panel, name)
        raise AttributeError(name)

    def _active_control(self) -> object:
        return self.text_ctrl if self.is_text_mode() else self.rich

    # -- lens switching ----------------------------------------------------- #
    def is_text_mode(self) -> bool:
        return self._notebook.GetSelection() == 1

    def show_rich_mode(self) -> None:
        self._notebook.ChangeSelection(0)
        self._mode_button.SetLabel("Edit as Markdown")
        self._mode_label.SetLabel("Rich text lens")
        self.rich.SetFocus()
        self._announce_caret_format(force=True)

    def show_text_mode(self) -> None:
        self._notebook.ChangeSelection(1)
        self._mode_button.SetLabel("Show rich text")
        self._mode_label.SetLabel("Markdown lens")
        self.text_ctrl.SetFocus()

    def toggle_mode(self) -> str:
        if self.is_text_mode():
            self.show_rich_mode()
            return "Rich text lens"
        self.show_text_mode()
        return "Markdown lens"

    # -- canonical value API ------------------------------------------------ #
    def GetValue(self) -> str:  # noqa: N802
        return self.text_ctrl.GetValue()

    def ChangeValue(self, value: str) -> None:  # noqa: N802
        self._suspend_sync = True
        try:
            self.text_ctrl.ChangeValue(value)
            self._render_rich(value)
        finally:
            self._suspend_sync = False

    def SetEditable(self, editable: bool) -> None:  # noqa: N802
        self.text_ctrl.SetEditable(editable)

    def SetFocus(self) -> None:  # noqa: N802
        self._active_control().SetFocus()

    # -- canonical offset-editing API --------------------------------------- #
    # QUILL's offset-based editor commands (join/move lines, case transforms,
    # search, spell check) must act on the canonical Markdown lens even while the
    # read-only rich pane is showing. Delegating these explicitly to ``text_ctrl``
    # keeps those commands exact on RTF documents instead of routing through
    # ``__getattr__`` to the rich view, whose offsets differ from the markup
    # (issue: "all surfaces, text and rtf"). The hard bidirectional rich-edit
    # mapping stays deferred, as documented above.
    def GetSelection(self) -> tuple[int, int]:  # noqa: N802
        return self.text_ctrl.GetSelection()

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self.text_ctrl.SetSelection(start, end)

    def GetStringSelection(self) -> str:  # noqa: N802
        return self.text_ctrl.GetStringSelection()

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self.text_ctrl.GetInsertionPoint()

    def SetInsertionPoint(self, pos: int) -> None:  # noqa: N802
        self.text_ctrl.SetInsertionPoint(pos)

    def GetRange(self, start: int, end: int) -> str:  # noqa: N802
        return self.text_ctrl.GetRange(start, end)

    def Replace(self, start: int, end: int, value: str) -> None:  # noqa: N802
        self.text_ctrl.Replace(start, end, value)
        self._render_rich(self.text_ctrl.GetValue())

    def WriteText(self, value: str) -> None:  # noqa: N802
        # Insert/overwrite at the canonical caret (replacing any selection). Used
        # by the atomic-replace path so case/transform edits record a single,
        # cleanly reversible undo step on the Markdown lens (issue #131).
        self.text_ctrl.WriteText(value)
        self._render_rich(self.text_ctrl.GetValue())

    def CanUndo(self) -> bool:  # noqa: N802
        return bool(self.text_ctrl.CanUndo())

    def CanRedo(self) -> bool:  # noqa: N802
        return bool(self.text_ctrl.CanRedo())

    def Undo(self) -> None:  # noqa: N802
        self.text_ctrl.Undo()
        self._render_rich(self.text_ctrl.GetValue())

    def Redo(self) -> None:  # noqa: N802
        self.text_ctrl.Redo()
        self._render_rich(self.text_ctrl.GetValue())

    # -- spoken formatting -------------------------------------------------- #
    def caret_format_description(self) -> str:
        """Return the spoken formatting phrase for the current caret position."""
        markdown = self.text_ctrl.GetValue()
        offset = self._extract_caret_offset()
        fmt = format_at_markdown_offset(markdown, offset)
        return describe_inline_format(
            bold=fmt.bold,
            italic=fmt.italic,
            href=fmt.href,
            heading_level=fmt.heading_level,
            bullet=fmt.bullet,
        )

    def _extract_caret_offset(self) -> int:
        getter = getattr(self.text_ctrl, "GetInsertionPoint", None)
        if callable(getter):
            try:
                return int(getter())
            except (TypeError, ValueError):
                return 0
        return 0

    def _announce_caret_format(self, *, force: bool = False) -> None:
        phrase = self.caret_format_description()
        if not force and phrase == self._last_format_phrase:
            return
        self._last_format_phrase = phrase

    # -- event wiring ------------------------------------------------------- #
    def bind_editor_events(self, frame: object) -> None:
        wx = self._wx
        self.text_ctrl.Bind(wx.EVT_TEXT, lambda _event: self._on_text_changed())
        self.text_ctrl.Bind(wx.EVT_KEY_DOWN, frame._on_editor_key_down)
        self.text_ctrl.Bind(wx.EVT_KEY_UP, frame._on_editor_key_up)
        self.text_ctrl.Bind(wx.EVT_LEFT_UP, frame._on_editor_caret_activity)
        self.text_ctrl.Bind(wx.EVT_SET_FOCUS, frame._on_editor_caret_activity)
        self.text_ctrl.Bind(wx.EVT_CONTEXT_MENU, frame._on_editor_context_menu)
        if hasattr(self.rich, "Bind"):
            self.rich.Bind(wx.EVT_SET_FOCUS, frame._on_editor_caret_activity)
            self.rich.Bind(wx.EVT_CONTEXT_MENU, frame._on_editor_context_menu)

    def _toggle_mode(self, _event: object) -> None:
        self.toggle_mode()

    def _on_page_changed(self, _event: object) -> None:
        if self.is_text_mode():
            self._mode_button.SetLabel("Show rich text")
            self._mode_label.SetLabel("Markdown lens")
        else:
            self._render_rich(self.text_ctrl.GetValue())
            self._mode_button.SetLabel("Edit as Markdown")
            self._mode_label.SetLabel("Rich text lens")

    def _on_text_changed(self) -> None:
        if self._suspend_sync:
            return
        self._on_change()

    # -- rich rendering (wx adapter over the pure render plan) -------------- #
    def _render_rich(self, markdown: str) -> None:
        plan = build_render_plan(markdown)
        self._apply_render_plan(plan)

    def _apply_render_plan(self, plan: list[RenderOp]) -> None:
        ctrl = self.rich
        # The fallback plain TextCtrl cannot honor formatting ops; show plain text.
        if not hasattr(ctrl, "BeginBold"):
            ctrl.ChangeValue("\n".join(self._plan_plain_lines(plan)))
            return
        wx = self._wx
        was_editable = ctrl.IsEditable() if hasattr(ctrl, "IsEditable") else True
        if hasattr(ctrl, "SetEditable"):
            ctrl.SetEditable(True)
        ctrl.Clear()
        for op in plan:
            kind = op[0]
            if kind == "heading":
                size = _HEADING_SIZES.get(int(op[1]), 12)
                ctrl.BeginFontSize(size)
                ctrl.BeginBold()
            elif kind == "bullet":
                if hasattr(ctrl, "BeginSymbolBullet"):
                    ctrl.BeginSymbolBullet("\u2022", 40, 40)
                else:  # pragma: no cover
                    ctrl.WriteText("\u2022 ")
            elif kind == "paragraph":
                pass
            elif kind == "bold_on":
                ctrl.BeginBold()
            elif kind == "bold_off":
                ctrl.EndBold()
            elif kind == "italic_on":
                ctrl.BeginItalic()
            elif kind == "italic_off":
                ctrl.EndItalic()
            elif kind == "url_on":
                ctrl.BeginURL(str(op[1]))
                if hasattr(ctrl, "BeginTextColour"):
                    ctrl.BeginTextColour(wx.Colour(0, 0, 238))
            elif kind == "url_off":
                if hasattr(ctrl, "EndTextColour"):
                    ctrl.EndTextColour()
                ctrl.EndURL()
            elif kind == "text":
                ctrl.WriteText(str(op[1]))
            elif kind == "newline":
                ctrl.EndAllStyles()
                ctrl.Newline()
        ctrl.EndAllStyles()
        if hasattr(ctrl, "SetEditable"):
            ctrl.SetEditable(was_editable)

    @staticmethod
    def _plan_plain_lines(plan: list[RenderOp]) -> list[str]:
        lines: list[str] = [""]
        for op in plan:
            if op[0] == "text":
                lines[-1] += str(op[1])
            elif op[0] == "bullet":
                lines[-1] += "\u2022 "
            elif op[0] == "newline":
                lines.append("")
        return lines
