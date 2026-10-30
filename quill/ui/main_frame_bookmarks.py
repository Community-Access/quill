"""Named bookmarks, code folding and favorite folders on QUILL's main window.

Moved whole out of ``MainFrame`` (todo D.4, 2026-10-17): named, temporary and
quick bookmarks with their edit-surviving anchors and per-document memory,
accessible code folding (fold state is spoken metadata, never hidden text), and
the Favorite Folders list with its type-to-filter file finder. The host
contract is unchanged: these methods use the same ``self`` attributes they did,
and every command id, key, menu row and announcement is the same.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.bookmark_anchor import capture_anchor, resolve_anchor
from quill.core.bookmarks import (
    DocumentMemory,
    bookmark_names,
    bookmark_position,
    quick_slot_name,
    set_bookmark,
)
from quill.core.code_folding import (
    FoldableRegion,
    extract_foldable_regions,
    next_region_boundary,
    previous_region_boundary,
    region_line_count,
    smallest_region_containing,
)
from quill.core.favorite_folders import (
    FavoriteFile,
    FavoriteFolders,
    filter_favorite_files,
    list_files_in_favorites,
)
from quill.core.marks import line_column_for_position
from quill.core.pdf_open import outline_bookmark_offsets
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.navigator_node import _NavigatorNode
from quill.ui.sound_manager import post_sound


class BookmarksFoldsMixin:
    """Bookmarks, folds and favorite folders; mixed into ``MainFrame``."""

    def _capture_bookmark_anchor(self, name: str, position: int) -> None:
        """Record an edit-surviving anchor for a bookmark, alongside its offset."""
        try:
            text = self.editor.GetValue()
        except Exception:  # noqa: BLE001 - anchoring is best-effort
            return
        anchors = getattr(self, "_bookmark_anchors", None)
        if anchors is None:
            anchors = {}
            self._bookmark_anchors = anchors
        anchors[name] = capture_anchor(text, position)

    def _import_pdf_outline_bookmarks(self, loaded: object, suffix: str) -> None:
        """Import a PDF's embedded outline (Adobe bookmarks) into the document's
        bookmark store on first open, so they show up in List Bookmarks
        (Alt+Shift+B) — QUILL already imports Word/EPUB structure; this closes the
        PDF gap.

        Each outline entry is resolved to its title on its page (else the page's
        start) via the form-feed page markers the PDF extractor writes, by the
        helper QUILL Lite's Go To shares (quill.core.pdf_open). Idempotent:
        it skips when the document already has bookmarks (a re-open, or a user who
        curated them), so it never duplicates entries or resurrects deleted ones,
        and it never blocks the open — an unresolvable entry is simply skipped."""
        if suffix != ".pdf":
            return
        metadata = getattr(loaded, "source_metadata", None)
        if not isinstance(metadata, dict):
            return
        outline = metadata.get("pdf_outline")
        if not outline:
            return
        tab = self._active_tab()
        if tab is None or getattr(tab, "document", None) is not loaded:
            return
        if getattr(tab, "bookmarks", None):
            return  # already has bookmarks — don't duplicate or fight curation

        text = getattr(loaded, "text", "") or ""
        bookmarks = outline_bookmark_offsets(text, outline)
        anchors = {name: capture_anchor(text, offset) for name, offset in bookmarks.items()}
        if not bookmarks:
            return
        self._bookmarks = bookmarks
        self._bookmark_anchors = anchors
        self._save_active_bookmarks()
        count = len(bookmarks)
        self._set_status(
            f"Imported {count} bookmark{'s' if count != 1 else ''} from the PDF outline "
            f"(open List Bookmarks with Alt+Shift+B)"
        )

    def _resolve_bookmark_target(self, name: str) -> int | None:
        """Best current offset for a bookmark: re-anchored if we have context,
        else the stored offset. Relocates the mark to where its text actually
        lives now instead of drifting after edits (#Points)."""
        stored = bookmark_position(self._bookmarks, name)
        anchor = getattr(self, "_bookmark_anchors", {}).get(name)
        if anchor is None:
            return stored
        try:
            text = self.editor.GetValue()
        except Exception:  # noqa: BLE001
            return stored
        resolved = resolve_anchor(text, anchor)
        # Keep the int map in step so a later save/list reflects the new spot --
        # and PERSIST it. The write-back was in memory only, so the tab and the
        # file on disk kept the pre-edit offset until the next Set Bookmark, and
        # a bookmark that had re-anchored correctly all session came back in the
        # wrong place after a restart (bad.md L7).
        if stored != resolved:
            self._bookmarks = set_bookmark(self._bookmarks, name, resolved)
            self._capture_bookmark_anchor(name, resolved)
            self._save_active_bookmarks()
        return resolved

    def set_bookmark(self) -> None:
        wx = self._wx
        default_name = f"Bookmark {len(self._bookmarks) + 1}"
        with wx.TextEntryDialog(
            self.frame,
            "Enter bookmark name (named jump point):",
            "Set Bookmark",
            value=default_name,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Set Bookmark") != wx.ID_OK:
                return
            name = dialog.GetValue().strip()
        if not name:
            self._set_status("Set bookmark cancelled")
            return
        position = self.editor.GetInsertionPoint()
        self._bookmarks = set_bookmark(self._bookmarks, name, position)
        self._capture_bookmark_anchor(name, position)
        self._save_active_bookmarks()
        self._set_status(f'Set bookmark "{name}"')

    def go_to_bookmark(self) -> None:
        wx = self._wx
        names = bookmark_names(self._bookmarks)
        if not names:
            self._set_status("No bookmarks available. Bookmarks are named jump points.")
            return
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose bookmark (named jump point):",
            "Go To Bookmark",
            choices=names,
        ) as dialog:
            # Guarantee a valid selection so OK always resolves to a bookmark,
            # and wire the standard affirmative/escape ids so the dialog is
            # reliably dismissible by keyboard.
            if hasattr(dialog, "SetSelection"):
                dialog.SetSelection(0)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, "Go To Bookmark") != wx.ID_OK:
                return
            name = dialog.GetStringSelection()
        target = self._resolve_bookmark_target(name)
        if target is None:
            self._set_status("Bookmark was not found")
            return
        self._move_point(target)
        self.editor.SetFocus()
        self._set_status(f'Jumped to bookmark "{name}"')

    def list_bookmarks(self) -> None:
        names = bookmark_names(self._bookmarks)
        if not names:
            self._set_status("No bookmarks available. Bookmarks are named jump points.")
            return
        text = self.editor.GetValue()
        nodes: list[_NavigatorNode] = []
        for name in names:
            # Where the bookmark IS, not where it was stored. The list printed
            # the raw stored offset while jumping re-anchored by snippet, so
            # every row after an edit named a line the jump would not land on --
            # and a list of jump points whose numbers are wrong is worse than a
            # list with no numbers, because it is checkable and wrong (L7).
            position = self._resolve_bookmark_target(name)
            if position is None:
                continue
            line, column = line_column_for_position(text, position)
            nodes.append(
                _NavigatorNode(
                    label=f"{name} (Ln {line}, Col {column})",
                    preview=f"Bookmark: {name}\n\nLine {line}, Column {column}",
                    payload=name,
                    action_label="Jump to Bookmark",
                    children=[],
                )
            )
        selected = self._show_tree_navigator(
            title="List Bookmarks",
            root_label="Bookmarks (Named Jump Points)",
            nodes=nodes,
        )
        if not isinstance(selected, str):
            self._set_status("Bookmark list cancelled")
            return
        target = self._resolve_bookmark_target(selected)
        if target is None:
            self._set_status("Bookmark was not found")
            return
        self._move_point(target)
        self.editor.SetFocus()
        self._set_status(f'Jumped to bookmark "{selected}"')

    def set_temp_bookmark(self) -> None:
        """Set the single unnamed, one-shot jump point (temporary bookmark).

        Deliberately no dialog and no persistence -- this is disposable scratch
        state, overwritten silently on every re-set, and forgotten on restart.
        """
        position = self.editor.GetInsertionPoint()
        self._temp_bookmark = position
        self._active_tab().temp_bookmark = position
        self._set_status("Temporary bookmark set")

    def go_to_temp_bookmark(self) -> None:
        """Jump to the temp bookmark with no picker dialog."""
        if self._temp_bookmark is None:
            self._set_status("No temporary bookmark set")
            return
        self._move_point(self._temp_bookmark)
        self.editor.SetFocus()
        self._set_status("Jumped to temporary bookmark")

    def set_quick_bookmark(self, slot: int) -> None:
        """Set numbered quick-bookmark slot 0-9 (reuses the named-bookmark store)."""
        name = quick_slot_name(slot)
        position = self.editor.GetInsertionPoint()
        self._bookmarks = set_bookmark(self._bookmarks, name, position)
        self._capture_bookmark_anchor(name, position)
        self._save_active_bookmarks()
        post_sound(f"bookmark_slot_{slot}")
        self._set_status(f"Quick bookmark {slot} set")

    def go_to_quick_bookmark(self, slot: int) -> None:
        """Jump to numbered quick-bookmark slot 0-9 with no picker dialog."""
        name = quick_slot_name(slot)
        target = self._resolve_bookmark_target(name)
        if target is None:
            self._set_status(f"Quick bookmark {slot} is not set")
            return
        self._move_point(target)
        self.editor.SetFocus()
        post_sound(f"bookmark_slot_{slot}")
        self._set_status(f"Jumped to quick bookmark {slot}")

    # -- accessible code folding (x.md PRD) ---------------------------------- #
    # Fold state is spoken metadata, never visual line-hiding: the document
    # text is never mutated, and raw arrow/word/line navigation is never
    # intercepted. Only structural jump commands (here) are fold-aware, so a
    # screen reader user arrowing through a folded region reads it exactly as
    # if it weren't folded -- nothing reachable is ever silently skipped.

    def _current_foldable_regions(self) -> list[FoldableRegion]:
        markup_kind = self._effective_markup_kind()
        return extract_foldable_regions(self.editor.GetValue(), markup_kind)

    def toggle_fold(self) -> None:
        """Fold or unfold the smallest foldable region containing the caret."""
        regions = self._current_foldable_regions()
        caret = self.editor.GetInsertionPoint()
        region = smallest_region_containing(regions, caret)
        if region is None:
            self._set_status("No foldable region at the cursor")
            return
        key = (region.start, region.end)
        text = self.editor.GetValue()
        lines = region_line_count(text, region)
        if key in self._folded_regions:
            self._folded_regions.discard(key)
            self._set_status(f'Unfolded: "{region.label}"')
        else:
            self._folded_regions.add(key)
            self._set_status(f'Folded: {lines} lines under "{region.label}"')

    def next_fold(self) -> None:
        """Jump to the next foldable region boundary, announcing fold state."""
        regions = self._current_foldable_regions()
        if not regions:
            self._set_status("No foldable regions in this document")
            return
        caret = self.editor.GetInsertionPoint()
        region = next_region_boundary(regions, caret)
        if region is None:
            self._set_status("No more foldable regions ahead")
            return
        self._jump_to_fold(region)

    def previous_fold(self) -> None:
        """Jump to the previous foldable region boundary, announcing fold state."""
        regions = self._current_foldable_regions()
        if not regions:
            self._set_status("No foldable regions in this document")
            return
        caret = self.editor.GetInsertionPoint()
        region = previous_region_boundary(regions, caret)
        if region is None:
            self._set_status("No more foldable regions behind")
            return
        self._jump_to_fold(region)

    def _jump_to_fold(self, region: FoldableRegion) -> None:
        self._record_location_before_jump()
        self.editor.SetInsertionPoint(region.start)
        self.editor.SetFocus()
        text = self.editor.GetValue()
        lines = region_line_count(text, region)
        state = "folded" if (region.start, region.end) in self._folded_regions else "expanded"
        self._set_status(f'"{region.label}", {state}, {lines} lines')

    def list_folds(self) -> None:
        """Show every foldable region with its fold state; jump or toggle from here.

        The accessible equivalent of a sighted user scanning the gutter fold
        triangles: a spoken table of contents with fold state, reachable
        without ever having to encounter a region by scrolling past it.
        """
        regions = self._current_foldable_regions()
        if not regions:
            self._set_status("No foldable regions in this document")
            return
        text = self.editor.GetValue()
        nodes: list[_NavigatorNode] = []
        for region in regions:
            key = (region.start, region.end)
            state = "Folded" if key in self._folded_regions else "Expanded"
            lines = region_line_count(text, region)
            nodes.append(
                _NavigatorNode(
                    label=f"{region.label} ({state}, {lines} lines)",
                    preview=f"{region.label}\n\n{state}, {lines} lines",
                    payload=key,
                    action_label="Jump to Region",
                    children=[],
                )
            )
        selected = self._show_tree_navigator(
            title="List Folds",
            root_label="Foldable Regions",
            nodes=nodes,
        )
        if not isinstance(selected, tuple):
            self._set_status("Fold list cancelled")
            return
        region = next((r for r in regions if (r.start, r.end) == selected), None)
        if region is None:
            self._set_status("Region was not found")
            return
        self._jump_to_fold(region)

    # -- favorite folders (community feature request) ------------------------ #
    def _favorite_folders(self) -> FavoriteFolders:
        if getattr(self, "_favorite_folders_cache", None) is None:
            self._favorite_folders_cache = FavoriteFolders.load()
        return self._favorite_folders_cache

    def add_favorite_folder(self) -> None:
        """Add the current document's folder to Favorite Folders.

        Kurzweil-1000-style favorites: a short, deliberately curated list for
        instant access, distinct from Windows' recency-based recent-folders --
        a folder used constantly but not touched in months still belongs here.
        """
        doc_path = getattr(self.document, "path", None)
        if not doc_path:
            self._set_status("Save this document first, or use a specific folder")
            return
        folder = str(Path(doc_path).resolve().parent)
        added = self._favorite_folders().add(folder)
        if added:
            self._set_status(f"Added to Favorite Folders: {Path(folder).name}")
        else:
            self._set_status(f"{Path(folder).name} is already a favorite folder")

    def remove_favorite_folder(self) -> None:
        """Pick a favorite folder to remove from the list."""
        wx = self._wx
        vault = self._favorite_folders()
        names = vault.names()
        if not names:
            self._set_status("No favorite folders yet. Use Add Favorite Folder first.")
            return
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose a favorite folder to remove:",
            "Remove Favorite Folder",
            choices=names,
        ) as dialog:
            if hasattr(dialog, "SetSelection"):
                dialog.SetSelection(0)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, "Remove Favorite Folder") != wx.ID_OK:
                self._set_status("Remove favorite folder cancelled")
                return
            index = dialog.GetSelection()
        folder = vault.folders[index]
        vault.remove(folder)
        self._set_status(f"Removed favorite folder: {names[index]}")

    def open_from_favorite_folder(self) -> None:
        """VSCode-Quick-Open-style file finder, scoped to favorite folders.

        Quill has no single-project-root "workspace" the way VSCode does, so
        this scans favorite folders (top-level only by default -- see
        list_files_in_favorites) instead of an entire tree. Type to filter by
        filename, arrow to a match, Enter/OK to open it -- the same
        one-keystroke-per-step rhythm as VSCode's Ctrl+P, just bounded to the
        short, deliberately curated favorites list rather than everything on
        disk. An opt-in "Include subfolders" checkbox switches to a recursive
        scan (capped, so a huge favorite still can't hang the dialog) for
        anyone who wants it.
        """
        wx = self._wx
        vault = self._favorite_folders()
        if not vault.folders:
            self._set_status("No favorite folders yet. Use Add Favorite Folder first.")
            return

        dialog = wx.Dialog(
            self.frame, title="Open From Favorite Folder", size=dip_size(self.frame, 560, 440)
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(dialog, label="Type to filter, then choose a file to open:"),
            0,
            wx.ALL,
            8,
        )
        search = wx.TextCtrl(dialog)
        search.SetName("Filter")
        root.Add(search, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        recursive_check = wx.CheckBox(dialog, label="Include subfolders")
        recursive_check.SetName("Include subfolders")
        root.Add(recursive_check, 0, wx.ALL, 8)
        results = wx.ListBox(dialog)
        results.SetName("Matching files")
        root.Add(results, 1, wx.ALL | wx.EXPAND, 8)
        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        dialog.SetSizer(root)

        all_files: list[FavoriteFile] = list_files_in_favorites(vault)
        current_matches: list[FavoriteFile] = list(all_files)

        def refresh(query: str) -> None:
            nonlocal current_matches
            current_matches = filter_favorite_files(all_files, query)
            results.Set([f"{item.path.name}  —  {item.folder_label}" for item in current_matches])
            if current_matches:
                results.SetSelection(0)

        def rescan() -> None:
            nonlocal all_files
            all_files = list_files_in_favorites(vault, recursive=recursive_check.GetValue())
            refresh(search.GetValue())

        refresh("")
        search.Bind(wx.EVT_TEXT, lambda _e: refresh(search.GetValue()))
        recursive_check.Bind(wx.EVT_CHECKBOX, lambda _e: rescan())
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        search.SetFocus()
        result = self._show_modal_dialog(dialog, "Open From Favorite Folder")
        selection = results.GetSelection()
        dialog.Destroy()
        if result != wx.ID_OK or selection == wx.NOT_FOUND:
            self._set_status("Open from favorite folder cancelled")
            return
        if not current_matches:
            self._set_status("No files found in your favorite folders.")
            return
        self.open_file(path=current_matches[selection].path)

    # -- persistent per-document bookmarks + last position ------------------ #
    def _save_active_bookmarks(self) -> None:
        """Write the active document's bookmarks back to its tab and (if the
        document is saved to disk) persist them per-document so they survive a
        restart. Untitled documents stay in memory for the session only."""
        tab = self._active_tab()
        if tab is not None:
            tab.bookmarks = dict(self._bookmarks)
            tab.bookmark_anchors = dict(self._bookmark_anchors)
        key = DocumentMemory.key_for(getattr(getattr(self, "document", None), "path", None))
        if key:
            try:
                self._doc_memory.set_bookmarks(key, self._bookmarks)
                self._doc_memory.set_anchors(key, self._bookmark_anchors)
            except Exception:  # noqa: BLE001 - persistence is best-effort
                pass

    def _remember_active_caret(self) -> None:
        """Persist the active document's current caret offset as its last position."""
        key = DocumentMemory.key_for(getattr(getattr(self, "document", None), "path", None))
        editor = getattr(self, "editor", None)
        if not key or editor is None:
            return
        try:
            self._doc_memory.set_last_position(key, editor.GetInsertionPoint())
        except Exception:  # noqa: BLE001
            pass

    def _restore_document_memory(self, tab: object) -> None:
        """On open, load a saved document's bookmarks into its tab and move the
        caret to where it last was. No-op for untitled documents."""
        key = DocumentMemory.key_for(getattr(tab.document, "path", None))
        if not key:
            return
        try:
            tab.bookmarks = self._doc_memory.bookmarks_for(key)
            tab.bookmark_anchors = self._doc_memory.anchors_for(key)
            self._adopt_numbered_bookmarks(tab, self._doc_memory.numbered_for(key))
            last = self._doc_memory.last_position(key)
        except Exception:  # noqa: BLE001
            return
        if last is None:
            return
        editor = tab.editor
        try:
            clamped = max(0, min(int(last), editor.GetLastPosition()))
            editor.SetInsertionPoint(clamped)
            show = getattr(editor, "ShowPosition", None)
            if callable(show):
                show(clamped)
        except Exception:  # noqa: BLE001
            pass
