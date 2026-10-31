"""Make a YouTube video from a picture and sound: the window (roadmap V3, V4).

Choose a picture and a sound file (or arrive here from a sound-only recording,
which fills the sound in), choose the shape, and optionally a slow zoom, a
sound wave along the bottom, chapters from the recording's markers, a title
and a description. The sound is used exactly as it is.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.picture_video import (
    PICTURE_TYPES,
    SHAPES,
    SOUND_TYPES,
    PictureVideoPlan,
    read_markers,
    validate,
    video_name,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip_size

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class PictureVideoDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        choose_file: Callable[[wx.Window, str, str], str | None],
        picture: str = "",
        sound: str = "",
    ) -> None:
        super().__init__(
            parent,
            title="Make a YouTube video from a picture and sound",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._choose_file = choose_file
        layout = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=(
                "The sound goes into the video exactly as it is. To record new sound first, use "
                "Record a demonstration with the screen and camera turned off."
            ),
        )
        intro.Wrap(560)
        layout.Add(intro, 0, wx.ALL, 10)
        grid = wx.FlexGridSizer(cols=3, hgap=8, vgap=8)
        grid.AddGrowableCol(1)
        self.picture = self._file_row(
            grid,
            "&Picture",
            picture,
            "The picture shown for the whole video. It is fitted to the shape, never stretched.",
            "&Browse for a picture...",
            "Pictures|" + ";".join(f"*{ext}" for ext in PICTURE_TYPES),
        )
        self.sound = self._file_row(
            grid,
            "&Sound",
            sound,
            "The recording or audio file that plays for the length of the video.",
            "Browse for a so&und...",
            "Sound files|" + ";".join(f"*{ext}" for ext in SOUND_TYPES),
        )
        self.sound.Bind(wx.EVT_TEXT, self._sound_changed)
        grid.Add(wx.StaticText(self, label="S&hape"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.shape = wx.Choice(self, choices=[label for label, _w, _h in SHAPES.values()])
        set_accessible_name(self.shape, "Shape")
        self.shape.SetHelpText(
            "The video's size: YouTube's usual 1920 by 1080, square for social posts, "
            "vertical for Shorts, or the picture's own size."
        )
        self.shape.SetSelection(0)
        grid.Add(self.shape, 1, wx.EXPAND)
        grid.AddSpacer(1)
        layout.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.zoom = wx.CheckBox(self, label="A slow &zoom on the picture")
        self.zoom.SetHelpText(
            "The picture moves gently closer over the video, instead of staying still."
        )
        layout.Add(self.zoom, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.wave = wx.CheckBox(self, label="Show a sound &wave along the bottom")
        self.wave.SetHelpText(
            "A white wave that moves with the sound, so viewers can see sound is playing."
        )
        layout.Add(self.wave, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.chapters = wx.CheckBox(self, label="Use the recording's &markers as chapters")
        self.chapters.SetHelpText(
            "Markers you added while recording become chapters in the video and timestamps "
            "in the description. YouTube needs at least three, ten seconds apart."
        )
        layout.Add(self.chapters, 0, wx.ALL, 10)
        layout.Add(wx.StaticText(self, label="&Title"), 0, wx.LEFT, 10)
        self.title_field = wx.TextCtrl(self)
        set_accessible_name(self.title_field, "Title")
        self.title_field.SetHelpText("The video's title, up to 100 characters.")
        layout.Add(self.title_field, 0, wx.EXPAND | wx.ALL, 10)
        layout.Add(wx.StaticText(self, label="&Description"), 0, wx.LEFT, 10)
        self.description = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=dip_size(self, -1, 90))
        set_accessible_name(self.description, "Description")
        self.description.SetHelpText(
            "What viewers read under the video. Chapters are added at the end."
        )
        layout.Add(self.description, 0, wx.EXPAND | wx.ALL, 10)
        layout.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Make the video",
            cancel_id=wx.ID_CANCEL,
        )
        for button_id, help_text in (
            (wx.ID_OK, "Make the video, check it, and save the YouTube text beside it."),
            (wx.ID_CANCEL, "Close without making a video."),
        ):
            button = self.FindWindow(button_id)
            if button is not None:
                button.SetHelpText(help_text)
        self.SetSizerAndFit(layout)
        self._sound_changed(None)
        (self.picture if not picture else self.sound if not sound else self.title_field).SetFocus()

    def _file_row(self, grid, label, value, help_text, button_label, wildcard):
        grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        field = wx.TextCtrl(self, value=value)
        set_accessible_name(field, label.replace("&", ""))
        field.SetHelpText(help_text)
        grid.Add(field, 1, wx.EXPAND)
        button = wx.Button(self, label=button_label)
        button.SetHelpText(f"Choose the {label.replace('&', '').lower()} file.")
        button.Bind(wx.EVT_BUTTON, lambda _e: self._browse(field, label, wildcard))
        grid.Add(button, 0)
        return field

    def _browse(self, field: wx.TextCtrl, label: str, wildcard: str) -> None:
        chosen = self._choose_file(self, label.replace("&", ""), wildcard)
        if chosen:
            field.SetValue(chosen)

    def _markers_path(self) -> Path:
        sound = Path(self.sound.GetValue().strip())
        return sound.with_name(sound.stem + ".markers.txt")

    def _sound_changed(self, _event: wx.Event | None) -> None:
        has_markers = bool(self.sound.GetValue().strip()) and self._markers_path().is_file()
        self.chapters.Enable(has_markers)
        self.chapters.SetValue(has_markers)
        if not self.title_field.GetValue() and self.sound.GetValue().strip():
            self.title_field.ChangeValue(Path(self.sound.GetValue().strip()).stem)

    def build_plan(self) -> PictureVideoPlan:
        sound = Path(self.sound.GetValue().strip())
        plan = PictureVideoPlan(
            picture=Path(self.picture.GetValue().strip()),
            sound=sound,
            output=video_name(sound),
            shape=list(SHAPES)[max(0, self.shape.GetSelection())],  # type: ignore[arg-type]
            zoom=self.zoom.GetValue(),
            wave=self.wave.GetValue(),
            title=self.title_field.GetValue().strip(),
            description=self.description.GetValue().strip(),
            chapters=read_markers(self._markers_path()) if self.chapters.GetValue() else (),
        )
        validate(plan)
        return plan
