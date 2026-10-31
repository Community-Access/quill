"""Make a picture with AI, by conversation (roadmap V1).

Describe the picture, choose its shape, and press Make the picture. Then ask
for changes in words ("make the background darker") and press it again: each
version is kept in the Versions list, with a description from a separate look
by the vision model, so you hear what was actually drawn. Every request is
approved first, by the host, naming the provider, model and endpoint.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.ai.image_generation import IMAGE_SIZES
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip_size

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.

Request = Callable[[list[str], str, Callable[[Path, str], None], Callable[[str], None]], None]


class PictureMakerDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        request: Request,
        make_video: Callable[[Path], None],
        announce: Callable[[str], None],
    ) -> None:
        super().__init__(
            parent, title="Make a picture with AI", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._request = request
        self._make_video = make_video
        self._announce = announce
        self.turns: list[str] = []
        self.versions: list[tuple[Path, str]] = []
        self._busy = False
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(
            wx.StaticText(self, label="&Describe the picture, or the change you want"),
            0,
            wx.LEFT | wx.TOP,
            10,
        )
        self.words = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=dip_size(self, 560, 80))
        set_accessible_name(self.words, "Describe the picture, or the change you want")
        self.words.SetHelpText(
            "First, describe the whole picture. After that, say only what to change, such as "
            "make the background darker; every earlier request is kept."
        )
        layout.Add(self.words, 0, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="S&hape"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.shape = wx.Choice(self, choices=[label for label, _s, _a in IMAGE_SIZES.values()])
        set_accessible_name(self.shape, "Shape")
        self.shape.SetHelpText("Wide for a YouTube video, square for a cover, tall for Shorts.")
        self.shape.SetSelection(0)
        row.Add(self.shape, 0, wx.RIGHT, 8)
        self.make = wx.Button(self, label="&Make the picture")
        self.make.SetHelpText(
            "Send the description to your AI provider after you approve it, then have the "
            "picture described to you."
        )
        self.make.Bind(wx.EVT_BUTTON, self._on_make)
        row.Add(self.make, 0)
        layout.Add(row, 0, wx.LEFT | wx.RIGHT, 10)
        layout.Add(wx.StaticText(self, label="&Versions"), 0, wx.LEFT | wx.TOP, 10)
        self.list = wx.ListBox(self, size=dip_size(self, 560, 90))
        set_accessible_name(self.list, "Versions")
        self.list.SetHelpText(
            "Every picture made so far, newest last. Choose one to hear its description."
        )
        self.list.Bind(wx.EVT_LISTBOX, self._on_version)
        layout.Add(self.list, 0, wx.EXPAND | wx.ALL, 10)
        layout.Add(wx.StaticText(self, label="Description of the chosen version"), 0, wx.LEFT, 10)
        self.description = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=dip_size(self, 560, 110)
        )
        set_accessible_name(self.description, "Description of the chosen version")
        self.description.SetHelpText(
            "What the vision model sees in the picture, from a separate look, not the "
            "generator's own claim."
        )
        layout.Add(self.description, 0, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.video = wx.Button(self, label="Make a video &with this picture...")
        self.video.SetHelpText("Use the chosen version as the picture of a YouTube video.")
        self.video.Bind(wx.EVT_BUTTON, self._on_video)
        row.Add(self.video, 0, wx.RIGHT, 8)
        self.folder = wx.Button(self, label="Open &folder")
        self.folder.SetHelpText("Open the folder where the pictures are saved.")
        self.folder.Bind(wx.EVT_BUTTON, self._on_folder)
        row.Add(self.folder, 0, wx.RIGHT, 8)
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Close. The pictures stay saved.")
        row.Add(close, 0)
        layout.Add(row, 0, wx.ALL, 10)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self.SetSizerAndFit(layout)
        self._sync()
        self.words.SetFocus()

    def _sync(self) -> None:
        has = bool(self.versions)
        self.video.Enable(has)
        self.folder.Enable(has)
        self.make.SetLabel("&Make the change" if self.turns else "&Make the picture")
        self.make.Enable(not self._busy)

    def _on_make(self, _event: wx.Event) -> None:
        words = self.words.GetValue().strip()
        if not words:
            self._announce(
                "Describe the picture first." if not self.turns else "Say what to change first."
            )
            self.words.SetFocus()
            return
        turns = [*self.turns, words]
        size = list(IMAGE_SIZES)[max(0, self.shape.GetSelection())]
        self._busy = True
        self._sync()

        def done(path: Path, description: str) -> None:
            if not self:
                return
            self._busy = False
            self.turns = turns
            self.versions.append((path, description))
            self.list.Append(f"Version {len(self.versions)}: {path.name}")
            self.list.SetSelection(len(self.versions) - 1)
            self.description.ChangeValue(description)
            self.words.ChangeValue("")
            self._sync()
            self.description.SetFocus()

        def failed(message: str) -> None:
            if not self:
                return
            self._busy = False
            self._sync()
            self._announce(message)

        self._request(turns, size, done, failed)

    def _on_version(self, _event: wx.Event) -> None:
        index = self.list.GetSelection()
        if 0 <= index < len(self.versions):
            self.description.ChangeValue(self.versions[index][1])

    def chosen(self) -> Path | None:
        index = self.list.GetSelection()
        return self.versions[index][0] if 0 <= index < len(self.versions) else None

    def _on_video(self, _event: wx.Event) -> None:
        picture = self.chosen()
        if picture is not None:
            self.EndModal(wx.ID_CANCEL)
            self._make_video(picture)

    def _on_folder(self, _event: wx.Event) -> None:
        picture = self.chosen()
        if picture is not None:
            import os

            os.startfile(str(picture.parent))  # noqa: S606 - the user's own folder
