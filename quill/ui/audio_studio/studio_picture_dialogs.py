"""The two windows behind Describe a Folder and Describe Again in QUILL Studio.

Neither window sends anything. Describe a Folder's OK leads to one more
question that names the picture count and who receives them (codex.md 10B.4);
Describe Again's OK sends the one picture you chose, or leads to the same
question for a folder. The work is :mod:`quill.core.ai.picture_batch`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import wx

from quill.core.ai.picture_batch import MAX_CEILING
from quill.core.ai.vision_prompts import enabled_style_choices, resolve_prompt_text
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.

__all__ = ["DEFAULT_STYLE", "DescribeAgainDialog", "DescribeFolderDialog", "PictureChoices"]

#: The prompt style a run starts on: the family's default (vision_default_prompt_style).
DEFAULT_STYLE = "accessibility"

DESCRIBE_FOLDER_TITLE = "Describe a Folder"
DESCRIBE_AGAIN_TITLE = "Describe Again"


@dataclass(frozen=True, slots=True)
class PictureChoices:
    """What a person chose in either window."""

    style: str
    style_title: str
    prompt: str
    details: bool
    location: bool
    ceiling: int
    folder: str = ""
    subfolders: bool = False
    target: int = 0


class _StyleAndDetails:
    """The rows both windows share: prompt style, photo details, location, ceiling."""

    style: wx.Choice
    details: wx.CheckBox
    location: wx.CheckBox
    ceiling: wx.SpinCtrl
    _styles: list[dict[str, str]]

    def _add_shared_rows(self, owner: wx.Dialog, layout: wx.BoxSizer, ceiling: int) -> None:
        self._styles = enabled_style_choices()
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(owner, label="Prompt st&yle"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self.style = wx.Choice(owner, choices=[s["title"] for s in self._styles])
        set_accessible_name(self.style, "Prompt style")
        self.style.SetHelpText(
            "How the pictures are described. Accessibility suits most people; Concise is short, "
            "Detailed is long, and AI Alt Text writes three lengths of alt text."
        )
        ids = [s["id"] for s in self._styles]
        self.style.SetSelection(ids.index(DEFAULT_STYLE) if DEFAULT_STYLE in ids else 0)
        row.Add(self.style, 0)
        layout.Add(row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.details = wx.CheckBox(
            owner, label="Send the &photo details with each picture: date, camera and lens"
        )
        self.details.SetHelpText(
            "Read the date taken, the camera and the lens from the picture on this computer and "
            "send them with it, so the description can say when it was taken."
        )
        self.details.SetValue(True)
        self.details.Bind(wx.EVT_CHECKBOX, self._details_changed)
        layout.Add(self.details, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.location = wx.CheckBox(owner, label="Also send where it was taken (&GPS location)")
        self.location.SetHelpText(
            "Off unless you check it, every time. When checked, the picture's GPS coordinates go "
            "to the same AI as the picture, and to nobody else. No place name is looked up."
        )
        self.location.SetValue(False)
        layout.Add(self.location, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(owner, label="At most this many pictures in one &run"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.ceiling = wx.SpinCtrl(owner, min=1, max=MAX_CEILING, initial=max(1, ceiling))
        set_accessible_name(self.ceiling, "At most this many pictures in one run")
        self.ceiling.SetHelpText(
            "The run stops after this many pictures. Run it again for the rest; pictures already "
            "described are never sent twice."
        )
        row.Add(self.ceiling, 0)
        layout.Add(row, 0, wx.ALL, 10)

    def _details_changed(self, _event: wx.Event | None) -> None:
        self.location.Enable(self.details.GetValue())
        if not self.details.GetValue():
            self.location.SetValue(False)

    def _shared_choices(self) -> dict[str, object]:
        chosen = self._styles[max(0, self.style.GetSelection())]
        return {
            "style": chosen["id"],
            "style_title": chosen["title"],
            "prompt": resolve_prompt_text(chosen["id"]),
            "details": self.details.GetValue(),
            "location": self.details.GetValue() and self.location.GetValue(),
            "ceiling": int(self.ceiling.GetValue()),
        }


def _buttons(dialog: wx.Dialog, layout: wx.BoxSizer, label: str, ok_help: str) -> None:
    layout.Add(dialog.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10)
    apply_modal_ids(
        dialog, affirmative_id=wx.ID_OK, affirmative_label=label, cancel_id=wx.ID_CANCEL
    )
    for button_id, help_text in ((wx.ID_OK, ok_help), (wx.ID_CANCEL, "Close without describing.")):
        button = dialog.FindWindow(button_id)
        if button is not None:
            button.SetHelpText(help_text)


class DescribeFolderDialog(_StyleAndDetails, wx.Dialog):
    """Choose the folder, the prompt style, the photo details and the ceiling."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        choose_folder: Callable[[wx.Window, str], str | None],
        folder: str = "",
        ceiling: int = 25,
    ) -> None:
        super().__init__(parent, title=DESCRIBE_FOLDER_TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        self._choose_folder = choose_folder
        layout = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=(
                "Studio describes every picture in the folder, one at a time, and opens the "
                "descriptions in QUILL. Pictures already described are not sent again. Nothing "
                "is sent until you say yes to the next question."
            ),
        )
        intro.Wrap(dip(self, 520))
        layout.Add(intro, 0, wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(self, label="&Folder of pictures"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.folder = wx.TextCtrl(self, value=folder, size=(dip(self, 320), -1))
        set_accessible_name(self.folder, "Folder of pictures")
        self.folder.SetHelpText("The folder whose pictures you want described.")
        row.Add(self.folder, 1, wx.RIGHT, 6)
        browse = wx.Button(self, label="&Browse...")
        browse.SetHelpText("Choose the folder of pictures.")
        browse.Bind(wx.EVT_BUTTON, self._browse)
        row.Add(browse, 0)
        layout.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.subfolders = wx.CheckBox(self, label="Include the pictures in &subfolders")
        self.subfolders.SetHelpText("Describe the pictures in folders inside this one as well.")
        layout.Add(self.subfolders, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._add_shared_rows(self, layout, ceiling)
        _buttons(
            self,
            layout,
            "Continue",
            "Count the pictures and ask before sending any of them.",
        )
        self.SetSizerAndFit(layout)
        (self.style if folder else self.folder).SetFocus()

    def _browse(self, _event: wx.Event) -> None:
        chosen = self._choose_folder(self, self.folder.GetValue().strip())
        if chosen:
            self.folder.SetValue(chosen)

    def choices(self) -> PictureChoices:
        return PictureChoices(
            folder=self.folder.GetValue().strip(),
            subfolders=self.subfolders.GetValue(),
            **self._shared_choices(),  # type: ignore[arg-type]
        )


class DescribeAgainDialog(_StyleAndDetails, wx.Dialog):
    """Choose what to describe again and how; the connection is the one in use."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        targets: list[str],
        going_to: str,
        ceiling: int = 25,
    ) -> None:
        super().__init__(parent, title=DESCRIBE_AGAIN_TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        layout = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=(
                f"A new description is added beside the ones already there, so you can compare "
                f"them. It goes to {going_to}. To use another AI, choose it with Choose Your AI "
                "first, then come back here."
            ),
        )
        intro.Wrap(dip(self, 520))
        layout.Add(intro, 0, wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(self, label="&Describe again"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self.target = wx.Choice(self, choices=targets)
        set_accessible_name(self.target, "Describe again")
        self.target.SetHelpText(
            "The picture to describe again, every picture of a folder you described, or one "
            "picture from that folder."
        )
        self.target.SetSelection(0)
        row.Add(self.target, 1)
        layout.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self._add_shared_rows(self, layout, ceiling)
        _buttons(
            self,
            layout,
            "Describe again",
            "Describe it again in the style you chose. A folder is counted and asked about first.",
        )
        self.SetSizerAndFit(layout)
        self.target.SetFocus()

    def choices(self) -> PictureChoices:
        return PictureChoices(target=max(0, self.target.GetSelection()), **self._shared_choices())  # type: ignore[arg-type]
