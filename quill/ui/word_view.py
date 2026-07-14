from __future__ import annotations

import re
from collections.abc import Callable
from html.parser import HTMLParser

from quill.core.document import Document
from quill.io.pandoc import (
    PandocConversionError,
    PandocUnavailableError,
    convert_document_with_pandoc,
)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _split_markdown_row(row: str) -> list[str]:
    content = row.strip()
    if not content.startswith("|") or not content.endswith("|"):
        return []
    cells = [cell.strip() for cell in content.strip("|").split("|")]
    return [cell for cell in cells]


def _looks_like_markdown_separator(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(bool(re.fullmatch(r":?-{3,}:?", cell.replace(" ", ""))) for cell in cells)


def _linearize_markdown_tables(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    table_index = 0
    index = 0
    while index < len(lines):
        header_cells = _split_markdown_row(lines[index])
        sep_cells = _split_markdown_row(lines[index + 1]) if index + 1 < len(lines) else []
        if header_cells and _looks_like_markdown_separator(sep_cells):
            table_index += 1
            output.append(f"Table {table_index}")
            output.append("Headers: " + " | ".join(header_cells))
            row_index = 0
            index += 2
            while index < len(lines):
                row_cells = _split_markdown_row(lines[index])
                if not row_cells:
                    break
                row_index += 1
                if len(row_cells) == len(header_cells):
                    pairs = [
                        f"{header}: {value}"
                        for header, value in zip(header_cells, row_cells, strict=True)
                    ]
                    output.append(f"Row {row_index}: " + "; ".join(pairs))
                else:
                    output.append(f"Row {row_index}: " + " | ".join(row_cells))
                index += 1
            output.append("")
            continue
        output.append(lines[index])
        index += 1
    result = "\n".join(output).strip()
    return result + "\n" if result else ""


class _AccessibleWordHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self._text_buffer: list[str] = []
        self._prefix = ""
        self._skip_depth = 0
        self._table_index = 0
        self._table_headers: list[str] = []
        self._row_index = 0
        self._row_cells: list[str] = []
        self._row_flags: list[bool] = []
        self._cell_buffer: list[str] = []
        self._cell_is_header = False
        self._in_table = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "head"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if lowered == "br":
            self._flush_line()
            return
        if lowered in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush_line()
            level = int(lowered[1])
            self._prefix = "#" * level + " "
            return
        if lowered in {"p", "li"}:
            self._flush_line()
            self._prefix = "- " if lowered == "li" else ""
            return
        if lowered == "table":
            self._flush_line()
            self._in_table = True
            self._table_index += 1
            self._table_headers = []
            self._row_index = 0
            self.lines.append(f"Table {self._table_index}")
            return
        if not self._in_table:
            return
        if lowered == "tr":
            self._row_cells = []
            self._row_flags = []
            return
        if lowered in {"th", "td"}:
            self._cell_buffer = []
            self._cell_is_header = lowered == "th"

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "head"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if lowered in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li"}:
            self._flush_line()
            self._prefix = ""
            return
        if not self._in_table:
            return
        if lowered in {"th", "td"}:
            text = _normalize_whitespace("".join(self._cell_buffer))
            self._row_cells.append(text)
            self._row_flags.append(self._cell_is_header)
            self._cell_buffer = []
            self._cell_is_header = False
            return
        if lowered == "tr":
            self._emit_row()
            return
        if lowered == "table":
            self._in_table = False
            self._table_headers = []
            self.lines.append("")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_table and (self._cell_buffer is not None):
            self._cell_buffer.append(data)
            return
        self._text_buffer.append(data)

    def as_text(self) -> str:
        self._flush_line()
        lines = [line.rstrip() for line in self.lines]
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines).strip() + "\n" if lines else ""

    def _flush_line(self) -> None:
        if not self._text_buffer:
            return
        text = _normalize_whitespace("".join(self._text_buffer))
        self._text_buffer = []
        if not text:
            return
        self.lines.append(f"{self._prefix}{text}".rstrip())

    def _emit_row(self) -> None:
        cells = [_normalize_whitespace(cell) for cell in self._row_cells]
        cells = [cell for cell in cells if cell]
        if not cells:
            return
        self._row_index += 1
        if not self._table_headers and any(self._row_flags):
            self._table_headers = cells
            self.lines.append("Headers: " + " | ".join(cells))
            return
        if self._table_headers and len(self._table_headers) == len(cells):
            pairs = [
                f"{header}: {value}"
                for header, value in zip(self._table_headers, cells, strict=True)
            ]
            self.lines.append(f"Row {self._row_index}: " + "; ".join(pairs))
            return
        self.lines.append(f"Row {self._row_index}: " + " | ".join(cells))


def render_word_accessible_preview(markdown_text: str, html_text: str | None = None) -> str:
    if html_text:
        parser = _AccessibleWordHtmlParser()
        parser.feed(html_text)
        parsed = parser.as_text()
        if parsed.strip():
            return parsed
    return _linearize_markdown_tables(markdown_text)


class WordDocumentSurface:
    def __init__(
        self,
        wx_module: object,
        parent: object,
        document: Document,
        on_change: Callable[[], None],
    ) -> None:
        self._wx = wx_module
        self._document = document
        self._on_change = on_change
        self._suspend_sync = False

        wx = self._wx
        self.panel = wx.Panel(parent)
        root = wx.BoxSizer(wx.VERTICAL)

        header = wx.BoxSizer(wx.HORIZONTAL)
        self._mode_button = wx.Button(self.panel, label="Use normal text editor")
        self._mode_button.Bind(wx.EVT_BUTTON, self._toggle_mode)
        header.Add(self._mode_button, 0, wx.RIGHT, 8)
        self._mode_label = wx.StaticText(self.panel, label="Word structure view")
        header.Add(self._mode_label, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(header, 0, wx.ALL, 6)

        self._notebook = wx.Notebook(self.panel)
        self._notebook.SetName("Word view")
        self._preview_page = wx.Panel(self._notebook)
        self._text_page = wx.Panel(self._notebook)
        self.preview = wx.TextCtrl(
            self._preview_page,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        )
        self.text_ctrl = wx.TextCtrl(
            self._text_page,
            style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_NOHIDESEL,
        )

        preview_sizer = wx.BoxSizer(wx.VERTICAL)
        preview_sizer.Add(self.preview, 1, wx.EXPAND)
        self._preview_page.SetSizer(preview_sizer)

        text_sizer = wx.BoxSizer(wx.VERTICAL)
        text_sizer.Add(self.text_ctrl, 1, wx.EXPAND)
        self._text_page.SetSizer(text_sizer)

        self._notebook.AddPage(self._preview_page, "Word view")
        self._notebook.AddPage(self._text_page, "Text")
        self._notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_page_changed)
        root.Add(self._notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self.panel.SetSizer(root)

        self._bind_events()
        self.ChangeValue(document.text)
        self.show_preview_mode()

    def __getattr__(self, name: str) -> object:
        active = self._active_control()
        if hasattr(active, name):
            return getattr(active, name)
        if hasattr(self.panel, name):
            return getattr(self.panel, name)
        raise AttributeError(name)

    def _active_control(self) -> object:
        return self.text_ctrl if self.is_text_mode() else self.preview

    def is_text_mode(self) -> bool:
        return self._notebook.GetSelection() == 1

    def show_preview_mode(self) -> None:
        self._notebook.ChangeSelection(0)
        self._mode_button.SetLabel("Use normal text editor")
        self._mode_label.SetLabel("Word structure view")
        self.preview.SetFocus()

    def show_text_mode(self) -> None:
        self._notebook.ChangeSelection(1)
        self._mode_button.SetLabel("Use Word view")
        self._mode_label.SetLabel("Normal text editor mode")
        self.text_ctrl.SetFocus()

    def toggle_mode(self) -> None:
        if self.is_text_mode():
            self.show_preview_mode()
        else:
            self.show_text_mode()

    def GetValue(self) -> str:
        return self.text_ctrl.GetValue()

    def ChangeValue(self, value: str) -> None:
        self._suspend_sync = True
        try:
            self.text_ctrl.ChangeValue(value)
            self._refresh_preview()
        finally:
            self._suspend_sync = False

    def SetEditable(self, editable: bool) -> None:
        self.text_ctrl.SetEditable(editable)

    def SetFocus(self) -> None:
        self._active_control().SetFocus()

    def GetSelection(self) -> tuple[int, int]:
        return self.text_ctrl.GetSelection()

    def SetSelection(self, start: int, end: int) -> None:
        self.text_ctrl.SetSelection(start, end)

    def GetInsertionPoint(self) -> int:
        return self.text_ctrl.GetInsertionPoint()

    def SetInsertionPoint(self, position: int) -> None:
        self.text_ctrl.SetInsertionPoint(position)

    def Replace(self, start: int, end: int, value: str) -> None:
        self._ensure_text_mode()
        self.text_ctrl.Replace(start, end, value)

    def Cut(self) -> None:
        if self.is_text_mode():
            self.text_ctrl.Cut()

    def Copy(self) -> None:
        active = self._active_control()
        copier = getattr(active, "Copy", None)
        if callable(copier):
            copier()

    def Paste(self) -> None:
        self._ensure_text_mode()
        self.text_ctrl.Paste()

    def Undo(self) -> None:
        self._ensure_text_mode()
        if self.text_ctrl.CanUndo():
            self.text_ctrl.Undo()

    def Redo(self) -> None:
        self._ensure_text_mode()
        if self.text_ctrl.CanRedo():
            self.text_ctrl.Redo()

    def bind_editor_events(self, frame: object) -> None:
        wx = self._wx
        self.text_ctrl.Bind(wx.EVT_TEXT, lambda _event: self._on_text_changed())
        self.text_ctrl.Bind(wx.EVT_KEY_DOWN, frame._on_editor_key_down)
        self.text_ctrl.Bind(wx.EVT_KEY_UP, frame._on_editor_key_up)
        self.text_ctrl.Bind(wx.EVT_LEFT_UP, frame._on_editor_caret_activity)
        self.text_ctrl.Bind(wx.EVT_SET_FOCUS, frame._on_editor_caret_activity)
        self.text_ctrl.Bind(wx.EVT_CONTEXT_MENU, frame._on_editor_context_menu)
        self._bind_preview_events(frame)

    def _bind_events(self) -> None:
        pass

    def _bind_preview_events(self, frame: object) -> None:
        wx = self._wx
        if hasattr(self.preview, "Bind"):
            self.preview.Bind(wx.EVT_SET_FOCUS, frame._on_editor_caret_activity)
            self.preview.Bind(wx.EVT_CONTEXT_MENU, frame._on_editor_context_menu)

    def _toggle_mode(self, _event: object) -> None:
        self.toggle_mode()

    def _on_page_changed(self, _event: object) -> None:
        if self.is_text_mode():
            self._mode_button.SetLabel("Use Word view")
            self._mode_label.SetLabel("Normal text editor mode")
        else:
            self._mode_button.SetLabel("Use normal text editor")
            self._mode_label.SetLabel("Word structure view")

    def _on_text_changed(self) -> None:
        if self._suspend_sync:
            return
        self._refresh_preview(prefer_source=False)
        self._on_change()

    def _refresh_preview(self, prefer_source: bool = True) -> None:
        preview_text = self._render_preview_text(prefer_source=prefer_source)
        self.preview.ChangeValue(preview_text)

    def _render_preview_text(self, prefer_source: bool = False) -> str:
        text = self.text_ctrl.GetValue()
        source_html: str | None = None
        if prefer_source and self._document.path is not None:
            try:
                converted = convert_document_with_pandoc(self._document.path, "html")
            except (PandocUnavailableError, PandocConversionError, OSError, ValueError):
                pass
            else:
                source_html = converted.text
        return render_word_accessible_preview(text, source_html)

    def _ensure_text_mode(self) -> None:
        if not self.is_text_mode():
            self.show_text_mode()
