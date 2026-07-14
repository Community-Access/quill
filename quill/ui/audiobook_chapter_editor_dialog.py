"""Chapter review/edit dialog for audiobook assembly.

A focused, keyboard-first ``wx.Dialog`` that lets the user **rename**, **reorder**,
and **merge** chapters before the audiobook is built. It edits a plan over a fixed
set of audio files — it does not scan or build anything itself. :meth:`show`
returns the edited plan (a list of ``(title, [file paths])``) or ``None`` on
cancel; the caller (``batch_speech_runner``) feeds the plan into
``quill.core.speech.audiobook.chapters_from_plan``.

This is the rename/reorder/merge editor that used to live in the standalone
``audiobook_builder_dialog`` (now folded into the Batch Export dialog); it is split
out here so the editor can be shown on demand — after synthesis, or for a folder of
pre-recorded audio — instead of being wired into one big dialog.

Per the NVDA focus rule (A11Y-SR-2) every control is parented directly on the
dialog. It is opened only via ``MainFrame._show_modal_dialog`` and wires its
OK/Cancel ids through ``apply_modal_ids`` so Escape closes it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    show_message_box,
)


@dataclass(slots=True)
class _Chapter:
    """One editable chapter row: a title and its merged file(s)."""

    title: str
    paths: list[str]

    def label(self) -> str:
        """List display text, noting a merge so the count is spoken/visible."""
        if len(self.paths) > 1:
            return f"{self.title}  ({len(self.paths)} files)"
        return self.title


class ChapterEditorDialog:
    """Rename / reorder / merge chapters before building an audiobook."""

    def __init__(
        self,
        parent: object,
        *,
        rows: list[tuple[str, str]],
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce_fn = announce
        self._result: list[tuple[str, list[str]]] | None = None
        # One row per chapter; each starts as a single file. The original rows
        # are kept so Restore can undo any amount of editing in one press.
        self._original_rows = list(rows)
        self._chapters: list[_Chapter] = self._chapters_from_rows(rows)

        self.dialog = wx.Dialog(
            parent,
            title="Review Audiobook Chapters",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(560, 480))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(
                self.dialog,
                label="C&hapters (each is a navigable marker; rename, reorder, or merge):",
            ),
            0,
            wx.LEFT | wx.TOP,
            8,
        )
        self._chapter_list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._chapter_list.SetName("Chapters")
        self._chapter_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_chapter_selected())
        apply_listbox_activation(self._chapter_list, lambda _e: self._focus_title_edit())
        root.Add(self._chapter_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        title_row = wx.BoxSizer(wx.HORIZONTAL)
        title_row.Add(
            wx.StaticText(self.dialog, label="Chapter t&itle:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._title_edit = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self._title_edit.SetName("Chapter title")
        self._title_edit.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._on_rename())
        rename_btn = wx.Button(self.dialog, label="Re&name")
        rename_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_rename())
        title_row.Add(self._title_edit, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        title_row.Add(rename_btn, 0)
        root.Add(title_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        order_row = wx.BoxSizer(wx.HORIZONTAL)
        self._up_btn = wx.Button(self.dialog, label="Move &Up")
        self._down_btn = wx.Button(self.dialog, label="Move &Down")
        self._merge_btn = wx.Button(self.dialog, label="&Merge into previous")
        self._remove_btn = wx.Button(self.dialog, label="Remo&ve")
        self._up_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_move(-1))
        self._down_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_move(1))
        self._merge_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_merge_up())
        self._remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_remove())
        order_row.Add(self._up_btn, 0, wx.RIGHT, 6)
        order_row.Add(self._down_btn, 0, wx.RIGHT, 6)
        order_row.Add(self._merge_btn, 0, wx.RIGHT, 6)
        order_row.Add(self._remove_btn, 0)
        root.Add(order_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        io_row = wx.BoxSizer(wx.HORIZONTAL)
        import_btn = wx.Button(self.dialog, label="Import ti&tles...")
        export_btn = wx.Button(self.dialog, label="E&xport titles...")
        restore_btn = wx.Button(self.dialog, label="Rest&ore original")
        import_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_import_titles())
        export_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_export_titles())
        restore_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_restore())
        io_row.Add(import_btn, 0, wx.RIGHT, 6)
        io_row.Add(export_btn, 0, wx.RIGHT, 6)
        io_row.Add(restore_btn, 0)
        root.Add(io_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        build_btn = wx.Button(self.dialog, id=wx.ID_OK, label="&Build audiobook")
        cancel_btn = wx.Button(self.dialog, id=wx.ID_CANCEL)
        build_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        btn_row.AddStretchSpacer()
        btn_row.Add(build_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.dialog.SetSizer(root)
        self.dialog.Fit()
        self._refresh_chapter_list()

    # ------------------------------------------------------------- chapter edit

    @staticmethod
    def _chapters_from_rows(rows: list[tuple[str, str]]) -> list[_Chapter]:
        return [
            _Chapter(title=(title.strip() or f"Chapter {i}"), paths=[path])
            for i, (path, title) in enumerate(rows, start=1)
        ]

    def _refresh_chapter_list(self, *, select: int = -1) -> None:
        self._chapter_list.Set([c.label() for c in self._chapters])
        if self._chapters:
            index = select if 0 <= select < len(self._chapters) else 0
            self._chapter_list.SetSelection(index)
        self._on_chapter_selected()

    def _selected_index(self) -> int:
        idx = self._chapter_list.GetSelection()
        return idx if 0 <= idx < len(self._chapters) else -1

    def _focus_title_edit(self) -> None:
        if self._selected_index() >= 0:
            self._title_edit.SetFocus()
            self._title_edit.SelectAll()

    def _on_chapter_selected(self) -> None:
        idx = self._selected_index()
        has = idx >= 0
        self._title_edit.SetValue(self._chapters[idx].title if has else "")
        self._title_edit.Enable(has)
        self._up_btn.Enable(has and idx > 0)
        self._down_btn.Enable(has and idx < len(self._chapters) - 1)
        # Merge folds a chapter into the one above it, so it needs a predecessor.
        self._merge_btn.Enable(has and idx > 0)

    def _on_rename(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        new_title = self._title_edit.GetValue().strip()
        if not new_title:
            self._error("A chapter title cannot be empty.")
            return
        self._chapters[idx].title = new_title
        self._refresh_chapter_list(select=idx)
        self._announce(f"Renamed chapter to {new_title}")

    def _on_move(self, delta: int) -> None:
        idx = self._selected_index()
        target = idx + delta
        if idx < 0 or not (0 <= target < len(self._chapters)):
            return
        self._chapters[idx], self._chapters[target] = (
            self._chapters[target],
            self._chapters[idx],
        )
        self._refresh_chapter_list(select=target)
        self._announce(f"Moved chapter {'up' if delta < 0 else 'down'} to position {target + 1}")

    def _on_merge_up(self) -> None:
        idx = self._selected_index()
        if idx <= 0:
            return
        previous = self._chapters[idx - 1]
        folded = self._chapters.pop(idx)
        previous.paths.extend(folded.paths)
        self._refresh_chapter_list(select=idx - 1)
        self._announce(f"Merged into previous chapter — {previous.label()}")

    def _on_remove(self) -> None:
        idx = self._selected_index()
        if idx < 0 or len(self._chapters) <= 1:
            self._error("At least one chapter must remain in the book.")
            return
        dropped = self._chapters.pop(idx)
        self._refresh_chapter_list(select=min(idx, len(self._chapters) - 1))
        self._announce(f"Removed {dropped.title}; {len(self._chapters)} chapters remain")

    def _on_restore(self) -> None:
        self._chapters = self._chapters_from_rows(self._original_rows)
        self._refresh_chapter_list()
        self._announce(f"Restored the original {len(self._chapters)} chapters")

    def _on_import_titles(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            "Import chapter titles",
            wildcard=(
                "Chapter lists (*.txt;*.cue;*.json;*.csv)|*.txt;*.cue;*.json;*.csv|"
                "All files (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            path = dlg.GetPath()
        from quill.core.speech.chapter_io import titles_from_text

        try:
            titles = titles_from_text(Path(path).read_text(encoding="utf-8-sig"))
        except OSError as exc:
            self._error(f"Could not read that file: {exc}")
            return
        if not titles:
            self._error("No chapter titles were found in that file.")
            return
        renamed = 0
        for chapter, title in zip(self._chapters, titles, strict=False):
            chapter.title = title
            renamed += 1
        self._refresh_chapter_list()
        self._announce(f"Imported {renamed} title(s) from {Path(path).name}")

    def _on_export_titles(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            "Export chapter titles",
            wildcard="Text (*.txt)|*.txt",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            path = dlg.GetPath()
        try:
            Path(path).write_text("".join(f"{c.title}\n" for c in self._chapters), encoding="utf-8")
        except OSError as exc:
            self._error(f"Could not write that file: {exc}")
            return
        self._announce(f"Exported {len(self._chapters)} title(s) to {Path(path).name}")

    def _announce(self, text: str) -> None:
        if self._announce_fn is not None:
            self._announce_fn(text)

    def _error(self, message: str) -> None:
        show_message_box(
            message, "Review Audiobook Chapters", self._wx.OK | self._wx.ICON_ERROR, self.dialog
        )

    # ------------------------------------------------------------------ public

    def _on_ok(self, evt: object) -> None:
        self._result = [(c.title, list(c.paths)) for c in self._chapters]
        evt.Skip()  # let ID_OK close the dialog

    def show(
        self, show_modal_dialog: Callable[[object, str], int]
    ) -> list[tuple[str, list[str]]] | None:
        """Open the dialog; return the edited ``(title, [paths])`` plan, or ``None``."""
        code = show_modal_dialog(self.dialog, "Review Audiobook Chapters")
        result = self._result if code == self._wx.ID_OK else None
        self.dialog.Destroy()
        return result
