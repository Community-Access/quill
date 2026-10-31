"""After a demonstration is saved: the check's result and what to do next (REC-014).

The spoken outcome is one sentence; this window holds it and every check, in
a read-only field that takes focus, with Play, Open folder, Copy path and
Inspect a frame (which opens the Screenshot Inspector on a frame taken from
the middle of the video).
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip_size

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


class DemoResultDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        text: str,
        *,
        play: Callable[[], None],
        open_folder: Callable[[], None],
        copy_path: Callable[[], None],
        inspect_frame: Callable[[], None] | None,
        title: str = "Demonstration saved",
        make_video: Callable[[], None] | None = None,
        make_captions: Callable[[], None] | None = None,
        ask_ai: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(wx.StaticText(self, label="Result"), 0, wx.LEFT | wx.TOP, 10)
        self.text = wx.TextCtrl(
            self, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY, size=dip_size(self, 560, 260)
        )
        set_accessible_name(self.text, "Result")
        self.text.SetHelpText(
            "Verified means every objective check passed. Needs review means the file plays "
            "but something may be spoiled, such as a silent source or black stretches. "
            "Failed means a stream is missing or the file does not decode."
        )
        layout.Add(self.text, 1, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, action, help_text in (
            ("&Play", play, "Play the video in your usual player."),
            ("Open &folder", open_folder, "Open the folder that holds the video."),
            ("&Copy path", copy_path, "Copy the video's full path to the clipboard."),
        ):
            button = wx.Button(self, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, run=action: run())
            row.Add(button, 0, wx.RIGHT, 6)
        if inspect_frame is not None:
            inspect = wx.Button(self, label="&Inspect a frame...")
            inspect.SetHelpText(
                "Take a picture from the middle of the video and open it in the Screenshot "
                "Inspector, to read its text or ask AI about it with your approval."
            )
            inspect.Bind(wx.EVT_BUTTON, lambda _e: inspect_frame())
            row.Add(inspect, 0, wx.RIGHT, 6)
        if ask_ai is not None:
            ask = wx.Button(self, label="&Ask AI about this video...")
            ask.SetHelpText(
                "Ask questions about the whole video or a stretch of it. Nothing is sent "
                "until you approve it."
            )
            ask.Bind(wx.EVT_BUTTON, lambda _e: (self.EndModal(wx.ID_CANCEL), ask_ai()))
            row.Add(ask, 0, wx.RIGHT, 6)
        if make_captions is not None:
            captions = wx.Button(self, label="Make captions and a &transcript")
            captions.SetHelpText(
                "Transcribe the speech on this computer and save captions (SRT and VTT) and a "
                "plain transcript beside the file. Nothing is sent anywhere."
            )
            captions.Bind(wx.EVT_BUTTON, lambda _e: (self.EndModal(wx.ID_CANCEL), make_captions()))
            row.Add(captions, 0, wx.RIGHT, 6)
        if make_video is not None:
            video = wx.Button(self, label="Make a &video with a picture...")
            video.SetHelpText(
                "Turn this sound into a video YouTube accepts, with a picture you choose."
            )
            video.Bind(wx.EVT_BUTTON, lambda _e: (self.EndModal(wx.ID_CANCEL), make_video()))
            row.Add(video, 0, wx.RIGHT, 6)
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Close this window.")
        row.Add(close, 0)
        layout.Add(row, 0, wx.ALL, 10)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self.SetSizerAndFit(layout)
        self.text.SetFocus()
