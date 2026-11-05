"""Make a picture with AI, by conversation (roadmap V1, wordpress.md 6.9).

Describe the picture, choose its shape, and press Make the picture. Then ask
for changes in words ("make the background darker") and press it again: each
version is kept in the Versions list, with a description from a separate look
by the vision model, so you hear what was actually drawn. Every request is
approved first, by the host, naming the provider, model and endpoint.

One window for every app: QUILL Studio opens it with Make a Video, and QUILL
and QUILL Lite open it from File > WordPress > Media and Files > Picture Maker
with the page's extras (a background, Suggest from Page Content, Describe,
Save As and Insert into Document). The work behind it is
:mod:`quill.core.ai.picture_maker`, also shared.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core.ai.image_generation import IMAGE_SIZES
from quill.core.ai.picture_maker import BACKGROUNDS, PictureSuggestion
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip_size

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.

Request = Callable[..., None]


class PictureMakerDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        request: Request,
        make_video: Callable[[Path], None] | None,
        announce: Callable[[str], None],
        title: str = "Make a picture with AI",
        page: PageExtras | None = None,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._request = request
        self._make_video = make_video
        self._announce = announce
        self._page = page
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
        self.background: wx.Choice | None = None
        self.colour: wx.TextCtrl | None = None
        self._backgrounds: list[tuple[str, str]] = []
        if page is not None:
            self._add_page_choices(layout, page)
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
        self.page_buttons: list[wx.Button] = []
        if page is not None:
            self._add_page_buttons(layout, page)
        self.video.Show(make_video is not None)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self.SetSizerAndFit(layout)
        self._sync()
        self.words.SetFocus()

    # -- the page's extras (wordpress.md 6.9) ------------------------------ #

    def _add_page_choices(self, layout: wx.BoxSizer, page: PageExtras) -> None:
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="Bac&kground"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._backgrounds = [
            (key, label) for key, label in BACKGROUNDS if key != "transparent" or page.transparent
        ]
        self.background = wx.Choice(self, choices=[label for _k, label in self._backgrounds])
        set_accessible_name(self.background, "Background")
        self.background.SetHelpText(
            "Normal lets the picture have its own background. Solid colour uses the colour you "
            "name. Transparent is offered only when your provider can make one: OpenAI image "
            "models can, Google Imagen cannot."
        )
        self.background.SetSelection(0)
        self.background.Bind(wx.EVT_CHOICE, lambda _e: self._sync())
        row.Add(self.background, 0, wx.RIGHT, 8)
        row.Add(wx.StaticText(self, label="Co&lour"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.colour = wx.TextCtrl(self, size=dip_size(self, 160, -1))
        set_accessible_name(self.colour, "Colour")
        palette = f" Your site's colours: {', '.join(page.palette)}." if page.palette else ""
        self.colour.SetHelpText(
            "The solid background colour, in words, such as navy or warm cream." + palette
        )
        row.Add(self.colour, 0)
        layout.Add(row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        suggest = page.suggest
        if suggest is not None:
            button = wx.Button(self, label="Suggest from &Page Content")
            button.SetHelpText(
                "Your chosen AI reads the page, or the selection, and proposes a description, a "
                "shape and a background. They land in these fields for you to change; nothing "
                "is made until you press Make the Picture."
            )
            button.Bind(wx.EVT_BUTTON, lambda _e: suggest(self.fill))
            layout.Add(button, 0, wx.LEFT | wx.TOP, 10)

    def _add_page_buttons(self, layout: wx.BoxSizer, page: PageExtras) -> None:
        row = wx.WrapSizer(wx.HORIZONTAL)
        actions: list[tuple[str, str, Callable[[Path], None] | None]] = [
            (
                "Describe &Image",
                "A fresh, longer description of the chosen version from your chosen AI: subject, "
                "arrangement, colours, any words, and problems.",
                page.describe,
            ),
            (
                "Open in Image Vi&ewer",
                "Open the chosen version in the picture viewer Windows uses.",
                page.open_viewer,
            ),
            ("Save &As...", "Save a copy of the chosen version somewhere else.", page.save_as),
            (page.insert_label, page.insert_help, page.insert),
        ]
        for label, help_text, run in actions:
            if run is None:
                continue
            button = wx.Button(self, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, r=run: self._on_page_action(r))
            row.Add(button, 0, wx.RIGHT | wx.BOTTOM, 8)
            self.page_buttons.append(button)
        layout.Add(row, 0, wx.LEFT | wx.RIGHT, 10)

    def _on_page_action(self, run: Callable[[Path], None]) -> None:
        picture = self.chosen()
        if picture is not None:
            run(picture)

    def fill(self, suggestion: PictureSuggestion) -> None:
        """Put a suggestion in the fields, to be changed; nothing is made."""
        if not self:
            return
        self.words.ChangeValue(suggestion.description)
        sizes = list(IMAGE_SIZES)
        if suggestion.shape in sizes:
            self.shape.SetSelection(sizes.index(suggestion.shape))
        if self.background is not None:
            keys = [key for key, _label in self._backgrounds]
            if suggestion.background in keys:
                self.background.SetSelection(keys.index(suggestion.background))
        if self.colour is not None:
            self.colour.ChangeValue(suggestion.colour)
        self._sync()
        self.words.SetFocus()

    def background_choice(self) -> tuple[str, str]:
        """``(background key, colour)`` as chosen; ``("normal", "")`` without the extras."""
        if self.background is None or self.colour is None or not self._backgrounds:
            return "normal", ""
        index = max(0, self.background.GetSelection())
        return self._backgrounds[index][0], self.colour.GetValue().strip()

    def _sync(self) -> None:
        has = bool(self.versions)
        self.video.Enable(has)
        self.folder.Enable(has)
        for button in getattr(self, "page_buttons", []):
            button.Enable(has)
        if self.colour is not None:
            self.colour.Enable(self.background_choice()[0] == "solid")
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

        if self._page is None:
            self._request(turns, size, done, failed)
            return
        background, colour = self.background_choice()
        self._request(turns, size, done, failed, background=background, colour=colour)

    def _on_version(self, _event: wx.Event) -> None:
        index = self.list.GetSelection()
        if 0 <= index < len(self.versions):
            self.description.ChangeValue(self.versions[index][1])

    def chosen(self) -> Path | None:
        index = self.list.GetSelection()
        return self.versions[index][0] if 0 <= index < len(self.versions) else None

    def _on_video(self, _event: wx.Event) -> None:
        picture = self.chosen()
        if picture is not None and self._make_video is not None:
            self.EndModal(wx.ID_CANCEL)
            self._make_video(picture)

    def _on_folder(self, _event: wx.Event) -> None:
        picture = self.chosen()
        if picture is not None:
            import os

            os.startfile(str(picture.parent))  # noqa: S606 - the user's own folder


class PageExtras:
    """What the WordPress Picture Maker adds to the window (wordpress.md 6.9).

    Each callable gets the chosen version's file; ``None`` leaves its button out.
    *suggest* gets :meth:`PictureMakerDialog.fill`, to call when the AI answers.
    """

    def __init__(
        self,
        *,
        transparent: bool,
        palette: list[str] | None = None,
        suggest: Callable[[Callable[[PictureSuggestion], None]], None] | None = None,
        describe: Callable[[Path], None] | None = None,
        open_viewer: Callable[[Path], None] | None = None,
        save_as: Callable[[Path], None] | None = None,
        insert: Callable[[Path], None] | None = None,
        insert_label: str = "Inse&rt into Document...",
        insert_help: str = (
            "Open the picture dialog for the chosen version: alternative text, caption and "
            "width. It is uploaded to the Media Library when you press Insert."
        ),
    ) -> None:
        self.transparent = transparent
        self.palette = palette or []
        self.suggest = suggest
        self.describe = describe
        self.open_viewer = open_viewer
        self.save_as = save_as
        self.insert = insert
        self.insert_label = insert_label
        self.insert_help = insert_help


def open_picture_maker(parent: Any, show_modal: Callable[[Any, str], int], **kwargs: Any) -> None:
    """Run the Picture Maker through the editor's own modal path."""
    dialog = PictureMakerDialog(parent, **kwargs)
    try:
        show_modal(dialog, dialog.GetTitle())
    finally:
        dialog.Destroy()
