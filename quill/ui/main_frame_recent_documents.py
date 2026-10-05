"""Recent documents in QUILL: the Open Recent submenu and the Recent Documents window.

Extracted from ``main_frame.py`` when the window landed (2026-10-04), so the
whole feature reads in one place and in the same order as QUILL Lite's half
(``quill/apps/lite_window_recent.py``). The rules are
:mod:`quill.core.recent_documents` and the window is
:mod:`quill.ui.recent_documents_dialog`, both shared, so the two editors cannot
drift on a list they keep identically.

QUILL's list is ``recent.json`` and its pins are ``recent-pinned.json``, both in
QUILL's own data folder; QUILL Lite keeps its own. The two are never merged --
a recent list describes one install, which is why neither the bridge nor a
portable backup carries it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core import recent_documents as rd
from quill.core.recent import (
    add_recent_file,
    load_pinned_recent_files,
    save_pinned_recent_files,
    save_recent_files,
)

__all__ = ["RecentDocumentsMixin"]


class RecentDocumentsMixin:
    """File > Open Recent, File > Recent Documents..., and keeping the list."""

    frame: Any
    settings: Any
    recent_files: list[Path]

    def _pinned_recent(self) -> list[str]:
        if getattr(self, "_pinned_recent_cache", None) is None:
            safe = bool(getattr(self, "_safe_mode", False))
            self._pinned_recent_cache: list[str] | None = [] if safe else load_pinned_recent_files()
        return list(self._pinned_recent_cache or [])

    def _register_recent_documents_commands(self) -> None:
        self.commands.register(  # type: ignore[attr-defined]
            "file.recent_documents",
            "Recent Documents",
            self.open_recent_documents,
            self._binding_for("file.recent_documents"),  # type: ignore[attr-defined]
        )

    def _prepare_recent_documents_item(self) -> None:
        """Bind the Recent Documents row, which lives at the foot of Open Recent.

        In the submenu rather than on File itself because QUILL's File menu has
        no Alt letter or digit left: a 37th row there cost Exit its letter.
        The row is appended on every rebuild, beside Clear Recent Files.
        """
        import wx

        self._id_recent_documents = wx.NewIdRef()
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_recent_documents(), id=self._id_recent_documents
        )

    def _refresh_recent_menu(self) -> None:
        if not hasattr(self, "_recent_menu") or not hasattr(self, "_wx"):
            return
        if not self._menu_updates_allowed():  # type: ignore[attr-defined]
            self._request_menu_refresh()  # type: ignore[attr-defined]
            return
        while self._recent_menu.GetMenuItemCount() > 0:
            item = self._recent_menu.FindItemByPosition(0)
            if item is None:
                break
            self._recent_menu.DestroyItem(item)
        self._recent_menu_ids.clear()
        pinned = self._pinned_recent()
        shown = rd.menu_paths([str(p) for p in self.recent_files], pinned)
        if not shown:
            item = self._recent_menu.Append(self._wx.ID_ANY, "(No recent files)")
            item.Enable(False)
        for index, entry in enumerate(shown, start=1):
            menu_id = self._wx.NewIdRef()
            label = rd.menu_label(index, entry, pinned=rd.is_pinned(pinned, entry))
            self._recent_menu.Append(menu_id, label)
            self._recent_menu_ids[int(menu_id)] = Path(entry)
        self._recent_menu.AppendSeparator()
        if hasattr(self, "_id_recent_documents"):
            from quill.core.i18n import _

            label = self._menu_label(_("Recent &Documents..."), "file.recent_documents")  # type: ignore[attr-defined]
            self._recent_menu.Append(self._id_recent_documents, label)
        self._recent_menu.Append(self._id_clear_recent, "C&lear Recent Files...")
        # A rebuilt submenu has no routes: these rows are file paths, built here
        # rather than in the menu-bar build, so they never met the pass. Without
        # this they are the only rows in QUILL with no keyboard route at all --
        # which is exactly the silent gap the gate is meant to catch.
        self._reapply_menu_routes()  # type: ignore[attr-defined]

    def _on_open_recent(self, event: Any) -> None:
        menu_id = event.GetId()
        path = self._recent_menu_ids.get(menu_id)
        if menu_id == int(self._id_clear_recent):
            self.clear_recent_files()
            return
        if path is None:
            event.Skip()
            return
        self.open_file(path)  # type: ignore[attr-defined]

    def clear_recent_files(self) -> None:
        """Clear Recent Files: asks first (No is the default) and keeps pins."""
        from quill.ui.recent_documents_dialog import confirm_clear_recent

        pinned = self._pinned_recent()
        kept = rd.clear_unpinned([str(p) for p in self.recent_files], pinned)
        removed = len(rd.ordered([str(p) for p in self.recent_files], pinned)) - len(pinned)
        if removed <= 0:
            self._set_status("There is nothing to clear: every recent file is pinned.")  # type: ignore[attr-defined]
            return
        if not confirm_clear_recent(self.frame, removed, len(pinned)):
            return
        self.recent_files = [Path(entry) for entry in kept]
        save_recent_files(self.recent_files)
        self._refresh_recent_menu()
        self._set_status(rd.describe_cleared(removed, len(pinned)))  # type: ignore[attr-defined]

    def _record_recent(self, path: Path) -> None:
        self.recent_files = add_recent_file(path, self.settings.recent_files_limit)
        self._refresh_recent_menu()

    def open_recent_documents(self) -> None:
        """File > Recent Documents... (Alt+Shift+0): the list as a window."""
        from quill.core.settings import save_settings
        from quill.ui.recent_documents_dialog import show_recent_documents

        answer = show_recent_documents(
            self.frame,
            [str(p) for p in self.recent_files],
            self._pinned_recent(),
            limit=int(getattr(self.settings, "recent_files_limit", rd.DEFAULT_LIMIT)),
            auto_clear_missing=bool(
                getattr(self.settings, "recent_files_auto_clear_missing", False)
            ),
            announce=self._announce,  # type: ignore[attr-defined]
        )
        if answer.changed:
            self.recent_files = [Path(entry) for entry in answer.recent]
            save_recent_files(self.recent_files)
            self._pinned_recent_cache = list(answer.pinned)
            save_pinned_recent_files(list(answer.pinned))
        settings = self.settings
        prefs = (answer.limit, answer.auto_clear_missing)
        if prefs != (settings.recent_files_limit, settings.recent_files_auto_clear_missing):
            self.settings.recent_files_limit = answer.limit
            self.settings.recent_files_auto_clear_missing = answer.auto_clear_missing
            save_settings(self.settings)
        self._refresh_recent_menu()
        if answer.open_path:
            self.open_file(Path(answer.open_path))  # type: ignore[attr-defined]
