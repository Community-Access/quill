"""Podcasts > (selected episode) > View Show Notes... -- read an episode's
description either as a rich (but image-free) HTML view or as accessible
plain text with real paragraph line breaks, and optionally send it into a
new editor tab.

Two things it can do with the notes rather than just show them, both added
2026-08-18 for the same reason -- **show notes are mostly links**, and a
read-only text box turns a link into a string of characters to read out and
retype:

* **Save As** offers HTML and Markdown alongside plain text. Those two are the
  formats where a link survives *as a link*; saving show notes as flat text
  throws away the half of them that was the point.
* **Links...** lists every address in the notes, to open in the real browser or
  copy. Shared with the transcript reader (:mod:`quill.ui.link_list_dialog`),
  because a second, subtly different list of links is exactly the drift these
  shared surfaces exist to prevent.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.show_notes import html_to_plain_text, strip_html_images
from quill.ui.dialog_contract import apply_modal_ids


class ShowNotesDialog:
    """One episode's show notes, read with the Notes reader (qc.md 5c).

    The same reader Now Playing and the main window's pane use: headings by H,
    links and timestamps by Tab, Copy Notes in four formats, Links in These
    Notes, View in Browser. Two verbs of its own stay: Send to Editor, and Save
    As, which keeps a link *as a link* in HTML and Markdown.
    """

    def __init__(
        self,
        parent: object,
        *,
        episode_title: str,
        description_html: str,
        on_send_to_editor: Callable[[str], None] | None = None,
        announce_cb: Callable[[str], None] | None = None,
        on_seek: Callable[[int], None] | None = None,
        podcast_title: str = "",
        copy_format: Callable[[], str] | None = None,
        set_copy_format: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        from quill.ui.notes_reader import NotesReader

        self._wx = wx
        self._description_html = description_html
        self._plain_text = html_to_plain_text(description_html)
        self._on_send_to_editor = on_send_to_editor
        self._announce = announce_cb or (lambda _m: None)

        self.dialog = wx.Dialog(
            parent,
            title=f"Show Notes -- {episode_title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((620, 520))
        root = wx.BoxSizer(wx.VERTICAL)
        self.reader = NotesReader(
            self.dialog,
            root,
            label="Show &notes:",
            announce=self._announce,
            on_seek=on_seek,
            copy_format=copy_format or (lambda: "plain"),
            set_copy_format=set_copy_format,
            min_height=300,
        )
        self.reader.set_notes(description_html, title=episode_title, podcast=podcast_title)
        self._notes = self.reader.field  # what the window is for; focused on show

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        send_btn = wx.Button(self.dialog, label="&Send to Editor")
        send_btn.SetHelpText("Opens these show notes as a new document, as plain text.")
        self._save_btn = wx.Button(self.dialog, label="Save &As...")
        self._save_btn.SetHelpText(
            "Saves these show notes to a file as plain text, HTML or Markdown; the "
            "last two keep every link as a link."
        )
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(send_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._save_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        send_btn.Bind(wx.EVT_BUTTON, self._on_send_to_editor_click)
        self._save_btn.Bind(wx.EVT_BUTTON, lambda _e: self.save_as())

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        # Focus on the thing this window is for (qc.md 6b): the notes.
        self._notes.SetFocus()
        try:
            show_modal_dialog(self.dialog, "Show Notes", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def show_links(self) -> int:
        """List every address in the notes, to open or copy (the reader's Links)."""
        links = self.reader.links()
        self.reader.show_links()
        return len(links)

    def save_as(self) -> str:
        """Write the notes to a file, in a format the listener chooses.

        HTML keeps the publisher's own markup (minus images, as the rich view
        does) and Markdown converts it -- both keep every link *as a link*,
        which plain text cannot. Plain text stays first because it is what most
        people want; the other two exist because show notes are mostly links
        and saving them flat throws away the half that mattered.
        """
        wx = self._wx
        formats = self._save_formats()
        wildcard = "|".join(f"{label} (*.{ext})|*.{ext}" for label, ext, _writer in formats)
        dialog = wx.FileDialog(
            self.dialog,
            "Save Show Notes As",
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return ""
            path = dialog.GetPath()
            _label, extension, writer = formats[max(0, dialog.GetFilterIndex())]
        finally:
            dialog.Destroy()
        if not path.lower().endswith(f".{extension}"):
            path = f"{path}.{extension}"
        try:
            from pathlib import Path

            Path(path).write_text(writer(), encoding="utf-8")
        except OSError as error:
            self._announce(f"The show notes could not be saved. {error}")
            return ""
        self._announce(f"Saved the show notes to {path}.")
        return path

    def _save_formats(self):
        """``(label, extension, writer)`` in the order the dialog offers them."""
        from quill.core.html_to_markdown import html_to_markdown

        return (
            ("Plain text", "txt", lambda: self._plain_text),
            ("HTML", "html", lambda: strip_html_images(self._description_html)),
            ("Markdown", "md", lambda: html_to_markdown(self._description_html)),
        )

    def _on_send_to_editor_click(self, _event: object) -> None:
        if self._on_send_to_editor is not None:
            self._on_send_to_editor(self._plain_text)
            self._announce("Sent show notes to a new document")
