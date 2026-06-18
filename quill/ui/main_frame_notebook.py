"""Notebook (Workspace) UI layer — NotebookUIMixin (§10.4 Milestone 2).

Mixin added to ``MainFrame``'s MRO.  Every method reaches ``wx``, the frame,
and sibling helpers via ``self``; no module-level ``wx`` import is needed here.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.notebook_store import (
    NotebookFormatError,
    create_notebook,
    create_notebook_from_folder,
    load_notebook,
    save_notebook,
)
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.notebook_navigator_page import _NotebookNode, build_notebook_nodes


class NotebookUIMixin:
    """Menu handlers and helpers for Notebook (Workspace) commands."""

    # ------------------------------------------------------------------
    # File menu commands
    # ------------------------------------------------------------------

    def new_notebook(self) -> None:
        wx = self._wx
        with wx.TextEntryDialog(
            self.frame,
            "Notebook name:",
            "New Notebook",
            value="My Notebook",
        ) as dlg:
            if self._show_modal_dialog(dlg, "New Notebook") != wx.ID_OK:
                return
            name = dlg.GetValue().strip()
        if not name:
            return
        with wx.FileDialog(
            self.frame,
            "Save notebook as",
            wildcard="QUILL Notebooks (*.quillnotebook)|*.quillnotebook",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if self._show_modal_dialog(dlg, "Save Notebook As") != wx.ID_OK:
                return
            path = Path(dlg.GetPath())
        try:
            nb = create_notebook(name, path=path)
        except OSError as exc:
            self._show_message_box(
                f"Could not create notebook:\n{exc}",
                "New Notebook",
                wx.OK | wx.ICON_ERROR,
            )
            return
        self._active_notebook = nb
        if hasattr(self, "_entries_panel"):
            self._entries_panel.load(nb)
        self._set_status(f'Notebook "{nb.name}" created.')
        self._refresh_statusbar()

    def new_notebook_from_folder(self) -> None:
        wx = self._wx
        with wx.DirDialog(
            self.frame,
            "Choose folder to import",
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dlg:
            if self._show_modal_dialog(dlg, "Choose Folder") != wx.ID_OK:
                return
            folder = Path(dlg.GetPath())
        name = folder.name
        with wx.TextEntryDialog(
            self.frame,
            "Notebook name:",
            "New Notebook from Folder",
            value=name,
        ) as dlg:
            if self._show_modal_dialog(dlg, "New Notebook from Folder") != wx.ID_OK:
                return
            name = dlg.GetValue().strip() or name
        with wx.FileDialog(
            self.frame,
            "Save notebook as",
            wildcard="QUILL Notebooks (*.quillnotebook)|*.quillnotebook",
            defaultFile=f"{name}.quillnotebook",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if self._show_modal_dialog(dlg, "Save Notebook As") != wx.ID_OK:
                return
            path = Path(dlg.GetPath())
        try:
            nb = create_notebook_from_folder(folder, path=path, name=name)
        except OSError as exc:
            self._show_message_box(
                f"Could not create notebook:\n{exc}",
                "New Notebook from Folder",
                wx.OK | wx.ICON_ERROR,
            )
            return
        self._active_notebook = nb
        if hasattr(self, "_entries_panel"):
            self._entries_panel.load(nb)
        count = len(nb.entries)
        self._set_status(f'Notebook "{nb.name}" created with {count} entries.')
        self._refresh_statusbar()

    def open_notebook(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Open notebook",
            wildcard="QUILL Notebooks (*.quillnotebook)|*.quillnotebook",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if self._show_modal_dialog(dlg, "Open Notebook") != wx.ID_OK:
                return
            path = Path(dlg.GetPath())
        try:
            nb = load_notebook(path)
        except NotebookFormatError as exc:
            self._show_message_box(
                f"Could not open notebook:\n{exc}",
                "Open Notebook",
                wx.OK | wx.ICON_ERROR,
            )
            return
        except OSError as exc:
            self._show_message_box(
                f"Could not read notebook file:\n{exc}",
                "Open Notebook",
                wx.OK | wx.ICON_ERROR,
            )
            return
        self._active_notebook = nb
        if hasattr(self, "_entries_panel"):
            self._entries_panel.load(nb)
        self._set_status(f'Notebook "{nb.name}" opened ({len(nb.entries)} entries).')
        self._refresh_statusbar()

    def notebook_save_snapshot(self) -> None:
        wx = self._wx
        nb = getattr(self, "_active_notebook", None)
        if nb is None:
            self._show_message_box(
                "No notebook is open.",
                "Save Snapshot",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        active_id = None
        tab_idx = getattr(self, "_active_tab_index", -1)
        tabs = getattr(self, "_document_tabs", [])
        if 0 <= tab_idx < len(tabs):
            doc = getattr(tabs[tab_idx], "document", None)
            doc_path = getattr(doc, "path", None) if doc is not None else None
            root_dir = getattr(nb, "root_dir", None)
            if doc_path is not None and root_dir:
                try:
                    rel = str(Path(doc_path).relative_to(root_dir))
                    entry = nb.entry_by_path(rel)
                    if entry:
                        active_id = entry.id
                except ValueError:
                    pass
        open_ids = [e.id for e in getattr(nb, "entries", [])]
        with wx.TextEntryDialog(
            self.frame,
            "Snapshot name:",
            "Save Snapshot",
            value=f"Snapshot {len(getattr(nb, 'snapshots', [])) + 1}",
        ) as dlg:
            if self._show_modal_dialog(dlg, "Save Snapshot") != wx.ID_OK:
                return
            snap_name = dlg.GetValue().strip()
        if not snap_name:
            return
        nb.save_snapshot(snap_name, open_ids, active_id)
        nb_path = getattr(nb, "path", None)
        if nb_path is not None:
            try:
                save_notebook(nb, nb_path)
            except OSError as exc:
                self._show_message_box(
                    f"Snapshot saved in memory but could not write to disk:\n{exc}",
                    "Save Snapshot",
                    wx.OK | wx.ICON_WARNING,
                )
                return
        self._set_status(f'Snapshot "{snap_name}" saved.')

    def manage_notebook_snapshots(self) -> None:
        wx = self._wx
        nb = getattr(self, "_active_notebook", None)
        if nb is None:
            self._show_message_box(
                "No notebook is open.",
                "Manage Snapshots",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        dialog = wx.Dialog(self.frame, title="Manage Snapshots", size=(520, 420))
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(wx.StaticText(dialog, label="Snapshots:"), 0, wx.ALL, 8)
        listbox = wx.ListBox(dialog, style=wx.LB_SINGLE)
        for snap in getattr(nb, "snapshots", []):
            created = getattr(snap, "created", "")[:10]
            listbox.Append(f"{snap.name}  ({created})", snap.id)
        outer.Add(listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_rename = wx.Button(dialog, label="Re&name")
        btn_delete = wx.Button(dialog, label="&Delete")
        btn_close = wx.Button(dialog, wx.ID_CLOSE, label="&Close")
        btn_sizer.Add(btn_rename, 0, wx.RIGHT, 4)
        btn_sizer.Add(btn_delete, 0, wx.RIGHT, 4)
        btn_sizer.Add(btn_close, 0)
        outer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)
        dialog.SetSizer(outer)
        apply_modal_ids(dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)

        def _save_nb() -> None:
            nb_path = getattr(nb, "path", None)
            if nb_path is not None:
                try:
                    save_notebook(nb, nb_path)
                except OSError:
                    pass

        def on_rename(_event: object) -> None:
            idx = listbox.GetSelection()
            if idx == wx.NOT_FOUND:
                return
            snap_id = listbox.GetClientData(idx)
            snap = nb.snapshot_by_id(snap_id)
            if snap is None:
                return
            with wx.TextEntryDialog(
                dialog, "New snapshot name:", "Rename Snapshot", value=snap.name
            ) as name_dlg:
                if self._show_modal_dialog(name_dlg, "Rename Snapshot") != wx.ID_OK:
                    return
                new_name = name_dlg.GetValue().strip()
            if new_name and new_name != snap.name:
                snap.name = new_name
                created = getattr(snap, "created", "")[:10]
                listbox.SetString(idx, f"{snap.name}  ({created})")
                _save_nb()

        def on_delete(_event: object) -> None:
            idx = listbox.GetSelection()
            if idx == wx.NOT_FOUND:
                return
            snap_id = listbox.GetClientData(idx)
            if nb.remove_snapshot(snap_id):
                listbox.Delete(idx)
                _save_nb()

        btn_rename.Bind(wx.EVT_BUTTON, on_rename)
        btn_delete.Bind(wx.EVT_BUTTON, on_delete)
        btn_close.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
        try:
            self._show_modal_dialog(dialog, "Manage Snapshots")
        finally:
            dialog.Destroy()

    # ------------------------------------------------------------------
    # View menu
    # ------------------------------------------------------------------

    def toggle_entries_panel(self) -> None:
        splitter = getattr(self, "_main_splitter", None)
        entries_panel = getattr(self, "_entries_panel", None)
        if splitter is None or entries_panel is None:
            return
        if getattr(self, "_entries_panel_visible", False):
            splitter.Unsplit(entries_panel.panel)
            self._entries_panel_visible = False
        else:
            splitter.SplitVertically(entries_panel.panel, self._documents_panel, 220)
            self._entries_panel_visible = True
            nb = getattr(self, "_active_notebook", None)
            if nb is not None:
                entries_panel.load(nb)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None and hasattr(self, "_id_toggle_entries_panel"):
            menu_bar.Check(int(self._id_toggle_entries_panel), self._entries_panel_visible)

    # ------------------------------------------------------------------
    # Navigate menu
    # ------------------------------------------------------------------

    def go_to_entry_in_notebook(self) -> None:
        wx = self._wx
        nb = getattr(self, "_active_notebook", None)
        if nb is None:
            self._show_message_box(
                "No notebook is open.  Use File > Open Notebook to open one.",
                "Go to Entry",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        if not getattr(nb, "entries", []):
            self._set_status("The notebook has no entries.")
            return
        nodes = build_notebook_nodes(nb)
        payload = self._show_tree_navigator(
            title="Go to Entry in Notebook",
            root_label=getattr(nb, "name", "Notebook"),
            nodes=nodes,
        )
        if payload is None:
            return
        # payload may be a NotebookEntry (leaf) or the first entry in a group node
        path_str = getattr(payload, "path", None)
        if path_str is None:
            return
        root_dir = getattr(nb, "root_dir", None)
        full_path = (Path(root_dir) / path_str) if root_dir else Path(path_str)
        if full_path.exists():
            self.open_file(full_path)
        else:
            self._set_status(f"Entry file not found: {path_str}")

    def go_to_heading_in_notebook(self) -> None:
        wx = self._wx
        nb = getattr(self, "_active_notebook", None)
        if nb is None:
            self._show_message_box(
                "No notebook is open.",
                "Go to Heading in Notebook",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        nodes = self._build_notebook_heading_nodes(nb)
        if not nodes:
            self._set_status("No headings found in notebook entries.")
            return
        payload = self._show_tree_navigator(
            title="Headings in Notebook",
            root_label=getattr(nb, "name", "Notebook"),
            nodes=nodes,
        )
        if payload is None:
            return
        file_path, char_pos = payload
        p = Path(file_path)
        if p.exists():
            self.open_file(p)
            if char_pos > 0:
                wx.CallAfter(self._jump_to, char_pos, "Jumped to heading")

    def go_to_bookmark_in_notebook(self) -> None:
        wx = self._wx
        nb = getattr(self, "_active_notebook", None)
        if nb is None:
            self._show_message_box(
                "No notebook is open.",
                "Go to Bookmark in Notebook",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        bookmarks = getattr(self, "_bookmarks", {})
        if not bookmarks:
            self._set_status("No bookmarks set in the current document.")
            return
        self.go_to_bookmark()

    def go_to_sticky_note_in_notebook(self) -> None:
        wx = self._wx
        nb = getattr(self, "_active_notebook", None)
        if nb is None:
            self._show_message_box(
                "No notebook is open.",
                "Go to Sticky Note in Notebook",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        self.manage_sticky_notes()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_notebook_heading_nodes(self, nb: object) -> list[_NotebookNode]:
        """Scan all notebook entry files and return a heading tree.

        One parent node per entry file; child nodes are the headings found
        inside that file.  Files that cannot be read or have no headings are
        silently skipped.
        """
        root_dir = getattr(nb, "root_dir", None)
        nodes: list[_NotebookNode] = []
        for entry in getattr(nb, "entries", []):
            path_str = getattr(entry, "path", "")
            title = getattr(entry, "title", None) or path_str
            full_path = (Path(root_dir) / path_str) if root_dir else Path(path_str)
            children: list[_NotebookNode] = []
            try:
                text = full_path.read_text(encoding="utf-8", errors="ignore")
                pos = 0
                for line in text.splitlines(keepends=True):
                    stripped = line.rstrip("\r\n")
                    if stripped.startswith("#"):
                        heading_text = stripped.lstrip("#").strip()
                        children.append(
                            _NotebookNode(
                                label=heading_text,
                                preview=stripped,
                                payload=(str(full_path), pos),
                                action_label="Jump to Heading",
                                children=[],
                            )
                        )
                    pos += len(line)
            except OSError:
                pass
            if children:
                nodes.append(
                    _NotebookNode(
                        label=title,
                        preview=path_str,
                        payload=(str(full_path), 0),
                        action_label="Open Entry",
                        children=children,
                    )
                )
        return nodes
