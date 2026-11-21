"""My Scribe Documents: every document in the person's Scribe account (PRD 7.5).

A modal dialog with Refresh, not a live list. "Show: Documents / Trash" sits
above the list; when there is nothing to list, a focusable line says so.
Commands: Download Formats... (the convert dialog, nothing uploaded), Open in
<app> (a file already downloaded), Rename..., Move to Trash, and in the Trash
view Recover and Delete Forever..., Ask for Human Review..., Copy Details.

After Move to Trash, Recover or Delete Forever focus moves to the next row
(the previous one if it was the last; the "No documents" line if the list is
empty) and one sentence is said -- the person caused it, so it is said.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.scribe.errors import ScribeError
from quill.core.scribe.model import DocumentSummary, formats_phrase
from quill.ui.dialog_contract import bind_close_button, show_modal_dialog

EMPTY = {
    0: "No documents in your Scribe account.",
    1: "Nothing in your Scribe trash.",
}


def short_date(stamp: str) -> str:
    return stamp[:10] if stamp else ""


class ScribeDocumentsDialog(wx.Dialog):
    def __init__(self, parent: Any, controller: Any) -> None:
        super().__init__(
            parent, title="My Scribe Documents", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._controller = controller
        self._documents: list[DocumentSummary] = []
        app = controller.app_name

        sizer = wx.BoxSizer(wx.VERTICAL)
        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(wx.StaticText(self, label="&Show:"), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 6)
        self.show = wx.Choice(self, choices=["Documents", "Trash"])
        self.show.SetSelection(0)
        self.show.SetHelpText("Documents in your account, or the trash (deleted after 7 days).")
        top.Add(self.show, 0, wx.ALL, 6)
        top.Add(wx.StaticText(self, label="Pages:"), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 6)
        self.pages = wx.TextCtrl(self, style=wx.TE_READONLY, value="Loading...")
        self.pages.SetName("Pages")
        self.pages.SetHelpText(
            "How many Scribe pages are left; for an organization, whose shared credits they are."
        )
        top.Add(self.pages, 1, wx.ALL, 6)
        self.buy = wx.Button(self, label="&Buy Pages")
        self.buy.SetHelpText(
            f"Opens Scribe's purchase page in your browser. {app} never takes payment."
        )
        top.Add(self.buy, 0, wx.ALL, 6)
        sizer.Add(top, 0, wx.EXPAND)

        sizer.Add(wx.StaticText(self, label="&Documents:"), 0, wx.LEFT, 6)
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.SetHelpText(
            "Your Scribe documents, including those made on the web or iPhone. Enter downloads "
            "formats; the Applications key lists every command."
        )
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 6)
        sizer.Add(wx.StaticText(self, label="Status:"), 0, wx.LEFT, 6)
        self.empty = wx.TextCtrl(self, style=wx.TE_READONLY, value="Loading your documents...")
        self.empty.SetHelpText("Shown when there is nothing to list.")
        sizer.Add(self.empty, 0, wx.EXPAND | wx.ALL, 6)

        row = wx.WrapSizer(wx.HORIZONTAL)
        self.commands: dict[str, Any] = {}
        for key, label, help_text in (
            (
                "download",
                "Do&wnload Formats...",
                "Chooses formats to make or download, the convert dialog without an upload.",
            ),
            (
                "open",
                f"Open in &{app}",
                f"Opens a file already downloaded from this document in {app}.",
            ),
            ("rename", "Re&name...", "Changes the document's title in your Scribe account."),
            ("trash", "Move to &Trash", "Moves it to the trash; it is deleted after 7 days."),
            ("recover", "&Recover", "Takes it out of the trash."),
            ("delete", "Delete &Forever...", "Deletes it now. This cannot be undone."),
            ("review", "Ask for &Human Review...", "Scribe's paid remediation, with a comment."),
            ("copy", "&Copy Details", "Copies the document's details to the clipboard."),
            ("refresh", "R&efresh", "Reads the list from Scribe again."),
        ):
            button = wx.Button(self, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, k=key: self.run(k))
            row.Add(button, 0, wx.ALL, 4)
            self.commands[key] = button
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Closes My Scribe Documents.")
        row.Add(close, 0, wx.ALL, 4)
        sizer.Add(row, 0, wx.EXPAND)
        self.SetSizer(sizer)
        self.SetSize(self.FromDIP(wx.Size(760, 520)))

        bind_close_button(self, close, modeless=False)
        self.show.Bind(wx.EVT_CHOICE, lambda _e: self.load())
        self.buy.Bind(wx.EVT_BUTTON, lambda _e: controller.buy_pages())
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self.run("download"))
        self.list.Bind(wx.EVT_CONTEXT_MENU, self._context_menu)
        self.list.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self._columns()
        self.load()
        self.show.SetFocus()

    @property
    def trash_view(self) -> bool:
        return self.show.GetSelection() == 1

    def _columns(self) -> None:
        self.list.ClearAll()
        names = (
            (("Title", 260), ("Trashed", 120), ("Deleted forever on", 160))
            if self.trash_view
            else (("Title", 260), ("Pages", 70), ("Date", 110), ("Formats ready", 260))
        )
        for index, (name, width) in enumerate(names):
            self.list.InsertColumn(index, name, width=self.FromDIP(width))
        for key in ("trash", "download", "open", "rename"):
            self.commands[key].Show(not self.trash_view)
        for key in ("recover", "delete"):
            self.commands[key].Show(self.trash_view)
        self.Layout()

    # ---------------------------------------------------------------- data

    def load(self, keep_id: str = "") -> None:
        trash = self.trash_view
        self._columns()

        def work() -> tuple[list[DocumentSummary], str]:
            client = self._controller.client()
            # account(): pages left, and the organization whose credits they are (3.4)
            documents = client.list_trash() if trash else client.list_documents()[0]
            return documents, client.account().pages_phrase()

        def done(result: tuple[list[DocumentSummary], str]) -> None:
            if not self:
                return
            documents, pages = result
            self.pages.SetValue(pages)
            self._fill(documents, keep_id)

        def failed(error: BaseException) -> None:
            if not self:
                return
            message = error.message if isinstance(error, ScribeError) else str(error)
            self.empty.SetValue(f"Your documents could not be loaded: {message}")
            self._fill([], "")
            self._controller.host.scribe_announce(self.empty.GetValue())

        self._controller._background(work, done, failed)

    def _fill(self, documents: list[DocumentSummary], keep_id: str) -> None:
        self._documents = documents
        self.list.DeleteAllItems()
        for doc in documents:
            if self.trash_view:
                row = self.list.InsertItem(self.list.GetItemCount(), doc.display_title)
                self.list.SetItem(row, 1, short_date(doc.trashed_at))
                self.list.SetItem(row, 2, short_date(doc.permanently_delete_at))
            else:
                row = self.list.InsertItem(self.list.GetItemCount(), doc.display_title)
                self.list.SetItem(row, 1, "" if doc.page_count is None else str(doc.page_count))
                self.list.SetItem(row, 2, short_date(doc.inserted_at))
                ready = formats_phrase(doc.ready_formats) if doc.ready_formats else "none yet"
                if doc.is_password_needed:
                    ready = "needs its password"
                self.list.SetItem(row, 3, ready)
        has = bool(documents)
        if not has and not self.empty.GetValue().startswith("Your documents could not"):
            self.empty.SetValue(EMPTY[1 if self.trash_view else 0])
        focused_list = wx.Window.FindFocus() is self.list
        self.empty.Show(not has)
        self.list.Show(has)
        self.Layout()
        moved = getattr(self, "_focus_list_after_load", False)
        self._focus_list_after_load = False
        if has:
            ids = [d.id for d in documents]
            index = ids.index(keep_id) if keep_id in ids else 0
            self.list.Focus(index)
            self.list.Select(index)
            if moved:
                self.list.SetFocus()
        elif focused_list or moved:
            self.empty.SetFocus()

    def selected(self) -> DocumentSummary | None:
        index = self.list.GetFocusedItem()
        return self._documents[index] if 0 <= index < len(self._documents) else None

    # ------------------------------------------------------------ commands

    def _on_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.run("delete" if self.trash_view else "trash")
            return
        event.Skip()

    def _context_menu(self, _event: Any) -> None:
        menu = wx.Menu()
        for key, button in self.commands.items():
            if button.IsShown():
                item = menu.Append(wx.ID_ANY, button.GetLabel())
                self.Bind(wx.EVT_MENU, lambda _e, k=key: self.run(k), item)
        self.PopupMenu(menu)
        menu.Destroy()

    def run(self, key: str) -> None:
        if key == "refresh":
            doc = self.selected()
            self.load(doc.id if doc else "")
            return
        doc = self.selected()
        if doc is None:
            self._controller.host.scribe_announce("Choose a document first.")
            return
        if key == "download":
            self._controller.convert_existing(doc)
        elif key == "open":
            self._open(doc)
        elif key == "rename":
            self._rename(doc)
        elif key == "trash":
            self._act(doc, lambda c: c.trash(doc.id), f"{doc.display_title} moved to Trash.")
        elif key == "recover":
            self._act(doc, lambda c: c.recover(doc.id), f"{doc.display_title} recovered.")
        elif key == "delete":
            self._delete(doc)
        elif key == "review":
            self._controller.ask_for_review(doc.id, doc.display_title)
        elif key == "copy":
            text = (
                f"{doc.display_title}\nScribe document ID: {doc.id}\nPages: {doc.page_count}\n"
                f"Created: {doc.inserted_at}\nFormats ready: {formats_phrase(doc.ready_formats)}"
            )
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(text))
                finally:
                    wx.TheClipboard.Close()
                self._controller.host.scribe_announce("Details copied.")

    def _neighbour(self, doc: DocumentSummary) -> str:
        ids = [d.id for d in self._documents]
        index = ids.index(doc.id)
        if index + 1 < len(ids):
            return ids[index + 1]
        return ids[index - 1] if index > 0 else ""

    def _act(self, doc: DocumentSummary, call: Any, sentence: str) -> None:
        keep = self._neighbour(doc)

        def done(_result: Any) -> None:
            self._focus_list_after_load = True
            self.load(keep)
            wx.CallLater(300, self._controller.host.scribe_announce, sentence)

        self._controller._background(lambda: call(self._controller.client()), done)

    def _delete(self, doc: DocumentSummary) -> None:
        when = short_date(doc.permanently_delete_at)
        dialog = wx.MessageDialog(
            self,
            f"Delete {doc.display_title} forever? This cannot be undone. Scribe would delete it "
            f"on its own on {when or 'its deletion date'}.",
            "Delete Forever",
            wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING,
        )
        dialog.SetOKCancelLabels("Delete Forever", "Cancel")
        try:
            answer = show_modal_dialog(dialog, "Delete Forever")
        finally:
            dialog.Destroy()
        if answer == wx.ID_OK:
            self._act(
                doc, lambda c: c.delete_forever(doc.id), f"{doc.display_title} deleted forever."
            )

    def _rename(self, doc: DocumentSummary) -> None:
        dialog = wx.TextEntryDialog(self, "&New name:", "Rename", doc.display_title)
        wx.CallAfter(_select_all, dialog)
        try:
            if show_modal_dialog(dialog, "Rename") != wx.ID_OK:
                return
            title = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not title:
            self._controller.host.scribe_announce("A document needs a name. Nothing was changed.")
            return
        self._act(doc, lambda c: c.rename(doc.id, title), f"Renamed to {title}.")

    def _open(self, doc: DocumentSummary) -> None:
        from quill.core.scribe.library import Library

        files = Library().files_for(doc.id)
        if not files:
            self._controller.host.scribe_announce(
                f"Nothing from {doc.display_title} is downloaded yet. Use Download Formats."
            )
            return
        from quill.core.scribe.queue import Job

        format_id, path = files[-1]
        said = self._controller.host.scribe_open_result(
            Job(document_id=doc.id, title=doc.display_title, app=self._controller.app_name),
            format_id,
            path,
        )
        if said:
            self.EndModal(wx.ID_OK)
            wx.CallLater(300, self._controller.host.scribe_announce, f"{said}.")


def _select_all(dialog: Any) -> None:
    try:
        for child in dialog.GetChildren():
            if isinstance(child, wx.TextCtrl):
                child.SelectAll()
    except RuntimeError:
        pass


__all__ = ["ScribeDocumentsDialog", "short_date"]
