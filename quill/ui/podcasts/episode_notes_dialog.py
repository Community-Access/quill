"""Podcasts > (selected episode) > My Notes in This Episode... -- browse,
jump to, copy, and delete this episode's timestamped notes.

Reachable **from the player** as well as from an episode's context menu in the
Manager (x.md item 11): a note is a thing you make while listening, so needing
to leave the player, find the episode in a tree and open a context menu to see
your notes was the wrong shape. ``Podcasts: My Notes in This Episode...`` acts
on whatever is playing.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.episode_notes import (
    EpisodeNote,
    format_note_for_sharing,
    notes_for_episode,
)
from quill.core.podcasts.episode_notes import (
    format_timestamp as _format_timestamp,
)
from quill.ui.dialog_contract import apply_modal_ids


class EpisodeNotesDialog:
    """Returns the selected note's start time in ms to jump to, or ``None``
    if closed without jumping."""

    def __init__(
        self,
        parent: object,
        *,
        show_id: str,
        episode_guid: str,
        episode_title: str,
        notes: list[EpisodeNote],
        on_delete: Callable[[str], list[EpisodeNote]] | None = None,
        announce_cb: Callable[[str], None] | None = None,
        show_title: str = "",
        audio_url: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self._show_id = show_id
        self._episode_guid = episode_guid
        self._episode_title = episode_title
        #: Only used to build the shareable text; absent is fine (a note whose
        #: show has since been unsubscribed still copies).
        self._show_title = show_title
        self._audio_url = audio_url
        self._notes = list(notes)
        self._on_delete = on_delete
        self._announce = announce_cb or (lambda _m: None)
        self._result: int | None = None

        self.dialog = wx.Dialog(
            parent,
            title=f"My Notes -- {episode_title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((480, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Notes"), 0, wx.LEFT | wx.TOP, 10)
        self._list = wx.ListBox(self.dialog)
        self._list.SetName("Your notes for this episode; select one and press Jump to go there")
        self._refresh_list()
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        jump_btn = wx.Button(self.dialog, wx.ID_OK, "&Jump To Note")
        copy_btn = wx.Button(self.dialog, label="&Copy Note")
        delete_btn = wx.Button(self.dialog, label="&Delete Note")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(jump_btn, 0, wx.RIGHT, 6)
        btn_row.Add(copy_btn, 0, wx.RIGHT, 6)
        btn_row.Add(delete_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_jump)
        jump_btn.Bind(wx.EVT_BUTTON, self._on_jump)
        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy_click)
        delete_btn.Bind(wx.EVT_BUTTON, self._on_delete_click)

    def _refresh_list(self) -> None:
        self._list.Clear()
        for note in self._notes:
            preview = note.text.splitlines()[0] if note.text else ""
            self._list.Append(f"{_format_timestamp(note.position_ms)} -- {preview}")
        if self._notes:
            self._list.SetSelection(0)

    def show(self) -> int | None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Jump To Note",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            answer = show_modal_dialog(self.dialog, "My Notes", announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _on_jump(self, _event: object) -> None:
        index = self._list.GetSelection()
        if 0 <= index < len(self._notes):
            self._result = self._notes[index].position_ms
            self.dialog.EndModal(self._wx.ID_OK)

    def _on_copy_click(self, _event: object) -> None:
        """Copy the selected note as text somebody else can act on.

        The episode, the show, the timestamp, the note and the audio link
        together -- the note's own text pasted alone is a fragment with no
        way back to the moment it marks.
        """
        wx = self._wx
        index = self._list.GetSelection()
        if not (0 <= index < len(self._notes)):
            self._announce("Select a note to copy.")
            return
        text = format_note_for_sharing(
            self._notes[index],
            show_title=self._show_title,
            episode_title=self._episode_title,
            audio_url=self._audio_url,
        )
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
        self._announce("Note copied")

    def _on_delete_click(self, _event: object) -> None:
        index = self._list.GetSelection()
        if not (0 <= index < len(self._notes)) or self._on_delete is None:
            return
        note = self._notes[index]
        updated = self._on_delete(note.note_id)
        self._notes = notes_for_episode(updated, self._show_id, self._episode_guid)
        self._refresh_list()
        self._announce("Note deleted")
