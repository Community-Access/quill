"""Bookmarks: one window over everything you marked (list.md 4.4, 4.5).

A bookmark is a position in a thing. QUILL had positions in books and notes on
podcast episodes, in two stores, with no window that showed both and nothing at
all for a station, a YouTube row or a recording -- which is most of what Quill
Radio plays.

This is the one list. Rows come from
:class:`~quill.core.media.bookmarks.BookmarkStore`, anchored by
:mod:`quill.core.bookmark_anchors`, so a bookmark dropped in Quill Radio is in
QUILL Cast's window with no sync and no protocol: both apps build the same
anchor for the same episode and read the same file in the shared data folder.

Four verbs, and the house shape:

* **Enter jumps.** Not a button first -- a list of places exists to be gone to,
  and every other list in the family answers Enter with its obvious verb.
* **Share** copies the place, the note and what it is in, together, because the
  note alone is a fragment nobody can act on.
* **Delete** takes what is selected, one row or twenty, and says how many.
* **Export** writes the lot as Markdown, for somebody keeping a listening log.

Jumping is the one verb this window cannot do on its own -- what "go there"
means belongs to whichever app can play the thing -- so the host registers a
handler per anchor kind. A row nothing claims has no Jump, and the button says
which state dimmed it rather than failing quietly.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core import bookmark_anchors, bookmark_ops
from quill.core.media.bookmarks import BookmarkStore, MediaBookmark, bookmarks_to_markdown
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

TITLE = "Bookmarks"

#: anchor kind -> handler(anchor, bookmark) -> spoken outcome. Registered by
#: each app for the kinds it can actually play. By kind rather than by stored
#: closure, for the same reason Recent Problems registers retries that way: a
#: row survives a restart, and a closure does not.
_JUMP_HANDLERS: dict[str, Callable[[str, MediaBookmark], str]] = {}


def register_jump(kind: str, handler: Callable[[str, MediaBookmark], str]) -> None:
    """Teach this app how to go to bookmarks of *kind*. Registering replaces."""
    _JUMP_HANDLERS[kind] = handler


def clear_jumps() -> None:
    """Forget every registered handler (tests, and app shutdown)."""
    _JUMP_HANDLERS.clear()


def can_jump(anchor: str) -> bool:
    return bookmark_anchors.kind_of(anchor) in _JUMP_HANDLERS


def jump(anchor: str, mark: MediaBookmark) -> str:
    """Run the registered handler; what to say either way."""
    handler = _JUMP_HANDLERS.get(bookmark_anchors.kind_of(anchor))
    if handler is None:
        return f"This app cannot open a {bookmark_anchors.label_for(anchor).lower()} from here."
    try:
        return (
            handler(anchor, mark) or f"Going to {bookmark_ops.spoken_position(mark.position_ms)}."
        )
    except Exception as error:  # noqa: BLE001 - a jump that fails must say so
        return f"Could not go there: {error}."


def show_bookmarks(host: Any, *, store: BookmarkStore | None = None) -> None:
    """Open the Bookmarks window. Modal, house pattern."""
    import wx

    store = store if store is not None else BookmarkStore()
    rows: list[tuple[str, MediaBookmark]] = store.all_bookmarks()

    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize(wx.Size(760, 460))
    root = wx.BoxSizer(wx.VERTICAL)

    summary_label = wx.StaticText(dialog, label=bookmark_ops.summarise(rows))
    root.Add(summary_label, 0, wx.ALL, 8)
    root.Add(wx.StaticText(dialog, label="&Everywhere you marked:"), 0, wx.LEFT | wx.RIGHT, 8)
    # Extended, so Delete works on twenty rows as readily as on one -- and
    # Enter still jumps to the first of them, which is the only sensible
    # reading of "go to these".
    listbox = wx.ListBox(dialog, style=wx.LB_EXTENDED)
    listbox.SetName(
        "Every bookmark, across podcasts, stations, videos, recordings and "
        "books. Enter goes to the highlighted one. Shift and arrow extend the "
        "selection; Delete takes everything selected."
    )
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    jump_btn = wx.Button(dialog, label="&Go There")
    jump_btn.SetHelpText(
        "Opens the highlighted bookmark's episode, station or recording and "
        "starts it at that moment. Available only for things this app can play."
    )
    share_btn = wx.Button(dialog, label="&Share")
    share_btn.SetHelpText(
        "Copies the place, the note and what it is in, as text somebody else "
        "can use. The note on its own is a fragment nobody can act on."
    )
    note_btn = wx.Button(dialog, label="Edit &Note...")
    note_btn.SetHelpText(
        "Adds or changes what this bookmark says. A bookmark with nothing "
        "written on it is still a bookmark -- the note is optional."
    )
    delete_btn = wx.Button(dialog, label="&Delete")
    delete_btn.SetHelpText(
        "Removes every selected bookmark. It deletes the marks only: no "
        "episode, download or recording is touched."
    )
    export_btn = wx.Button(dialog, label="E&xport...")
    export_btn.SetHelpText("Writes every bookmark to a Markdown file, for a listening log.")
    close_btn = wx.Button(dialog, wx.ID_CLOSE, label="Cl&ose")
    close_btn.SetHelpText("Closes Bookmarks. Nothing is removed.")
    for button in (jump_btn, share_btn, note_btn, delete_btn, export_btn, close_btn):
        buttons.Add(button, 0, wx.RIGHT, 6)
    root.Add(buttons, 0, wx.ALL, 8)
    apply_modal_ids(dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())
    dialog.SetSizer(root)

    def _selected_rows() -> list[tuple[str, MediaBookmark]]:
        return [rows[i] for i in sorted(listbox.GetSelections()) if 0 <= i < len(rows)]

    def _first() -> tuple[str, MediaBookmark] | None:
        chosen = _selected_rows()
        return chosen[0] if chosen else None

    def _select_only(index: int) -> None:
        # SetSelection *adds* on an extended list; without clearing first the
        # selection grows every refresh and the next Delete takes the lot.
        for selected in list(listbox.GetSelections()):
            listbox.Deselect(selected)
        if 0 <= index < listbox.GetCount():
            listbox.SetSelection(index)

    def _refresh(select: int = 0) -> None:
        rows[:] = store.all_bookmarks()
        listbox.Set([bookmark_ops.row_label(anchor, mark) for anchor, mark in rows])
        summary_label.SetLabel(bookmark_ops.summarise(rows))
        if rows:
            _select_only(min(max(0, select), len(rows) - 1))
        _sync()

    def _sync() -> None:
        current = _first()
        jump_btn.Enable(current is not None and can_jump(current[0]))
        if current is not None and not can_jump(current[0]):
            kind = bookmark_anchors.label_for(current[0]).lower()
            jump_btn.SetHelpText(f"This app cannot open a {kind} from here.")
        for button in (share_btn, note_btn, delete_btn):
            button.Enable(current is not None)
        export_btn.Enable(bool(rows))

    def _on_jump(_event: Any) -> None:
        current = _first()
        if current is None:
            host._announce("No bookmark is selected.")
            return
        anchor, mark = current
        if not can_jump(anchor):
            host._announce(f"Go There: {jump(anchor, mark)}")
            return
        host._announce(jump(anchor, mark))
        dialog.EndModal(wx.ID_CLOSE)

    def _on_share(_event: Any) -> None:
        current = _first()
        if current is None:
            host._announce("No bookmark is selected.")
            return
        text = bookmark_ops.share_text(*current)
        copier = getattr(host, "_copy_text", None)
        if callable(copier):
            copier(text)
        elif wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
        host._announce("Bookmark copied, with where it points.")

    def _on_note(_event: Any) -> None:
        current = _first()
        if current is None:
            host._announce("No bookmark is selected.")
            return
        anchor, mark = current
        with wx.TextEntryDialog(
            dialog,
            f"Note for {bookmark_ops.spoken_position(mark.position_ms)}:",
            "Edit Note",
            mark.note,
        ) as entry:
            if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            note = entry.GetValue().strip()
        store.add(anchor, mark.position_ms, label=mark.label, note=note, title=mark.title)
        index = listbox.GetSelections()[0] if listbox.GetSelections() else 0
        _refresh(index)
        host._announce("Note saved." if note else "Note cleared; the bookmark is still here.")

    def _on_delete(_event: Any) -> None:
        from quill.core.counted import Counted

        chosen = _selected_rows()
        if not chosen:
            host._announce("No bookmark is selected.")
            return
        index = min(sorted(listbox.GetSelections()) or [0])
        removed = sum(1 for anchor, mark in chosen if store.remove(anchor, mark.position_ms))
        _refresh(index)
        host._announce(
            Counted(done=removed, _eligible=len(chosen)).sentence("Removed", noun="bookmark")
        )

    def _on_export(_event: Any) -> None:
        if not rows:
            host._announce("There is nothing to export.")
            return
        with wx.FileDialog(
            dialog,
            message="Export bookmarks",
            defaultFile="bookmarks.md",
            wildcard="Markdown (*.md)|*.md|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as chooser:
            if chooser.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            destination = chooser.GetPath()
        try:
            _write_markdown(destination, rows)
        except OSError as error:
            host._announce(f"Could not export the bookmarks: {error}")
            return
        host._announce(f"Exported {len(rows)} bookmark(s).")

    jump_btn.Bind(wx.EVT_BUTTON, _on_jump)
    share_btn.Bind(wx.EVT_BUTTON, _on_share)
    note_btn.Bind(wx.EVT_BUTTON, _on_note)
    delete_btn.Bind(wx.EVT_BUTTON, _on_delete)
    export_btn.Bind(wx.EVT_BUTTON, _on_export)
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
    listbox.Bind(wx.EVT_LISTBOX, lambda _e: _sync())
    apply_listbox_activation(listbox, _on_jump)
    _refresh()
    wx.CallAfter(listbox.SetFocus)
    try:
        host._show_modal_dialog(dialog, TITLE)
    finally:
        dialog.Destroy()


def _write_markdown(path: str, rows: list[tuple[str, MediaBookmark]]) -> None:
    """One Markdown document, grouped by the thing each bookmark is in.

    Grouped rather than flat because a listening log is read by *what*, not by
    time -- and because ``bookmarks_to_markdown`` already renders one thing's
    marks, so this is the heading between them and nothing else.
    """
    from pathlib import Path

    grouped: dict[str, list[MediaBookmark]] = {}
    titles: dict[str, str] = {}
    for anchor, mark in rows:
        grouped.setdefault(anchor, []).append(mark)
        if mark.title.strip():
            titles[anchor] = mark.title.strip()
    chunks = ["# Bookmarks", ""]
    for anchor, marks in grouped.items():
        name = titles.get(anchor) or bookmark_anchors.body_of(anchor) or anchor
        chunks.append(
            bookmarks_to_markdown(f"{name} ({bookmark_anchors.label_for(anchor)})", marks)
        )
    Path(path).write_text("\n".join(chunks), encoding="utf-8")


__all__ = [
    "TITLE",
    "can_jump",
    "clear_jumps",
    "jump",
    "register_jump",
    "show_bookmarks",
]
