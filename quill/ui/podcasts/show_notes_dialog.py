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
from typing import Any

from quill.core.podcasts.show_notes import html_to_plain_text, strip_html_images


class ShowNotesWindow:
    """One episode's show notes, read with the Notes reader (qc.md 5c).

    The same reader Now Playing and the main window's pane use: headings by H,
    links and timestamps by Tab, Copy Notes in four formats, Links in These
    Notes, View in Browser. Two verbs of its own stay: Send to Editor, and Save
    As, which keeps a link *as a link* in HTML and Markdown.

    A peer window (qc.md Phase 4): made once, and asked for again -- for this
    episode or another -- it is raised with the notes asked about.
    """

    TITLE = "Show Notes"
    MENU_TITLE = "Show No&tes"

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

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._body: Any = None
        self.frame = wx.Frame(parent, title="Show Notes", size=(760, 640))
        self.frame.SetMinSize((620, 520))
        self.frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.load(
            episode_title=episode_title,
            description_html=description_html,
            on_send_to_editor=on_send_to_editor,
            on_seek=on_seek,
            podcast_title=podcast_title,
            copy_format=copy_format,
            set_copy_format=set_copy_format,
        )
        self.frame.CentreOnParent()

    def load(
        self,
        *,
        episode_title: str,
        description_html: str,
        on_send_to_editor: Callable[[str], None] | None = None,
        on_seek: Callable[[int], None] | None = None,
        podcast_title: str = "",
        copy_format: Callable[[], str] | None = None,
        set_copy_format: Callable[[str], None] | None = None,
    ) -> None:
        """Show *episode_title*'s notes -- the first time, or for the next one asked."""
        from quill.ui.notes_reader import NotesReader

        wx = self._wx
        self._description_html = description_html
        self._plain_text = html_to_plain_text(description_html)
        self._on_send_to_editor = on_send_to_editor
        self.frame.SetTitle(f"Show Notes -- {episode_title}")
        if self._body is not None:
            self._body.Destroy()
        self._body = body = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)
        self.reader = NotesReader(
            body,
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
        send_btn = wx.Button(body, label="&Send to Editor")
        send_btn.SetHelpText("Opens these show notes as a new document, as plain text.")
        self._save_btn = wx.Button(body, label="Save &As...")
        self._save_btn.SetHelpText(
            "Saves these show notes to a file as plain text, HTML or Markdown; the "
            "last two keep every link as a link."
        )
        close_btn = wx.Button(body, label="Close")
        close_btn.SetHelpText("Closes this window and returns to where you were.")
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, close_btn, modeless=True)
        btn_row.Add(send_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._save_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        body.SetSizer(root)
        sizer = self.frame.GetSizer()
        sizer.Clear()
        sizer.Add(body, 1, wx.EXPAND)
        self.frame.Layout()
        send_btn.Bind(wx.EVT_BUTTON, self._on_send_to_editor_click)
        self._save_btn.Bind(wx.EVT_BUTTON, lambda _e: self.save_as())

    def focus_target(self) -> Any:
        # Focus on the thing this window is for (qc.md 6b): the notes.
        return self._notes

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
            self.frame,
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
