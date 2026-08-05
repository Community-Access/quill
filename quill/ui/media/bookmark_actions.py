"""Bookmark send-to-document and sync actions for the media player.

Kept out of the player frame so it stays under budget. "Send to document" from a
separate app is a **copy to clipboard** of a paste-ready line (the user pastes it
into their QUILL document or a Sticky Note); plus a **Markdown export** of a
book's bookmarks. The **sync bundle** export/import is the device-independent half
of QuilleSync (the server push/pull is separate).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import wx

from quill.core.media.bookmarks import (
    BookmarkStore,
    MediaBookmark,
    bookmarks_to_markdown,
    format_bookmark_line,
)


def copy_bookmark_to_clipboard(host: Any, mark: MediaBookmark, book_title: str) -> None:
    """Copy a paste-ready bookmark line to the clipboard (send-to-document)."""
    line = format_bookmark_line(mark.position_ms, note=mark.note or mark.label, title=book_title)
    if wx.TheClipboard.Open():
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(line))
        finally:
            wx.TheClipboard.Close()
        host._announce("Bookmark copied to the clipboard.")
    else:
        host._announce("Could not access the clipboard.")


def export_bookmarks_markdown(host: Any, book_title: str, marks: list[MediaBookmark]) -> None:
    """Write a book's bookmarks to a Markdown file the user chooses."""
    path = _save_path(host, "Export bookmarks", "Markdown (*.md)|*.md")
    if path is None:
        return
    try:
        Path(path).write_text(bookmarks_to_markdown(book_title, marks), encoding="utf-8")
        host._announce(f"Exported {len(marks)} bookmark(s).")
    except OSError as error:
        host._show_message_box(f"Could not export bookmarks.\n\n{error}", "Export Bookmarks")


def export_sync_bundle(host: Any, store: BookmarkStore) -> None:
    """Write all bookmarks to a portable sync bundle (QuilleSync local half)."""
    path = _save_path(host, "Export sync bundle", "Sync bundle (*.json)|*.json")
    if path is None:
        return
    try:
        Path(path).write_text(json.dumps(store.export_bundle(), indent=2), encoding="utf-8")
        host._announce("Bookmark sync bundle exported.")
    except OSError as error:
        host._show_message_box(f"Could not export the bundle.\n\n{error}", "Export Sync Bundle")


def import_sync_bundle(host: Any, store: BookmarkStore, on_done: Any) -> None:
    """Merge bookmarks from a sync bundle the user chooses; refresh via ``on_done``."""
    with wx.FileDialog(
        host.frame,
        "Import sync bundle",
        wildcard="Sync bundle (*.json)|*.json|All files (*.*)|*.*",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as picker:
        if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return
        path = picker.GetPath()
    try:
        bundle = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        host._show_message_box(f"Could not read the bundle.\n\n{error}", "Import Sync Bundle")
        return
    added = store.merge_bundle(bundle if isinstance(bundle, dict) else {})
    host._announce(f"Imported {added} new bookmark(s).")
    on_done()


def _save_path(host: Any, title: str, wildcard: str) -> str | None:
    with wx.FileDialog(
        host.frame, title, wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
    ) as picker:
        if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return None
        return picker.GetPath()


__all__ = [
    "copy_bookmark_to_clipboard",
    "export_bookmarks_markdown",
    "export_sync_bundle",
    "import_sync_bundle",
]
