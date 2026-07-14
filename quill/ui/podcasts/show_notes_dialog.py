"""Podcasts > (selected episode) > View Show Notes... -- read an episode's
description either as a rich (but image-free) HTML view or as accessible
plain text with real paragraph line breaks, and optionally send it into a
new editor tab.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.show_notes import html_to_plain_text, strip_html_images
from quill.ui.dialog_contract import apply_modal_ids


class ShowNotesDialog:
    """Read-only viewer for one episode's show notes/description."""

    def __init__(
        self,
        parent: object,
        *,
        episode_title: str,
        description_html: str,
        on_send_to_editor: Callable[[str], None] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

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
        self.dialog.SetMinSize((560, 480))
        root = wx.BoxSizer(wx.VERTICAL)

        view_row = wx.BoxSizer(wx.HORIZONTAL)
        view_row.Add(
            wx.StaticText(self.dialog, label="&View as:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._view_choice = wx.Choice(self.dialog, choices=["Plain text", "Rich text"])
        self._view_choice.SetName("Show notes view: plain text or rich formatted text")
        self._view_choice.SetSelection(0)
        view_row.Add(self._view_choice, 0)
        root.Add(view_row, 0, wx.EXPAND | wx.ALL, 10)

        self._plain_view = wx.TextCtrl(
            self.dialog,
            value=self._plain_text or "(No show notes for this episode.)",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        )
        self._plain_view.SetName("Show notes, plain text")
        root.Add(self._plain_view, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._rich_view: object | None = None
        try:
            import wx.html as wxhtml

            self._rich_view = wxhtml.HtmlWindow(self.dialog)
            self._rich_view.SetName("Show notes, rich text")
            sanitized = strip_html_images(description_html)
            self._rich_view.SetPage(sanitized or "<p>(No show notes for this episode.)</p>")
            self._rich_view.Hide()
            root.Add(self._rich_view, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        except Exception:  # noqa: BLE001 - rich view is optional; plain text always works
            self._view_choice.Enable(False)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        send_btn = wx.Button(self.dialog, label="&Send to Editor")
        send_btn.SetName("Open these show notes as a new document")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(send_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._view_choice.Bind(wx.EVT_CHOICE, self._on_view_choice)
        send_btn.Bind(wx.EVT_BUTTON, self._on_send_to_editor_click)

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Show Notes", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _on_view_choice(self, _event: object) -> None:
        rich_selected = self._view_choice.GetSelection() == 1 and self._rich_view is not None
        self._plain_view.Show(not rich_selected)
        if self._rich_view is not None:
            self._rich_view.Show(rich_selected)
        self.dialog.Layout()

    def _on_send_to_editor_click(self, _event: object) -> None:
        if self._on_send_to_editor is not None:
            self._on_send_to_editor(self._plain_text)
            self._announce("Sent show notes to a new document")
