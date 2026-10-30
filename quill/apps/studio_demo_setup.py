"""Record a Demonstration's setup helpers: the check, the test, camera and sounds.

Split from :mod:`quill.apps.studio_demo` (GATE-11). The setup dialog calls
these through its :class:`~quill.ui.studio_demo_dialog.DemoCallbacks`.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

import wx

from quill.core.demo_recording import MICROPHONE_KEY, DemoPlan, can_start, preflight, summary


class StudioDemoSetupMixin:
    def _choose_demo_folder(self, parent: wx.Window, current: str) -> str | None:
        dialog = wx.DirDialog(parent, "Choose the save folder", current)
        try:
            if self._show_modal_dialog(dialog, "Choose the save folder") == wx.ID_OK:
                return dialog.GetPath()
            return None
        finally:
            dialog.Destroy()

    def _choose_program(self):
        from quill.platform.windows.audio_sessions import AudioSessionError, list_sessions

        try:
            sessions = [s for s in list_sessions() if s.process_id not in (0, os.getpid())]
        except AudioSessionError as error:
            self._announce(str(error))
            return None
        if not sessions:
            self._announce("No other program has a sound session now. Start its sound first.")
            return None
        dialog = wx.SingleChoiceDialog(
            self.frame,
            "Programs with sound. Choose one to add as its own sound source.",
            "Add a program's sound",
            [f"{s.name}, {'playing now' if s.peak > 0.001 else 'quiet'}" for s in sessions],
        )
        try:
            if self._show_modal_dialog(dialog, "Add a program's sound") != wx.ID_OK:
                return None
            chosen = sessions[dialog.GetSelection()]
            return chosen.process_id, chosen.name
        finally:
            dialog.Destroy()

    def _demo_check_context(self, plan: DemoPlan, ffmpeg: str, caps):
        from quill.core.dictation_owner import MicrophoneLock
        from quill.platform.windows.screen_recorder_check import CheckContext

        holder = ""
        if plan.source("microphone") is not None:
            holder = MicrophoneLock("studio", key=MICROPHONE_KEY).busy()
        handles = [int(w.GetHandle()) for w in wx.GetTopLevelWindows() if w]
        return CheckContext(
            ffmpeg,
            caps,
            self._recording_hotkeys_assigned(),
            handles,
            microphone_holder=holder,
            camera_guidance=getattr(self, "_demo_camera_advice", "") if plan.camera.enabled else "",
        )

    def _run_demo_check(self, plan: DemoPlan, done, ffmpeg: str, caps) -> None:
        context = self._demo_check_context(plan, ffmpeg, caps)

        def work(**_kwargs):
            from quill.platform.windows.screen_recorder_check import gather_facts

            scratch = Path(tempfile.mkdtemp(prefix="studio-demo-check-"))
            try:
                facts = gather_facts(plan, context, scratch)
            finally:
                shutil.rmtree(scratch, ignore_errors=True)
            findings = preflight(plan, facts)
            return summary(plan, findings), can_start(findings)

        def ready(_task, result):
            text, ok = result
            done(text, ok)

        def failed(_task, error):
            done(f"Stop: the check could not run: {error}", False)

        self._task_manager.submit(
            "Check a demonstration",
            work,
            on_success=ready,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),
        )

    def _camera_check_dialog(self, ffmpeg: str, device: str, mirrored: bool) -> None:
        from quill.ui.studio_demo_camera import CameraCheckDialog

        dialog = CameraCheckDialog(
            self._demo_dialog or self.frame,
            ffmpeg,
            device,
            mirrored=mirrored,
            announce=self._announce,
        )
        try:
            self._show_modal_dialog(dialog, "Check camera framing")
            self._demo_camera_advice = dialog.latest()
            if self._demo_dialog is not None and dialog.mirrored != mirrored:
                self._demo_dialog.mirrored.SetValue(dialog.mirrored)
        finally:
            dialog.Destroy()

    def check_camera_framing(self) -> None:
        ffmpeg = self._demo_ffmpeg()
        if not ffmpeg:
            self._announce("Checking the camera needs FFmpeg. Use Voices, Get FFmpeg.")
            return
        from quill.platform.windows.demo_media import list_cameras

        cameras = list_cameras(ffmpeg)
        if not cameras:
            self._announce("No camera was found.")
            return
        camera = self._demo_preferences().get("camera", {})
        camera = camera if isinstance(camera, dict) else {}
        device = str(camera.get("device", ""))
        self._camera_check_dialog(
            ffmpeg, device if device in cameras else cameras[0], bool(camera.get("mirrored"))
        )

    def open_mixer(self) -> None:
        from quill.ui.studio_mixer import StudioMixerDialog

        parent = getattr(self, "_demo_dialog", None) or self.frame
        dialog = StudioMixerDialog(parent, announce=self._announce)
        try:
            self._show_modal_dialog(dialog, "Studio Mixer")
        finally:
            dialog.Destroy()

    def _run_demo_test(self, plan: DemoPlan, ffmpeg: str, caps) -> None:
        if getattr(self, "_demo", None) is not None or getattr(self, "_demo_busy", ""):
            self._announce("A recording is already running.")
            return
        lock = self._take_demo_microphone(plan)
        if lock is False:
            return
        folder = Path(tempfile.mkdtemp(prefix="studio-demo-test-"))
        test_plan = replace(plan, folder=str(folder), countdown=0, keep_stems=False)
        self._demo_busy = "A test recording is running"
        self._announce("Recording a 5-second test.")

        def work(*, cancellation_token, **_kwargs):
            from quill.platform.windows.screen_recorder import DemoRecorder

            recorder = DemoRecorder(test_plan, ffmpeg=ffmpeg, caps=caps, on_event=lambda *_a: None)
            recorder.open_sources()
            recorder.start()
            cancellation_token.event.wait(5.0)
            return recorder.finish(cancellation_token)

        def finished(_task, verification):
            self._release_demo_microphone(lock)
            self._demo_busy = ""
            self._show_demo_result(verification, title="Test recording", temporary=folder)

        def failed(_task, error):
            self._release_demo_microphone(lock)
            self._demo_busy = ""
            shutil.rmtree(folder, ignore_errors=True)
            self._announce(f"The test recording failed: {error}")

        self._task_manager.submit(
            "Test recording",
            work,
            on_success=finished,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),
        )
