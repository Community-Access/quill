"""Record a demonstration: the setup dialog and its spoken check (Studio PRD 7A).

One window, top to bottom in the order a presenter decides: what to record,
which sounds go in (and, always named, whether the screen reader is one of
them), the camera, the picture, where the file goes. *Check* runs every
REC-011 check in the background and puts one summary into a read-only field
that takes focus, so the screen reader reads it once; Start recording stays
disabled while any Stop remains, and any change after a check asks for a new
one rather than starting on stale facts.

Sound sources are a list with a state column, not check boxes (QUILL's list
convention): Space puts the selected source in or out of the recording.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import replace

import wx
from wx.lib.scrolledpanel import ScrolledPanel

from quill.core.demo_recording import (
    CAMERA_POSITIONS,
    CAMERA_SIZES,
    COUNTDOWN_RANGE,
    FRAME_RATES,
    LEVEL_RANGE_DB,
    SOUND_FORMATS,
    CameraSetup,
    DemoPlan,
    DemoRecordingError,
    SoundSource,
    validate_plan,
)
from quill.core.studio_capture import CaptureTarget
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.studio_demo_actions import DemoActionsMixin
from quill.ui.studio_demo_picture import DemoPictureMixin
from quill.ui.studio_demo_sources import DemoSourcesMixin, recordable

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.

_SIZE_LABELS = ("Native size", "1080p (1080 pixels high)", "720p (720 pixels high)")


class DemoCallbacks:
    """What the dialog asks of its host; all run on the UI thread."""

    def __init__(
        self,
        *,
        check: Callable[[DemoPlan, Callable[[str, bool], None]], None],
        test: Callable[[DemoPlan, int], None],
        camera_check: Callable[[str, bool], None],
        sounds: Callable[[], None],
        assign_keys: Callable[[], None],
        choose_program: Callable[[], tuple[str, object, str] | None],
        list_targets: Callable[[], list[CaptureTarget]],
        cameras: list[str],
        microphones: list[str],
        readers: list[tuple[str, int]],
        studio_pid: int,
        display_info: Callable[[tuple[int, int, int, int]], tuple[str, tuple[int, int, int, int]]],
        confirm: Callable[[str, str], bool],
        choose_folder: Callable[[wx.Window, str], str | None],
    ) -> None:
        self.confirm = confirm
        self.choose_folder = choose_folder
        self.check = check
        self.test = test
        self.camera_check = camera_check
        self.sounds = sounds
        self.assign_keys = assign_keys
        self.choose_program = choose_program
        self.list_targets = list_targets
        self.cameras = cameras
        self.microphones = microphones
        self.readers = readers
        self.studio_pid = studio_pid
        self.display_info = display_info


class RecordDemoDialog(DemoSourcesMixin, DemoPictureMixin, DemoActionsMixin, wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        targets: list[CaptureTarget],
        callbacks: DemoCallbacks,
        preferences: dict,
        folder: str,
    ) -> None:
        super().__init__(
            parent, title="Record a demonstration", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.callbacks = callbacks
        self.preferences = preferences
        self.targets = recordable(targets)
        self.sources: list[SoundSource] = []
        self.checked_plan: DemoPlan | None = None
        self._checking = False
        panel = ScrolledPanel(self)
        self.content = panel
        outer = wx.BoxSizer(wx.VERTICAL)

        outer.Add(wx.StaticText(panel, label="&Target"), 0, wx.LEFT | wx.TOP, 10)
        self.target = wx.Choice(panel, choices=[t.friendly_label for t in self.targets])
        set_accessible_name(self.target, "Target")
        self.target.SetHelpText(
            "What to record: a named window, one display, or the full desktop. A window "
            "recording records that window's area of the screen; anything covering it is "
            "recorded too, and moving the window is not followed."
        )
        self.target.SetSelection(0 if self.targets else wx.NOT_FOUND)
        for index, target in enumerate(self.targets):
            if target.kind == "window":
                self.target.SetSelection(index)
                break
        self.target.Bind(wx.EVT_CHOICE, self._target_changed)
        outer.Add(self.target, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        refresh = wx.Button(panel, label="&Refresh windows and displays")
        refresh.SetHelpText("Read the list of windows and displays again.")
        refresh.Bind(wx.EVT_BUTTON, self._refresh_targets)
        outer.Add(refresh, 0, wx.ALL, 10)
        self.refresh_button = refresh
        self.screen_on = wx.CheckBox(panel, label="Include the screen pict&ure")
        self.screen_on.SetValue(bool(preferences.get("screen", True)))
        self.screen_on.SetHelpText(
            "Record the target above. Turn it off to record only the camera, or, with the "
            "camera off too, only sound."
        )
        self.screen_on.Bind(wx.EVT_CHECKBOX, self._picture_changed)
        outer.Add(self.screen_on, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        outer.Add(wx.StaticText(panel, label="&Sound sources"), 0, wx.LEFT, 10)
        self.source_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        set_accessible_name(self.source_list, "Sound sources")
        self.source_list.SetHelpText(
            "Every sound that can go into the recording. Space puts the selected source in "
            "or leaves it out. The screen reader and the microphone start left out; nothing "
            "you hear changes, only what is recorded."
        )
        for column, (title, width) in enumerate((("Source", 260), ("State", 140), ("Level", 90))):
            self.source_list.InsertColumn(column, title, width=width)
        self.source_list.Bind(wx.EVT_KEY_DOWN, self._source_key)
        self.source_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._source_selected)
        self.source_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._toggle_source())
        outer.Add(self.source_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(panel, label="&Level of the selected source, decibels"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            8,
        )
        low, high = LEVEL_RANGE_DB
        self.level = wx.SpinCtrlDouble(panel, min=low, max=high, initial=0.0, inc=1.0)
        self.level.SetDigits(0)
        set_accessible_name(self.level, "Level of the selected source, decibels")
        self.level.SetHelpText(
            "How loud the selected source is in the recording, from minus 60 to plus 12 "
            "decibels. 0 leaves it as it is. This never changes what you hear."
        )
        self.level.Bind(wx.EVT_SPINCTRLDOUBLE, self._level_changed)
        row.Add(self.level, 0)
        outer.Add(row, 0, wx.ALL, 10)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        add = wx.Button(panel, label="Add a &program's sound...")
        add.SetHelpText(
            "Choose another program that is playing sound, such as a media player, and add "
            "its sound as a source of its own."
        )
        add.Bind(wx.EVT_BUTTON, self._add_program)
        buttons.Add(add, 0, wx.RIGHT, 8)
        self.remove = wx.Button(panel, label="Re&move program")
        self.remove.SetHelpText("Remove a program you added. Built-in sources cannot be removed.")
        self.remove.Bind(wx.EVT_BUTTON, self._remove_program)
        buttons.Add(self.remove, 0, wx.RIGHT, 8)
        hear = wx.Button(panel, label="Mixer: sounds you &hear...")
        hear.SetHelpText(
            "Mute or unmute what you hear from any program, as the Windows volume mixer does. "
            "A program you mute there is silent for you and for every recording."
        )
        hear.Bind(wx.EVT_BUTTON, lambda _e: self.callbacks.sounds())
        buttons.Add(hear, 0)
        outer.Add(buttons, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        outer.Add(wx.StaticText(panel, label="Microphone &device"), 0, wx.LEFT, 10)
        self.microphone = wx.Choice(panel, choices=["System default", *callbacks.microphones])
        set_accessible_name(self.microphone, "Microphone device")
        self.microphone.SetHelpText(
            "Which microphone the Microphone source records. It opens only while you record "
            "and only when the Microphone source is in the recording."
        )
        saved_mic = self._saved_source("microphone").get("device", "")
        index = self.microphone.FindString(saved_mic) if saved_mic else 0
        self.microphone.SetSelection(index if index != wx.NOT_FOUND else 0)
        self.microphone.Bind(wx.EVT_CHOICE, self._microphone_changed)
        outer.Add(self.microphone, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        outer.Add(wx.StaticText(panel, label="&Your screen reader"), 0, wx.LEFT, 10)
        reader_choices = [self._reader_label(name) for name, _pid in callbacks.readers]
        self.reader = wx.Choice(panel, choices=[*reader_choices, "None"])
        set_accessible_name(self.reader, "Your screen reader")
        self.reader.SetHelpText(
            "The screen reader whose speech Studio keeps private. Its speech is left out of "
            "the recording unless you put Screen reader speech in."
        )
        saved_reader = str(preferences.get("screen_reader", ""))
        names = [name for name, _pid in callbacks.readers]
        self.reader.SetSelection(names.index(saved_reader) if saved_reader in names else 0)
        self.reader.Bind(wx.EVT_CHOICE, self._reader_changed)
        outer.Add(self.reader, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.exclude_reader = wx.CheckBox(
            panel, label="Leave the screen reader &out of system sound"
        )
        self.exclude_reader.SetValue(True)
        self.exclude_reader.SetHelpText(
            "When System sound is in the recording, record everything except your screen "
            "reader. Studio's own sounds are silenced while it records the system."
        )
        self.exclude_reader.Bind(wx.EVT_CHECKBOX, self._stale)
        outer.Add(self.exclude_reader, 0, wx.ALL, 10)

        camera = (
            preferences.get("camera", {}) if isinstance(preferences.get("camera"), dict) else {}
        )
        self.camera_on = wx.CheckBox(panel, label="Include the &camera picture")
        self.camera_on.SetHelpText(
            "Record your camera too. It is off unless you turn it on, and the camera opens "
            "only while you check its framing or record."
        )
        self.camera_on.SetValue(bool(camera.get("enabled", False)) and bool(callbacks.cameras))
        self.camera_on.Bind(wx.EVT_CHECKBOX, self._camera_toggled)
        outer.Add(self.camera_on, 0, wx.LEFT | wx.RIGHT, 10)
        self.camera_panel = wx.Panel(panel)
        grid = wx.FlexGridSizer(cols=2, hgap=10, vgap=6)
        grid.AddGrowableCol(1)
        grid.Add(
            wx.StaticText(self.camera_panel, label="Camera de&vice"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.camera = wx.Choice(self.camera_panel, choices=callbacks.cameras or ["No camera found"])
        set_accessible_name(self.camera, "Camera device")
        self.camera.SetHelpText("Which camera to record.")
        saved_camera = self.camera.FindString(str(camera.get("device", "")))
        self.camera.SetSelection(saved_camera if saved_camera != wx.NOT_FOUND else 0)
        self.camera.Bind(wx.EVT_CHOICE, self._stale)
        grid.Add(self.camera, 1, wx.EXPAND)
        grid.Add(
            wx.StaticText(self.camera_panel, label="Camera pos&ition"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self.position = wx.Choice(
            self.camera_panel, choices=[p[0].upper() + p[1:] for p in CAMERA_POSITIONS]
        )
        set_accessible_name(self.position, "Camera position")
        self.position.SetHelpText(
            "Which corner of the video shows your camera picture, or Camera only to record "
            "the camera instead of the screen picture."
        )
        position = str(camera.get("position", "bottom right"))
        self.position.SetSelection(
            CAMERA_POSITIONS.index(position) if position in CAMERA_POSITIONS else 0  # type: ignore[arg-type]
        )
        self.position.Bind(wx.EVT_CHOICE, self._stale)
        grid.Add(self.position, 1, wx.EXPAND)
        grid.Add(
            wx.StaticText(self.camera_panel, label="Camera picture si&ze"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self.camera_size = wx.Choice(
            self.camera_panel,
            choices=[f"{size} percent of the video width" for size in CAMERA_SIZES],
        )
        set_accessible_name(self.camera_size, "Camera picture size")
        self.camera_size.SetHelpText("How wide the camera picture is, as a share of the video.")
        size = int(camera.get("size_percent", 25) or 25)
        self.camera_size.SetSelection(CAMERA_SIZES.index(size) if size in CAMERA_SIZES else 2)
        self.camera_size.Bind(wx.EVT_CHOICE, self._stale)
        grid.Add(self.camera_size, 1, wx.EXPAND)
        self.camera_panel.SetSizer(grid)
        outer.Add(self.camera_panel, 0, wx.EXPAND | wx.ALL, 10)
        self.face_alerts = wx.CheckBox(panel, label="Tell me when my face leaves the camera vie&w")
        self.face_alerts.SetValue(bool(camera.get("face_alerts", True)))
        self.face_alerts.SetHelpText(
            "While recording, Studio says when your face leaves the camera's view and when it "
            "returns, using face detection that runs on this computer. When your screen "
            "reader's speech is being recorded, Studio adds a marker instead of speaking."
        )
        self.face_alerts.Bind(wx.EVT_CHECKBOX, self._stale)
        outer.Add(self.face_alerts, 0, wx.LEFT | wx.RIGHT, 10)
        self.mirrored = wx.CheckBox(panel, label="The camera gives a mirror image")
        self.mirrored.SetValue(bool(camera.get("mirrored", False)))
        self.mirrored.SetHelpText(
            "Turn this on if positioning advice sends you the wrong way: some cameras flip "
            "their picture left to right."
        )
        self.mirrored.Bind(wx.EVT_CHECKBOX, self._stale)
        outer.Add(self.mirrored, 0, wx.ALL, 10)
        self.camera_check_button = wx.Button(panel, label="Ch&eck camera framing...")
        self.camera_check_button.SetHelpText(
            "Open the camera and hear, as you move, whether your face is in view and centred, "
            "and which way to move. Nothing is recorded or saved."
        )
        self.camera_check_button.Bind(wx.EVT_BUTTON, self._camera_check)
        outer.Add(self.camera_check_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        video = wx.FlexGridSizer(cols=2, hgap=10, vgap=6)
        video.AddGrowableCol(1)
        video.Add(wx.StaticText(panel, label="Frame r&ate"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.fps = wx.Choice(panel, choices=[f"{rate} frames a second" for rate in FRAME_RATES])
        set_accessible_name(self.fps, "Frame rate")
        self.fps.SetHelpText(
            "30 suits most demonstrations. 60 is smoother and needs a display target and "
            "desktop duplication; 15 makes smaller files."
        )
        fps = int(preferences.get("fps", 30) or 30)
        self.fps.SetSelection(FRAME_RATES.index(fps) if fps in FRAME_RATES else 2)
        self.fps.Bind(wx.EVT_CHOICE, self._stale)
        video.Add(self.fps, 1, wx.EXPAND)
        video.Add(wx.StaticText(panel, label="Ma&ximum picture size"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.ceiling = wx.Choice(panel, choices=list(_SIZE_LABELS))
        set_accessible_name(self.ceiling, "Maximum picture size")
        self.ceiling.SetHelpText(
            "Native size keeps every pixel. 1080p or 720p scales a larger picture down, "
            "keeping its shape, for smaller files."
        )
        self.ceiling.SetSelection(
            {0: 0, 1080: 1, 720: 2}.get(int(preferences.get("size_ceiling", 0) or 0), 0)
        )
        self.ceiling.Bind(wx.EVT_CHOICE, self._stale)
        video.Add(self.ceiling, 1, wx.EXPAND)
        video.Add(wx.StaticText(panel, label="Countdown, seconds"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.countdown = wx.SpinCtrl(
            panel,
            min=COUNTDOWN_RANGE[0],
            max=COUNTDOWN_RANGE[1],
            initial=int(preferences.get("countdown", 3) or 0),
        )
        set_accessible_name(self.countdown, "Countdown, seconds")
        self.countdown.SetHelpText(
            "Seconds Studio counts down aloud before recording begins, so you can move to the "
            "program you are demonstrating. 0 starts at once."
        )
        video.Add(self.countdown, 0)
        outer.Add(video, 0, wx.EXPAND | wx.ALL, 10)
        self.pointer = wx.CheckBox(panel, label="Include the mouse poi&nter")
        self.pointer.SetValue(bool(preferences.get("pointer", True)))
        self.pointer.SetHelpText("Draw the mouse pointer in the video.")
        self.pointer.Bind(wx.EVT_CHECKBOX, self._stale)
        outer.Add(self.pointer, 0, wx.LEFT | wx.RIGHT, 10)

        outer.Add(wx.StaticText(panel, label="Save &folder"), 0, wx.LEFT | wx.TOP, 10)
        folder_row = wx.BoxSizer(wx.HORIZONTAL)
        self.folder = wx.TextCtrl(panel, value=str(preferences.get("folder") or folder))
        set_accessible_name(self.folder, "Save folder")
        self.folder.SetHelpText(
            "An absolute folder for the video and its check reports. An existing file is "
            "never replaced."
        )
        self.folder.Bind(wx.EVT_TEXT, self._stale)
        folder_row.Add(self.folder, 1, wx.RIGHT, 8)
        browse = wx.Button(panel, label="&Browse...")
        browse.SetHelpText("Choose the save folder.")
        browse.Bind(wx.EVT_BUTTON, self._browse)
        folder_row.Add(browse, 0)
        outer.Add(folder_row, 0, wx.EXPAND | wx.ALL, 10)
        self.stems = wx.CheckBox(panel, label="Also keep each sound source as its own WAV file")
        self.stems.SetValue(bool(preferences.get("keep_stems", False)))
        self.stems.SetHelpText("Beside the video, keep one WAV per sound source for later editing.")
        outer.Add(self.stems, 0, wx.LEFT | wx.RIGHT, 10)
        self.keep_awake = wx.CheckBox(panel, label="Keep the computer awake while recording")
        self.keep_awake.SetValue(bool(preferences.get("keep_awake", True)))
        self.keep_awake.SetHelpText(
            "Stop the computer sleeping, the screen turning off and the screen saver starting "
            "while you record or stream. Released as soon as you stop."
        )
        self.keep_awake.Bind(wx.EVT_CHECKBOX, self._stale)
        outer.Add(self.keep_awake, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.do_not_disturb = wx.CheckBox(panel, label="Turn on Do Not Disturb while recording")
        self.do_not_disturb.SetValue(bool(preferences.get("do_not_disturb", True)))
        self.do_not_disturb.SetHelpText(
            "Silence Windows notifications so none slides into the picture or the sound. "
            "Studio puts Do Not Disturb back the way it was when you stop, even after a crash."
        )
        self.do_not_disturb.Bind(wx.EVT_CHECKBOX, self._stale)
        outer.Add(self.do_not_disturb, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.silent_track = wx.CheckBox(
            panel, label="Give a video with no sound a silent soundtrack"
        )
        self.silent_track.SetValue(bool(preferences.get("silent_track", True)))
        self.silent_track.SetHelpText(
            "Some websites refuse a video with no soundtrack. On adds a silent one when no "
            "sound source is in the recording; off leaves the soundtrack out."
        )
        self.silent_track.Bind(wx.EVT_CHECKBOX, self._stale)
        outer.Add(self.silent_track, 0, wx.ALL, 10)
        outer.Add(wx.StaticText(panel, label="Sound-only file format"), 0, wx.LEFT, 10)
        self.sound_format = wx.Choice(
            panel, choices=[label for label, _ext in SOUND_FORMATS.values()]
        )
        set_accessible_name(self.sound_format, "Sound-only file format")
        self.sound_format.SetHelpText(
            "The kind of file Studio saves when there is no picture, only sound. M4A suits "
            "most uses; WAV and FLAC keep every detail; Opus is smallest for speech."
        )
        formats = list(SOUND_FORMATS)
        saved_format = str(preferences.get("sound_format", "m4a"))
        self.sound_format.SetSelection(
            formats.index(saved_format) if saved_format in formats else 0
        )  # type: ignore[arg-type]
        self.sound_format.Bind(wx.EVT_CHOICE, self._stale)
        outer.Add(self.sound_format, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self.check_button = wx.Button(panel, label="Chec&k")
        self.check_button.SetHelpText(
            "Check everything before recording: the target, a trial picture, each sound "
            "source, the microphone, the camera, FFmpeg, the folder and its free space. The "
            "result appears below and is read once."
        )
        self.check_button.Bind(wx.EVT_BUTTON, self._check)
        actions.Add(self.check_button, 0, wx.RIGHT, 8)
        test = wx.Button(panel, label="Record a &quick test")
        test.SetHelpText(
            "Record a short test with exactly these settings to a temporary file, check it "
            "the same way as a real recording, and offer to play it. The test file is "
            "deleted afterwards."
        )
        test.Bind(wx.EVT_BUTTON, self._test)
        actions.Add(test, 0, wx.RIGHT, 8)
        actions.Add(
            wx.StaticText(panel, label="Test length, seconds"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self.test_seconds = wx.SpinCtrl(panel, min=5, max=600, initial=5)
        set_accessible_name(self.test_seconds, "Test length, seconds")
        self.test_seconds.SetHelpText(
            "How long the test records, from 5 seconds to 10 minutes. A longer test is a "
            "rehearsal: it shows whether the settings hold up."
        )
        actions.Add(self.test_seconds, 0, wx.RIGHT, 8)
        keys = wx.Button(panel, label="Assi&gn keys...")
        keys.SetHelpText(
            "Assign system-wide keys to stop, pause, mark and check a recording from inside "
            "the program you are demonstrating."
        )
        keys.Bind(wx.EVT_BUTTON, lambda _e: self.callbacks.assign_keys())
        actions.Add(keys, 0)
        outer.Add(actions, 0, wx.ALL, 10)
        outer.Add(wx.StaticText(panel, label="Check result"), 0, wx.LEFT, 10)
        self.summary = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(-1, 160)
        )
        set_accessible_name(self.summary, "Check result")
        self.summary.SetHelpText(
            "What will be recorded, which sounds are in and out, where the file goes, then "
            "every problem. Stop means recording cannot start; Warn means it can but may be "
            "spoiled. Press Enter here to start recording when nothing stops it."
        )
        self.summary.ChangeValue("Choose your settings, then press Check.")
        self.summary.Bind(wx.EVT_KEY_DOWN, self._summary_key)
        outer.Add(self.summary, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(outer)
        panel.SetupScrolling(scroll_x=False)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(panel, 1, wx.EXPAND)
        layout.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Start recording",
            cancel_id=wx.ID_CANCEL,
        )
        self.start_button = self.FindWindow(wx.ID_OK)
        if self.start_button is not None:
            self.start_button.SetHelpText(
                "Start the countdown and record. Available after a check finds no Stop."
            )
            self.start_button.Enable(False)
        cancel = self.FindWindow(wx.ID_CANCEL)
        if cancel is not None:
            cancel.SetHelpText("Close without recording.")
        self.SetSizer(layout)
        available = wx.GetClientDisplayRect()
        self.SetSize((min(820, available.width), min(820, available.height)))
        self._build_sources()
        self._camera_toggled(None)
        self.target.SetFocus()

    # -- sources --------------------------------------------------------------------

    # -- camera ----------------------------------------------------------------------

    # -- the plan and the check --------------------------------------------------------

    def build_plan(self) -> DemoPlan:
        target = self._current_target()
        if not self.screen_on.GetValue():
            # No screen picture: the target is irrelevant and never checked.
            target = CaptureTarget("display", "No screen", (0, 0, 0, 0))
        elif target is None:
            raise DemoRecordingError("Choose a window, display or the full desktop to record.")
        if self.screen_on.GetValue():
            device, display_bounds = self.callbacks.display_info(target.bounds)
        else:
            device, display_bounds = "", (0, 0, 0, 0)
        reader, reader_pid = self._reader()
        sources = []
        for source in self.sources:
            if source.kind == "system" and self.exclude_reader.GetValue() and reader_pid:
                source = replace(source, exclude_process_id=reader_pid, exclude_name=reader)
            sources.append(source)
        camera_on = self.camera_on.GetValue() and bool(self.callbacks.cameras)
        plan = DemoPlan(
            target_kind=target.kind,  # type: ignore[arg-type]
            target_label=target.friendly_label,
            target_identity=target.label,
            screen=self.screen_on.GetValue(),
            sound_format=list(SOUND_FORMATS)[max(0, self.sound_format.GetSelection())],  # type: ignore[arg-type]
            silent_track=self.silent_track.GetValue(),
            keep_awake=self.keep_awake.GetValue(),
            do_not_disturb=self.do_not_disturb.GetValue(),
            bounds=target.bounds,
            folder=os.path.expanduser(self.folder.GetValue().strip()),
            window_handle=target.window_handle,
            process_id=target.process_id,
            application=target.application,
            display_bounds=target.bounds if target.kind == "display" else display_bounds,
            display_device=target.device if target.kind == "display" else device,
            fps=FRAME_RATES[max(0, self.fps.GetSelection())],
            pointer=self.pointer.GetValue(),
            size_ceiling=(0, 1080, 720)[max(0, self.ceiling.GetSelection())],
            sources=tuple(sources),
            camera=CameraSetup(
                enabled=camera_on,
                device=self.camera.GetString(self.camera.GetSelection()) if camera_on else "",
                position=CAMERA_POSITIONS[max(0, self.position.GetSelection())],
                size_percent=CAMERA_SIZES[max(0, self.camera_size.GetSelection())],
                face_alerts=self.face_alerts.GetValue(),
                mirrored=self.mirrored.GetValue(),
            ),
            keep_stems=self.stems.GetValue(),
            countdown=self.countdown.GetValue(),
            studio_process_id=self.callbacks.studio_pid,
            screen_reader=reader,
        )
        validate_plan(plan)
        return plan
