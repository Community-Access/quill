"""Ask AI questions about a video: choose the video and the stretch (roadmap A1).

The whole video, or a stretch from one time to another. Studio then lays out
frames from that stretch as one labelled picture and opens the Screenshot
Inspector's conversation, where nothing is sent until you approve it.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.video_review import FRAME_CHOICES, captions_beside
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class VideoQuestionDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        choose_file: Callable[[wx.Window, str, str], str | None],
        video: str = "",
    ) -> None:
        super().__init__(
            parent, title="Ask AI questions about a video", style=wx.DEFAULT_DIALOG_STYLE
        )
        self._choose_file = choose_file
        layout = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=(
                "Studio takes frames from the stretch you choose, lays them out as one labelled "
                "picture, and opens a conversation about it. Nothing is sent to AI until you "
                "approve it there."
            ),
        )
        intro.Wrap(520)
        layout.Add(intro, 0, wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label="&Video"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.video = wx.TextCtrl(self, value=video)
        set_accessible_name(self.video, "Video")
        self.video.SetHelpText("The video to ask about.")
        self.video.Bind(wx.EVT_TEXT, self._video_changed)
        row.Add(self.video, 1, wx.RIGHT, 6)
        browse = wx.Button(self, label="&Browse...")
        browse.SetHelpText("Choose the video file.")
        browse.Bind(wx.EVT_BUTTON, self._browse)
        row.Add(browse, 0)
        layout.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.whole = wx.RadioButton(self, label="The &whole video", style=wx.RB_GROUP)
        self.whole.SetHelpText("Look across the whole video.")
        self.stretch = wx.RadioButton(self, label="A &stretch of it")
        self.stretch.SetHelpText("Look only between the two times below.")
        for control in (self.whole, self.stretch):
            control.Bind(wx.EVT_RADIOBUTTON, self._mode_changed)
            layout.Add(control, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        times = wx.FlexGridSizer(cols=2, hgap=8, vgap=6)
        times.Add(
            wx.StaticText(self, label="&From, minutes and seconds"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.start = wx.TextCtrl(self, value="0:00")
        set_accessible_name(self.start, "From, minutes and seconds")
        self.start.SetHelpText("Where the stretch starts, like 1:05 or 1:02:03.")
        times.Add(self.start, 0)
        times.Add(
            wx.StaticText(self, label="&To, minutes and seconds"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.end = wx.TextCtrl(self)
        set_accessible_name(self.end, "To, minutes and seconds")
        self.end.SetHelpText("Where the stretch ends. Leave empty for the end of the video.")
        times.Add(self.end, 0)
        layout.Add(times, 0, wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(self, label="&Number of frames"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.frames = wx.Choice(self, choices=[str(n) for n in FRAME_CHOICES])
        set_accessible_name(self.frames, "Number of frames")
        self.frames.SetHelpText(
            "More frames show more of what happened; fewer make each frame larger and clearer."
        )
        self.frames.SetSelection(FRAME_CHOICES.index(9))
        row.Add(self.frames, 0)
        layout.Add(row, 0, wx.LEFT | wx.RIGHT, 10)
        self.transcript = wx.CheckBox(self, label="Include the trans&cript of that stretch")
        self.transcript.SetHelpText(
            "When captions exist beside the video, send what was said in the same stretch with "
            "the picture. Make captions from the recording's result window."
        )
        layout.Add(self.transcript, 0, wx.ALL, 10)
        layout.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Prepare the question",
            cancel_id=wx.ID_CANCEL,
        )
        for button_id, help_text in (
            (wx.ID_OK, "Take the frames and open the conversation. Nothing is sent yet."),
            (wx.ID_CANCEL, "Close without asking."),
        ):
            button = self.FindWindow(button_id)
            if button is not None:
                button.SetHelpText(help_text)
        self.SetSizerAndFit(layout)
        self.whole.SetValue(True)
        self._mode_changed(None)
        self._video_changed(None)
        (self.whole if video else self.video).SetFocus()

    def _browse(self, _event: wx.Event) -> None:
        chosen = self._choose_file(self, "Video", "Videos|*.mp4;*.mkv;*.mov;*.webm;*.avi")
        if chosen:
            self.video.SetValue(chosen)

    def _mode_changed(self, _event: wx.Event | None) -> None:
        self.start.Enable(self.stretch.GetValue())
        self.end.Enable(self.stretch.GetValue())

    def _video_changed(self, _event: wx.Event | None) -> None:
        text = self.video.GetValue().strip()
        has = bool(text) and captions_beside(Path(text)) is not None
        self.transcript.Enable(has)
        self.transcript.SetValue(has)

    def choices(self) -> tuple[Path, str, str, int, bool]:
        start, end = (
            ("", "") if self.whole.GetValue() else (self.start.GetValue(), self.end.GetValue())
        )
        frames = FRAME_CHOICES[max(0, self.frames.GetSelection())]
        return Path(self.video.GetValue().strip()), start, end, frames, self.transcript.GetValue()
