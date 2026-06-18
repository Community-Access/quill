"""Workspace-session (snapshot) lifecycle for ``MainFrame`` (CQ-1).

Extracted verbatim from ``main_frame.py`` into a cohesive mixin so the UI
monolith shrinks without any behaviour change. ``MainFrame`` inherits
``SessionsMixin`` and every method resolves identically through the MRO; the
methods reference instance state and sibling methods via ``self`` exactly as
before. Covers the Sessions and Recent-Sessions menus, the open-documents
submenu, and the save/open workspace-snapshot commands.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.document import Document
from quill.core.locations import LocationRing
from quill.core.sessions import (
    active_index_from_session,
    add_recent_session,
    build_session_payload,
    caret_positions_from_session,
    clear_recent_sessions,
    documents_from_session,
    load_recent_sessions,
    load_session,
    session_title,
)
from quill.core.sessions import (
    save_session as save_session_file,
)


class SessionsMixin:
    def _refresh_sessions_menu(self) -> None:
        if not hasattr(self, "_sessions_menu") or not hasattr(self, "_wx"):
            return
        if not self._menu_updates_allowed():
            self._request_menu_refresh()
            return
        try:
            while self._sessions_menu.GetMenuItemCount() > 0:
                item = self._sessions_menu.FindItemByPosition(0)
                if item is None:
                    break
                self._sessions_menu.DestroyItem(item)
            while self._open_documents_menu.GetMenuItemCount() > 0:
                item = self._open_documents_menu.FindItemByPosition(0)
                if item is None:
                    break
                self._open_documents_menu.DestroyItem(item)
            while self._recent_sessions_menu.GetMenuItemCount() > 0:
                item = self._recent_sessions_menu.FindItemByPosition(0)
                if item is None:
                    break
                self._recent_sessions_menu.DestroyItem(item)
        except RuntimeError:
            return
        self._session_menu_ids.clear()
        self._recent_session_menu_ids.clear()
        self._sessions_menu.Append(
            self._id_save_session,
            self._menu_label("Save &Snapshot...", "file.save_session"),
        )
        self._sessions_menu.Append(
            self._id_open_session,
            self._menu_label("&Open Snapshot...", "file.open_session"),
        )
        self._sessions_menu.AppendSubMenu(
            self._recent_sessions_menu,
            "Recent &Snapshots",
        )
        self._sessions_menu.AppendSeparator()
        self._sessions_menu.AppendSubMenu(
            self._open_documents_menu,
            "Open &Documents in Current Workspace",
        )
        self._refresh_recent_sessions_menu()
        self._refresh_window_docs_menu()
        if not self._document_tabs:
            item = self._open_documents_menu.Append(
                self._wx.ID_ANY, "(No open documents in workspace)"
            )
            item.Enable(False)
            return
        for index, tab in enumerate(self._document_tabs):
            menu_id = self._wx.NewIdRef()
            label = tab.document.name
            if index == self._active_tab_index:
                label = f"{label} (active)"
            self._open_documents_menu.Append(menu_id, label)
            self._session_menu_ids[int(menu_id)] = index

    def _refresh_window_docs_menu(self) -> None:
        window_menu = getattr(self, "_window_menu", None)
        if window_menu is None or not hasattr(self, "_wx"):
            return
        ids = getattr(self, "_window_doc_menu_ids", {})
        try:
            for menu_id in list(ids.keys()):
                item = window_menu.FindItemById(menu_id)
                if item is not None:
                    window_menu.DestroyItem(item)
        except RuntimeError:
            return
        ids.clear()
        tabs = getattr(self, "_document_tabs", None)
        if not tabs:
            return
        active = getattr(self, "_active_tab_index", -1)
        for i, tab in enumerate(tabs):
            doc_id = self._wx.NewIdRef()
            name = getattr(tab.document, "name", f"Document {i + 1}")
            suffix = " (active)" if i == active else ""
            window_menu.Append(doc_id, f"&{i + 1}: {name}{suffix}")
            ids[int(doc_id)] = i
        self._window_doc_menu_ids = ids

    def _on_window_doc_menu(self, event: object) -> None:
        menu_id = event.GetId()
        ids = getattr(self, "_window_doc_menu_ids", {})
        index = ids.get(menu_id)
        if index is None:
            event.Skip()
            return
        self._select_tab(index)

    def _refresh_recent_sessions_menu(self) -> None:
        if not hasattr(self, "_recent_sessions_menu") or not hasattr(self, "_wx"):
            return
        if not self._menu_updates_allowed():
            self._request_menu_refresh()
            return
        while self._recent_sessions_menu.GetMenuItemCount() > 0:
            item = self._recent_sessions_menu.FindItemByPosition(0)
            if item is None:
                break
            self._recent_sessions_menu.DestroyItem(item)
        self._recent_session_menu_ids.clear()
        recent_sessions = load_recent_sessions()
        self._recent_sessions = recent_sessions
        if not recent_sessions:
            item = self._recent_sessions_menu.Append(
                self._wx.ID_ANY, "(No saved workspace snapshots)"
            )
            item.Enable(False)
            self._recent_sessions_menu.AppendSeparator()
            self._recent_sessions_menu.Append(
                self._id_clear_recent_sessions,
                "C&lear Recent Workspace Snapshots",
            )
            return
        for path in recent_sessions:
            payload = load_session(path)
            label = session_title(payload, path.stem)
            menu_id = self._wx.NewIdRef()
            self._recent_sessions_menu.Append(menu_id, label)
            self._recent_session_menu_ids[int(menu_id)] = path
        self._recent_sessions_menu.AppendSeparator()
        self._recent_sessions_menu.Append(
            self._id_clear_recent_sessions,
            "C&lear Recent Workspace Snapshots",
        )

    def _on_session_menu(self, event: object) -> None:
        menu_id = event.GetId()
        index = self._session_menu_ids.get(menu_id)
        if index is None:
            event.Skip()
            return
        self._select_tab(index)

    def _on_recent_session_menu(self, event: object) -> None:
        menu_id = event.GetId()
        if menu_id == int(self._id_clear_recent_sessions):
            clear_recent_sessions()
            self._recent_sessions = []
            self._refresh_sessions_menu()
            self._set_status("Cleared recent sessions")
            return
        path = self._recent_session_menu_ids.get(menu_id)
        if path is None:
            event.Skip()
            return
        self.open_session(path)

    def _clear_document_tabs(self) -> None:
        for index in range(len(self._document_tabs) - 1, -1, -1):
            self.notebook.DeletePage(index)
        self._document_tabs.clear()
        self._active_tab_index = -1

    def _open_documents_from_session(
        self,
        documents: list[Document],
        active_index: int,
        caret_positions: list[int] | None = None,
    ) -> None:
        self._clear_document_tabs()
        for document in documents:
            self._create_document_tab(document, select=False)
        if not self._document_tabs:
            self._create_document_tab(Document(), select=True)
            self._location_ring = LocationRing()
            self._location_ring.record(0)
            self._refresh_sessions_menu()
            return
        # §8.4: restore per-tab caret positions saved with the session.
        if caret_positions:
            for idx, tab in enumerate(self._document_tabs):
                pos = caret_positions[idx] if idx < len(caret_positions) else 0
                if pos > 0 and tab.editor is not None:
                    try:
                        tab.editor.SetInsertionPoint(pos)
                    except Exception:  # noqa: BLE001
                        pass
        active_index = max(0, min(active_index, len(self._document_tabs) - 1))
        self._select_tab(active_index)
        self._location_ring = LocationRing()
        self._location_ring.record(0)
        self._refresh_title()
        self._refresh_sessions_menu()
        # Quillin document.loaded_from_session event (one per restored document).
        fire = getattr(self, "_fire_quillin_event", None)
        if callable(fire):
            for tab in self._document_tabs:
                doc_path = getattr(tab.document, "path", None)
                fire(
                    "document.loaded_from_session",
                    {
                        "file_path": str(doc_path) if doc_path is not None else "",
                        "extension": doc_path.suffix.lower() if doc_path is not None else "",
                        "title": getattr(tab.document, "name", ""),
                    },
                )

    def save_session(self, path: Path | None = None) -> None:
        wx = self._wx
        default_name = (
            f"{self.document.name}.quill-session.json"
            if self.document.name
            else "quill-session.json"
        )
        target = path
        if target is None:
            wildcard = (
                "Quill session files (*.quill-session.json)|*.quill-session.json|"
                "JSON files (*.json)|*.json|All files (*.*)|*.*"
            )
            with wx.FileDialog(
                self.frame,
                "Save session",
                wildcard=wildcard,
                defaultFile=default_name,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as dialog:
                if self._show_modal_dialog(dialog, "Save Session") != wx.ID_OK:
                    self._set_status("Save session cancelled")
                    return
                target = Path(dialog.GetPath())
        if target is None:
            return
        session_title_text = target.name
        for suffix in (".quill-session.json", ".json"):
            if session_title_text.endswith(suffix):
                session_title_text = session_title_text[: -len(suffix)]
                break
        session_title_text = session_title_text.strip() or "Quill Session"
        # §8.4: collect per-tab caret positions to restore on next session open.
        caret_positions: list[int] = []
        for tab in self._document_tabs:
            try:
                pos = tab.editor.GetInsertionPoint() if tab.editor is not None else 0
            except Exception:  # noqa: BLE001
                pos = 0
            caret_positions.append(pos)
        payload = build_session_payload(
            title=session_title_text,
            active_index=self._current_tab_index(),
            documents=[tab.document for tab in self._document_tabs],
            caret_positions=caret_positions,
        )
        save_session_file(target, payload)
        self._recent_sessions = load_recent_sessions()
        self._refresh_sessions_menu()
        self._set_status(f"Saved workspace snapshot to {target.name}")

    def open_session(self, path: Path | None = None) -> None:
        wx = self._wx
        target = path
        if target is None:
            wildcard = (
                "Quill session files (*.quill-session.json)|*.quill-session.json|"
                "JSON files (*.json)|*.json|All files (*.*)|*.*"
            )
            with wx.FileDialog(
                self.frame,
                "Open session",
                wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dialog:
                if self._show_modal_dialog(dialog, "Open Session") != wx.ID_OK:
                    self._set_status("Open session cancelled")
                    return
                target = Path(dialog.GetPath())
        if target is None or not target.exists():
            self._set_status("Session file not found")
            return
        if not self._can_close_all_documents():
            self._set_status("Open session cancelled")
            return
        payload = load_session(target)
        documents = documents_from_session(payload)
        caret_positions = caret_positions_from_session(payload)
        active_index = active_index_from_session(payload, len(documents))
        self._open_documents_from_session(documents, active_index, caret_positions=caret_positions)
        self._recent_sessions = add_recent_session(target, self.settings.recent_files_limit)
        self._refresh_sessions_menu()
        self._set_status(f"Opened workspace snapshot {target.name}")
