"""The media windows of their own: choosing files, and one file's details (wordpress.md 6.2).

Everything else the media commands show reuses :mod:`quill.ui.wordpress_dialogs`
(lists, reports, questions, confirmations) and the image dialog in
:mod:`quill.ui.wordpress_item_dialogs`. Standard controls only, F1 help on
every control, no network.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import wx

from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.wordpress_dialogs import ShowModal, _buttons, _row

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.

_WILDCARD = (
    "Pictures, sound, video and documents|*.png;*.jpg;*.jpeg;*.gif;*.webp;*.avif;*.heic;"
    "*.mp3;*.m4a;*.wav;*.ogg;*.mp4;*.m4v;*.mov;*.webm;*.pdf;*.docx;*.doc;*.pptx;*.xlsx;"
    "*.odt;*.txt;*.csv;*.vtt|All files|*.*"
)


def choose_files(parent: wx.Window, show_modal: ShowModal, *, title: str) -> list[Path]:
    """A standard Open dialog that takes many files; empty when cancelled."""
    with wx.FileDialog(
        parent,
        title,
        wildcard=_WILDCARD,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
    ) as picker:
        if show_modal(picker, title) != wx.ID_OK:
            return []
        return [Path(p) for p in picker.GetPaths()]


def choose_picture(parent: wx.Window, show_modal: ShowModal, *, title: str) -> Path | None:
    """A standard Open dialog for one picture; None when cancelled."""
    with wx.FileDialog(
        parent,
        title,
        wildcard="Pictures|*.png;*.jpg;*.jpeg;*.gif;*.webp|All files|*.*",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as picker:
        if show_modal(picker, title) != wx.ID_OK:
            return None
        return Path(picker.GetPath())


@dataclass
class UploadDetails:
    title: str
    alt: str
    caption: str
    decorative: bool


class UploadDetailsDialog(wx.Dialog):
    """Title, alt text (first, for a picture), Decorative and caption, before upload."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        name: str,
        site_name: str,
        is_image: bool,
        title: str = "",
        alt: str = "",
        caption: str = "",
        on_suggest_async: Callable[[Callable[[str], None]], None] | None = None,
        on_describe: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent, title=f"Upload: {name}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.SetHelpText(
            f"What {site_name}'s Media Library keeps with this file. Upload sends the file and "
            "these details; Cancel skips this file and the others carry on."
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.alt: wx.TextCtrl | None = None
        self.decorative: wx.CheckBox | None = None
        if is_image:
            self.alt = wx.TextCtrl(self, value=alt, style=wx.TE_MULTILINE)
            self.alt.SetHelpText(
                "Alternative text: what this picture says to someone using a screen reader. "
                "One or two sentences about its purpose; read out any words it shows. This is "
                "the library's default; each place it is used can still have its own."
            )
            self.alt.SetMinSize(dip_size(self, 440, 60))
            _row(sizer, self, "&Alternative text:", self.alt)
            self.suggest = wx.Button(self, label="&Suggest Alternative Text")
            self.suggest.SetHelpText(
                "Asks your chosen AI to propose alternative text from the picture. The "
                "proposal goes into the field for you to read and change; it is never saved "
                "by itself."
            )
            self.suggest.Enable(on_suggest_async is not None)
            if on_suggest_async is not None:
                self.suggest.Bind(wx.EVT_BUTTON, lambda _e: on_suggest_async(self.propose_alt))
            sizer.Add(self.suggest, 0, wx.LEFT | wx.RIGHT, 8)
            self.decorative = wx.CheckBox(
                self, label="&Decorative: it adds nothing a visitor needs"
            )
            self.decorative.SetHelpText(
                "Check this for a divider, a texture or a purely decorative picture. Its "
                "alternative text is left empty on purpose, so screen readers skip it."
            )
            alt_field = self.alt
            self.decorative.Bind(wx.EVT_CHECKBOX, lambda e: alt_field.Enable(not e.IsChecked()))
            sizer.Add(self.decorative, 0, wx.ALL, 8)
        self.title_field = wx.TextCtrl(self, value=title)
        self.title_field.SetHelpText(
            "The file's title in the Media Library. Only people who manage the site see it."
        )
        _row(sizer, self, "&Title:", self.title_field)
        self.caption = wx.TextCtrl(self, value=caption)
        self.caption.SetHelpText(
            "Visible text shown under the file where it is used: names, credits or context. "
            "Optional."
        )
        _row(sizer, self, "&Caption:", self.caption)
        if is_image:
            self.describe = wx.Button(self, label="Describe &Image...")
            self.describe.SetHelpText(
                "A longer description and appraisal of what is in the picture, for you: "
                "subject, arrangement, colours, any words, and problems like awkward cropping."
            )
            self.describe.Enable(on_describe is not None)
            if on_describe is not None:
                self.describe.Bind(wx.EVT_BUTTON, lambda _e: on_describe())
            sizer.Add(self.describe, 0, wx.ALL, 8)
        sizer.Add(_buttons(self, "Upload"), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)
        (self.alt or self.title_field).SetFocus()

    def propose_alt(self, proposal: str) -> None:
        if proposal and self and self.alt is not None:
            self.alt.SetValue(proposal)
            self.alt.SetFocus()
            self.alt.SelectAll()

    def answer(self) -> UploadDetails:
        decorative = bool(self.decorative and self.decorative.GetValue())
        alt = "" if decorative or self.alt is None else self.alt.GetValue().strip()
        return UploadDetails(
            title=self.title_field.GetValue().strip(),
            alt=alt,
            caption=self.caption.GetValue().strip(),
            decorative=decorative,
        )


def ask_upload_details(
    parent: wx.Window, show_modal: ShowModal, **kwargs: object
) -> UploadDetails | None:
    dialog = UploadDetailsDialog(parent, **kwargs)  # type: ignore[arg-type]
    try:
        if show_modal(dialog, dialog.GetTitle()) != wx.ID_OK:
            return None
        return dialog.answer()
    finally:
        dialog.Destroy()
