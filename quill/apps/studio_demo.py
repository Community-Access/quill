"""Record a Demonstration in QUILL Studio: menu, tray, keys and the recording's life.

A thin adapter, like :mod:`quill.apps.studio_capture`: the rules are in
:mod:`quill.core.demo_recording`, the Windows work in
:mod:`quill.platform.windows.screen_recorder`, the windows in
``quill/ui/studio_demo_*.py``. This mixin owns the order of events -- the
spoken check, the microphone lock, the countdown, hiding Studio from its own
recording, the Recording status window, Stop and save, and recovery after a
crash -- and the rule about what Studio may say while it records (REC-016):
failures always; confirmations as speech, or as sounds only when the screen
reader's own speech is part of the recording.

Background work runs on the task manager; nothing here blocks the UI thread
on FFmpeg or a device.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import wx

from quill.apps.studio_demo_finish import StudioDemoFinishMixin
from quill.apps.studio_demo_setup import StudioDemoSetupMixin
from quill.apps.studio_picture_maker import StudioPictureMakerMixin
from quill.apps.studio_picture_video import StudioPictureVideoMixin
from quill.apps.studio_streaming import StudioStreamingMixin
from quill.core.demo_recording import (
    MICROPHONE_KEY,
    DemoPlan,
    default_folder,
    spoken_duration,
)
from quill.core.demo_recording_session import preferences_from_plan
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic
from quill.stability.task_manager import UiLifetimeToken
from quill.ui.post_menu_speech import SettledSpeechMixin

_PREFS_FILE = "studio-demo-recording.json"
_SUPPRESSED = "Recording a demonstration"


class StudioDemoMixin(
    SettledSpeechMixin,
    StudioDemoSetupMixin,
    StudioDemoFinishMixin,
    StudioPictureVideoMixin,
    StudioPictureMakerMixin,
    StudioStreamingMixin,
):
    # -- commands, menu, tray -----------------------------------------------------

    def _demo_command_specs(self):
        return (
            ("studio.record_demo", "R&ecord a demonstration...", self.record_demonstration),
            ("studio.record_pause", "Pa&use or resume recording", self.pause_demonstration),
            ("studio.record_marker", "Add a recording mar&ker", self.mark_demonstration),
            ("studio.record_mute", "&Mute microphone in recording", self.mute_demonstration),
            ("studio.record_status", "Recording s&tatus", self.speak_demonstration_status),
            ("studio.record_window", "Show recording &window", self.show_demonstration_window),
            (
                "studio.record_emergency_stop",
                "Emer&gency stop and save",
                self.emergency_stop_demonstration,
            ),
            ("studio.record_discard", "Di&scard this recording...", self.discard_demonstration),
            (
                "studio.record_recover",
                "Reco&ver unfinished recordings...",
                self.recover_demonstrations,
            ),
            ("studio.camera_check", "Check camera &framing...", self.check_camera_framing),
            ("studio.mixer", "Studio Mi&xer...", self.open_mixer),
            ("studio.broadcast", "&Broadcast live...", self.broadcast_live),
            ("studio.broadcast_mute", "Mute everything public", self.mute_broadcast),
            ("studio.broadcast_stop", "Stop the &live broadcast", self.stop_broadcast),
            ("studio.make_picture", "&New picture with AI...", self.make_picture_with_ai),
            (
                "studio.ask_ai_video",
                "Ask AI &questions about a video...",
                self.ask_ai_about_video,
            ),
            (
                "studio.picture_video",
                "Make a &YouTube video from a picture and sound...",
                self.make_picture_video,
            ),
        )

    def _append_demo_menu(self, capture: wx.Menu) -> list:
        self._post_menu_speech_for().watch(self.frame)
        capture.AppendSeparator()
        bindings = []
        for command_id, label, handler in self._demo_command_specs():
            item_id = wx.NewIdRef()
            capture.Append(item_id, self._menu_label(label, command_id))
            bindings.append((item_id, handler))
        return bindings

    def _register_demo_commands(self) -> None:
        for command_id, label, handler in self._demo_command_specs():
            self.commands.register(
                command_id, label.replace("&", ""), handler, self._binding_for(command_id)
            )

    def _append_demo_tray(self, menu: wx.Menu) -> None:
        """Recording items act without restoring Studio, so it stays out of the video."""
        self._post_menu_speech_for().watch(menu)  # UX-013: speak after the reader's focus line
        recorder = getattr(self, "_demo", None)
        if recorder is None:
            entries = [
                ("studio.record_demo", "Record a demonstration...", self.record_demonstration, True)
            ]
        else:
            paused = recorder.state == "paused"
            entries = [
                (
                    "studio.record_demo",
                    "Stop and save the recording",
                    self.stop_demonstration,
                    False,
                ),
                (
                    "studio.record_pause",
                    "Resume recording" if paused else "Pause recording",
                    self.pause_demonstration,
                    False,
                ),
                ("studio.record_marker", "Add a marker", self.mark_demonstration, False),
                (
                    "studio.record_status",
                    "Recording status",
                    self.speak_demonstration_status,
                    False,
                ),
                (
                    "studio.record_window",
                    "Show recording window",
                    self.show_demonstration_window,
                    False,
                ),
            ]
        for command, label, action, restore in entries:
            item_id = wx.NewIdRef()
            menu.Append(item_id, self._menu_label(label, command))
            menu.Bind(
                wx.EVT_MENU,
                lambda _e, run=action, show=restore: (
                    self._restore_from_tray() if show else None,
                    run(),
                ),
                id=item_id,
            )
            self._keep_menu_ids(item_id)
        menu.AppendSeparator()

    # -- shared helpers -----------------------------------------------------------

    def _demo_lifetime(self) -> UiLifetimeToken:
        self._ensure_capture_lifetime()
        return self._capture_lifetime

    def _demo_preferences(self) -> dict:
        data = read_json(app_data_dir() / _PREFS_FILE, {})
        return data if isinstance(data, dict) else {}

    def _demo_default_folder(self) -> Path:
        from quill.core.paths import portable_bundle_root
        from quill.platform.windows.screen_recorder_finish import videos_folder

        try:
            portable = portable_bundle_root() is not None
        except Exception:  # noqa: BLE001 - not knowing means installed
            portable = False
        return default_folder(videos_folder(), app_data_dir(), portable=portable)

    def _demo_ffmpeg(self):
        from quill.core.speech.ffmpeg import find_ffmpeg

        return find_ffmpeg()

    def _demo_caps(self, ffmpeg: str):
        cached = getattr(self, "_demo_caps_cache", None)
        if cached is not None and cached[0] == ffmpeg:
            return cached[1]
        from quill.platform.windows.demo_media import probe_capabilities

        caps = probe_capabilities(ffmpeg)
        self._demo_caps_cache = (ffmpeg, caps)
        return caps

    def _demo_reader_speech_recorded(self) -> bool:
        recorder = getattr(self, "_demo", None)
        return recorder is not None and recorder.plan.source("screen_reader") is not None

    def _demo_say(self, sentence: str, *, failure: bool = False) -> None:
        """REC-016: failures always speak; others only when the reader is not recorded."""
        self._set_status_quiet(sentence)
        if failure or not self._demo_reader_speech_recorded():
            self._announce_settled(sentence)
        else:
            from quill.ui import sound_manager

            sound_manager.post_sound("notification")

    def _recording_hotkeys_assigned(self) -> int:
        from quill.apps.studio_capture_hotkeys import RECORDING_HOTKEY_COMMANDS

        allowed = {entry[0] for entry in RECORDING_HOTKEY_COMMANDS}
        registered = set(getattr(self, "_global_hotkey_map", {}).values())
        return len(allowed & registered)

    @staticmethod
    def _running_readers() -> list[tuple[str, int]]:
        from quill.platform.windows.process_loopback import READER_PROCESSES

        found: dict[str, int] = {}
        try:
            import psutil

            for process in psutil.process_iter(["pid", "name"]):
                name = str(process.info.get("name") or "").lower()
                if name in READER_PROCESSES and name not in found:
                    found[name] = int(process.info["pid"])
        except Exception:  # noqa: BLE001 - no reader list is still a usable dialog
            pass
        order = ("jfw.exe", "nvda.exe", "narrator.exe")
        return sorted(found.items(), key=lambda item: order.index(item[0]))

    # -- Record a demonstration ------------------------------------------------------

    def record_demonstration(self) -> None:
        if getattr(self, "_demo", None) is not None:
            self.stop_demonstration()
            return
        if getattr(self, "_demo_busy", ""):
            self._announce(f"{self._demo_busy}. Wait for it to finish.")
            return
        if not self.frame.IsShown():
            self._restore_from_tray()
        ffmpeg = self._demo_ffmpeg()
        if not ffmpeg:
            self._show_message_box(
                "Recording a demonstration needs FFmpeg. Use Voices, Get FFmpeg, then try again.",
                "Record a demonstration",
                wx.OK | wx.ICON_ERROR,
            )
            return
        caps = self._demo_caps(ffmpeg)
        if not caps.can_record:
            self._show_message_box(
                "This FFmpeg cannot record a demonstration: it needs a screen grabber, an H.264 "
                "video encoder and the AAC audio encoder. Use Voices, Get FFmpeg to replace it.",
                "Record a demonstration",
                wx.OK | wx.ICON_ERROR,
            )
            return
        from quill.platform.windows.demo_audio import list_microphones
        from quill.platform.windows.demo_media import list_cameras
        from quill.platform.windows.screen_recorder_check import display_for
        from quill.platform.windows.studio_capture import list_capture_targets
        from quill.ui.studio_demo_dialog import DemoCallbacks, RecordDemoDialog

        try:
            targets = list_capture_targets(include_all_windows=False)
        except Exception as error:  # noqa: BLE001 - shown, never raised
            self._show_message_box(str(error), "Record a demonstration", wx.OK | wx.ICON_ERROR)
            return
        try:
            microphones = [mic.name for mic in list_microphones()]
        except Exception:  # noqa: BLE001 - no audio stack still lets the screen record
            microphones = []
        callbacks = DemoCallbacks(
            check=lambda plan, done: self._run_demo_check(plan, done, ffmpeg, caps),
            test=lambda plan, seconds: self._run_demo_test(plan, ffmpeg, caps, seconds),
            camera_check=lambda device, mirrored: self._camera_check_dialog(
                ffmpeg, device, mirrored
            ),
            sounds=self.open_mixer,
            assign_keys=self.open_capture_hotkeys,
            choose_program=self._choose_program,
            list_targets=lambda: list_capture_targets(include_all_windows=False),
            cameras=list_cameras(ffmpeg),
            microphones=microphones,
            readers=self._running_readers(),
            studio_pid=os.getpid(),
            display_info=display_for,
            confirm=lambda text, title: (
                self._show_message_box(text, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
                in (wx.YES, wx.ID_YES)
            ),
            choose_folder=self._choose_demo_folder,
        )
        dialog = RecordDemoDialog(
            self.frame,
            targets,
            callbacks,
            self._demo_preferences(),
            str(self._demo_default_folder()),
        )
        self._demo_dialog = dialog
        try:
            if self._show_modal_dialog(dialog, "Record a demonstration") != wx.ID_OK:
                return
            plan = dialog.checked_plan
        finally:
            self._demo_dialog = None
            dialog.Destroy()
        if plan is None:
            return
        try:
            write_json_atomic(app_data_dir() / _PREFS_FILE, preferences_from_plan(plan))
        except OSError:
            pass  # Settings not remembered is not a reason to refuse recording.
        self._begin_demonstration(plan, ffmpeg, caps)

    # -- the 5-second test ----------------------------------------------------------

    # -- starting -------------------------------------------------------------------

    def _take_demo_microphone(self, plan: DemoPlan):
        """The shared microphone lock when the plan records it; ``False`` if refused."""
        if plan.source("microphone") is None:
            return None
        from quill.core.dictation_owner import MicrophoneLock

        lock = MicrophoneLock("studio", key=MICROPHONE_KEY)
        refusal = lock.take()
        if refusal:
            self._announce(refusal)
            return False
        return lock

    @staticmethod
    def _release_demo_microphone(lock) -> None:
        if lock:
            try:
                lock.release()
            except Exception:  # noqa: BLE001 - a lock file we cannot remove times out
                pass

    def _begin_demonstration(self, plan: DemoPlan, ffmpeg: str, caps) -> None:
        from quill.platform.windows.screen_recorder import DemoRecorder

        lock = self._take_demo_microphone(plan)
        if lock is False:
            return
        try:
            recorder = DemoRecorder(
                plan,
                ffmpeg=ffmpeg,
                caps=caps,
                on_event=lambda text, failure: wx.CallAfter(self._demo_event, text, failure),
                on_framing=lambda text: wx.CallAfter(self._demo_face, text),
            )
        except Exception as error:  # noqa: BLE001 - spoken, never raised into wx
            self._release_demo_microphone(lock)
            self._show_message_box(str(error), "Record a demonstration", wx.OK | wx.ICON_ERROR)
            return
        recorder.auto_stop = lambda reason: wx.CallAfter(self.stop_demonstration, reason)
        self._demo_busy = "A recording is starting"
        self._demo_lock = lock
        target_is_studio = plan.window_handle and any(
            int(w.GetHandle()) == plan.window_handle for w in wx.GetTopLevelWindows() if w
        )
        countdown = plan.countdown

        def work(*, cancellation_token, progress_callback, **_kwargs):
            recorder.open_sources()
            for seconds in range(countdown, 0, -1):
                cancellation_token.raise_if_cancelled()
                progress_callback(str(seconds))
                cancellation_token.event.wait(1.0)
            cancellation_token.raise_if_cancelled()
            return None

        def go(_task, _result):
            self._demo_busy = ""
            if plan.screen and not target_is_studio and self.frame.IsShown():
                self.frame.Hide()  # Studio stays out of its own recording.
            self._demo_protect(True)
            self._demo_quiet_start(plan)
            if plan.screen:
                self._exclude_studio_windows(True)
            if plan.source("system") is not None:
                from quill.ui import sound_manager

                self._demo_sounds_were_muted = sound_manager.set_muted(True)
            try:
                recorder.start()
            except Exception as error:  # noqa: BLE001
                self._demo_cleanup(recorder)
                recorder.discard()
                self._announce(f"Recording could not start: {error}")
                return
            self._demo = recorder
            self._demo_title = self.frame.GetTitle()
            self.frame.SetTitle(f"Recording - {self._demo_title}")
            self._update_tray_tooltip(f"Recording: {plan.target_label}")
            self._open_demo_status()
            self._demo_say("Recording started.")

        def failed(_task, error):
            self._demo_busy = ""
            self._release_demo_microphone(lock)
            self._demo_lock = None
            for source in recorder.sources:
                source.close()
            shutil.rmtree(recorder.work, ignore_errors=True)
            self._announce(f"Recording did not start: {error}")

        self._task_manager.submit(
            "Start a demonstration",
            work,
            on_success=go,
            on_failure=failed,
            on_progress=lambda _task, text: self._announce(str(text)),
            ui_lifetime=self._demo_lifetime(),
        )

    def _demo_quiet_start(self, plan: DemoPlan) -> None:
        """Keep awake and Do Not Disturb for the length of the recording (P7)."""
        from quill.platform.windows.focus_guard import DoNotDisturb, KeepAwake

        if plan.keep_awake:
            self._demo_awake = KeepAwake()
            if not self._demo_awake.acquire():
                self._set_status_quiet("Windows did not keep the computer awake.")
        if plan.do_not_disturb:
            self._demo_dnd = DoNotDisturb(app_data_dir())
            problem = self._demo_dnd.start()
            if problem:
                self._demo_say(problem, failure=True)

    def _demo_quiet_stop(self) -> None:
        awake = getattr(self, "_demo_awake", None)
        if awake is not None:
            awake.release()
            self._demo_awake = None
        dnd = getattr(self, "_demo_dnd", None)
        if dnd is not None:
            dnd.stop()
            self._demo_dnd = None

    def _demo_protect(self, on: bool) -> None:
        jobs = getattr(self, "_protected_background_jobs", None)
        if jobs is None:
            return
        if on:
            jobs[_SUPPRESSED] = "Recording a demonstration"
        else:
            jobs.pop(_SUPPRESSED, None)

    def _exclude_studio_windows(self, exclude: bool) -> None:
        from quill.platform.windows.screen_recorder_check import exclude_from_capture

        demo = getattr(self, "_demo", None)
        shown = demo is not None and demo.plan.show_status_window
        visible = getattr(self, "_demo_status", None) if shown else None
        windows = [w for w in wx.GetTopLevelWindows() if w and w is not visible]
        exclude_from_capture([int(w.GetHandle()) for w in windows], exclude)

    def _open_demo_status(self) -> None:
        from quill.ui.studio_demo_status import RecordingStatusFrame

        recorder = self._demo
        frame = RecordingStatusFrame(
            None,
            status=lambda: recorder.status_line(),
            pause=self.pause_demonstration,
            marker=lambda: self.mark_demonstration(ask=True),
            mute=self.mute_demonstration,
            speak_status=self.speak_demonstration_status,
            stop=self.stop_demonstration,
            discard=self.discard_demonstration,
            has_microphone=recorder.plan.source("microphone") is not None,
        )
        self._demo_status = frame
        if recorder.plan.screen:
            self._exclude_studio_windows(True)
        frame.show_quietly()

    def _demo_event(self, sentence: str, failure: bool) -> None:
        self._demo_say(sentence, failure=failure)
        status = getattr(self, "_demo_status", None)
        if status:
            status.refresh()

    def _demo_face(self, sentence: str) -> None:
        if getattr(self, "_demo", None) is None:
            return
        if self._demo_reader_speech_recorded():
            self._set_status_quiet(sentence)  # Marked by the recorder; never spoken into the file.
            return
        self._announce(sentence)

    # -- while recording -------------------------------------------------------------

    def _require_demo(self):
        recorder = getattr(self, "_demo", None)
        if recorder is None:
            self._announce("No demonstration is recording.")
        return recorder

    def pause_demonstration(self) -> None:
        recorder = self._require_demo()
        if recorder is None or getattr(self, "_demo_pausing", False):
            return
        self._demo_pausing = True
        resuming = recorder.state == "paused"

        def work(**_kwargs):
            if resuming:
                recorder.resume()
            else:
                recorder.pause()

        def done(_task, _result):
            self._demo_pausing = False
            status = getattr(self, "_demo_status", None)
            if status:
                status.set_paused(not resuming)
                status.refresh()
            self._demo_say("Recording resumed." if resuming else "Recording paused.")

        def failed(_task, error):
            self._demo_pausing = False
            self._demo_say(str(error), failure=True)

        self._task_manager.submit(
            "Pause or resume a demonstration",
            work,
            on_success=done,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),
        )

    def mark_demonstration(self, ask: bool = False) -> None:
        recorder = self._require_demo()
        if recorder is None:
            return
        label = ""
        if ask:
            dialog = wx.TextEntryDialog(
                getattr(self, "_demo_status", None) or self.frame,
                "Optional label for this marker:",
                "Add marker",
            )
            try:
                if self._show_modal_dialog(dialog, "Add marker") != wx.ID_OK:
                    return
                label = dialog.GetValue().strip()
            finally:
                dialog.Destroy()
        number = len(recorder.markers.markers) + 1
        seconds = recorder.mark(label or f"Marker {number}")
        self._demo_say(f"Marker {number} at {spoken_duration(seconds)}.")

    def mute_demonstration(self) -> None:
        recorder = self._require_demo()
        if recorder is None:
            return
        muted = not recorder.mic_muted
        if not recorder.set_microphone_muted(muted):
            self._announce("The microphone is not part of this recording.")
            return
        status = getattr(self, "_demo_status", None)
        if status:
            status.set_muted(muted)
            status.refresh()
        self._demo_say("Microphone muted in the recording." if muted else "Microphone unmuted.")

    def speak_demonstration_status(self) -> None:
        recorder = getattr(self, "_demo", None)
        if recorder is None:
            busy = getattr(self, "_demo_busy", "")
            self._announce(busy + "." if busy else "No demonstration is recording.")
            return
        # Asked for: spoken even while the reader is recorded, as the user chose to.
        self._announce(recorder.status_line())

    def show_demonstration_window(self) -> None:
        status = getattr(self, "_demo_status", None)
        if not status:
            self._announce("No demonstration is recording.")
            return
        status.Show()
        status.Raise()
        status.text.SetFocus()

    def emergency_stop_demonstration(self) -> None:
        self.stop_demonstration()

    # -- stopping -----------------------------------------------------------------

    # -- recovery -------------------------------------------------------------------
