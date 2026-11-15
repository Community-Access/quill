"""Lists in and out of the WordPress Workbench (PRD 15.10; W7).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- **Export List** (Ctrl+Shift+X): the list as it is shown -- its columns, its
  filter, its rows -- as Excel, CSV or a Markdown table (the QUILL table the
  editor's table commands read).
- **Import Posts from a Spreadsheet** (Ctrl+Shift+I): the preview starts with
  which column fills which field and which columns are left out, then a line
  per row; afterwards, a report with a sentence per row.
- **Import a Folder of Documents** (Ctrl+Alt+Shift+I): each Markdown, text or
  Word file a draft, previewed file by file, reported file by file; pictures
  beside a document are uploaded and links between the documents pointed at
  their drafts (:mod:`quill.core.wordpress.workbench_carry`).

Every one ends by naming what it left out (WP-G).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from quill.core.wordpress.workbench_carry import (
    SPREADSHEET_LEFT_OUT,
    export_left_out,
    folder_left_out,
    left_out_section,
    send_folder,
)
from quill.core.wordpress.workbench_io import (
    export_rows,
    folder_plan,
    import_mapping,
    import_plan,
    mapping_lines,
    read_spreadsheet,
    send_import_results,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchListCommands", "read_document"]


def read_document(path: Path) -> str:
    """A Markdown, text or Word file as Markdown, through the editor's own Word reader."""
    if path.suffix.lower() == ".docx":
        from quill.io.docx_text import read_docx_text, read_docx_xml_text

        return read_docx_text(path) or read_docx_xml_text(path)
    return path.read_text(encoding="utf-8-sig")


class WorkbenchListCommands:
    """Export List, Import Posts from a Spreadsheet, Import a Folder of Documents."""

    frame: Any
    parent: Any
    history: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    _site_now: Callable[[Any], str]

    def _file(self, title: str, wildcard: str, *, save: bool) -> Path | None:
        wx = self.frame._wx
        style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT if save else wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        dialog = wx.FileDialog(self.parent, title, wildcard=wildcard, style=style)
        try:
            if self.show_modal(dialog, title) != wx.ID_OK:
                return None
            return Path(dialog.GetPath())
        finally:
            dialog.Destroy()

    def _folder(self, title: str) -> Path | None:
        wx = self.frame._wx
        dialog = wx.DirDialog(self.parent, title, style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        try:
            if self.show_modal(dialog, title) != wx.ID_OK:
                return None
            return Path(dialog.GetPath())
        finally:
            dialog.Destroy()

    def do_export_list(self, _ref: Any, _row: WbRow | None) -> None:
        frame = self.frame
        if frame is None or not frame.rows:
            self.say("There is nothing in the list to export.")
            return
        path = self._file(
            "Export List",
            "Excel workbook (*.xlsx)|*.xlsx|CSV (*.csv)|*.csv|Markdown table (*.md)|*.md",
            save=True,
        )
        if path is None:
            return
        node = frame.node(frame.current)
        columns = frame.provider.columns(node)
        from quill.core.wordpress.workbench_listing import column_title

        rows = [frame.provider.cells(r, columns) for r in frame.rows]
        count = export_rows(path, [column_title(c) for c in columns], rows)
        every = [column_title(c) for c in (getattr(node, "columns", ()) or ())]
        left_out = export_left_out([column_title(c) for c in columns], every)
        self.say(f"Exported {count} rows to {path.name}. {left_out}")

    def _kind_here(self, ref: Any) -> str:
        return "page" if ref is not None and ref.key.startswith("pages") else "post"

    def _import(
        self,
        site: str,
        kind: str,
        plan: Sequence[Any],
        head: Sequence[str],
        *,
        left_out: Sequence[str] = (),
        folder: bool = False,
    ) -> None:
        ready = [r for r in plan if not r.problem]
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Import into {site}",
            summary=f"{len(ready)} {kind}s will be made on {site} as drafts (or pending or "
            f"private, where a Status column says so); {len(plan) - len(ready)} are skipped.",
            lines=[*head, *(r.sentence for r in plan)],
            yes="Import",
        ):
            return
        api = self.ctx(site).api

        def send() -> list[str]:
            if folder:
                return send_folder(api, kind, plan)
            return send_import_results(api, kind, plan) + left_out_section(left_out)

        def done(said: list[str]) -> None:
            made = sum(1 for s in said if s.startswith("Made"))
            self.history.record(Change(site, f"Imported {made} {kind}s into {site}."))
            self.say(f"Imported {made} of {len(plan)} into {site}.")
            dlg.show_report(
                self.parent,
                self.show_modal,
                title=f"Import into {site}",
                text="\n".join(said),
                help_text="What happened to each row or file of the import, then what it left out.",
            )
            self.refresh()

        self.background("importing", send, done)

    def do_import_posts(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        path = self._file(
            "Import Posts from a Spreadsheet",
            "Spreadsheets (*.xlsx;*.csv)|*.xlsx;*.csv",
            save=False,
        )
        if path is None:
            return
        try:
            rows = read_spreadsheet(path)
        except Exception as exc:  # noqa: BLE001 - a broken file is a sentence, not a crash
            self.say(f"{path.name} could not be read: {exc}")
            return
        headers = list(rows[0]) if rows else []
        mapping, ignored = import_mapping(headers)
        plan = import_plan(rows)
        left_out = [f"columns matching no field: {', '.join(ignored)}" if ignored else ""]
        left_out += [f"{r.where}: {r.problem}" for r in plan if r.problem]
        left_out.append(SPREADSHEET_LEFT_OUT)
        head = mapping_lines(mapping, ignored)
        self._import(site, self._kind_here(ref), plan, head, left_out=left_out)

    def do_import_folder(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_now(ref)
        if not site:
            return
        folder = self._folder("Import a Folder of Documents")
        if folder is None:
            return
        kind = self._kind_here(ref)

        def read(plan: list[Any]) -> None:
            if not plan:
                self.say(f"{folder.name} has no Markdown, text or Word files.")
                return
            head = [
                "Each file's first heading is its title; files are made in name order. "
                "Pictures beside a file are uploaded, and links between the files are "
                "pointed at their drafts.",
                *(f"Left out: {line}." for line in folder_left_out(plan)),
            ]
            self._import(site, kind, plan, head, folder=True)

        self.background("reading the folder", lambda: folder_plan(folder, read_document), read)
