"""Record a Demonstration: stopping, discarding, the result, recovery and shutdown.

Split from :mod:`quill.apps.studio_demo` (GATE-11).
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

import wx

from quill.core.demo_recording_session import find_unfinished
from quill.core.demo_unfinished import Unfinished, describe_unfinished
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_log = logging.getLogger(__name__)

#: The unfinished recordings last *said* at launch, so the same set is spoken
#: once and then only written to the status bar (FUX-05).
_RECOVERY_SAID_FILE = "studio_unfinished_said.json"


def _not_finished(item: Unfinished) -> str:
    """A recovery that failed: the recording by name, never a path or exception text."""
    return (
        f"{item.name} could not be finished. Its recorded pieces are kept; Capture, "
        "Recover unfinished recordings tries again or discards them."
    )


class StudioDemoFinishMixin:
    def _demo_cleanup(self, recorder) -> None:
        self._demo_quiet_stop()
        status = getattr(self, "_demo_status", None)
        self._demo_status = None
        if status:
            status.finish()
        self._exclude_studio_windows(False)
        title = getattr(self, "_demo_title", "")
        if title:
            self.frame.SetTitle(title)
        self._demo_title = ""
        self._refresh_statusbar()
        if hasattr(self, "_demo_sounds_were_muted"):
            from quill.ui import sound_manager

            sound_manager.set_muted(self._demo_sounds_were_muted)
            del self._demo_sounds_were_muted
        self._demo_protect(False)

    def stop_demonstration(self, reason: str = "") -> None:
        recorder = getattr(self, "_demo", None)
        if recorder is None:
            if not reason:
                self._announce("No demonstration is recording.")
            return
        self._demo = None
        self._demo_cleanup(recorder)
        self._demo_busy = "The demonstration is being saved"
        lock = getattr(self, "_demo_lock", None)
        self._demo_lock = None
        protected = getattr(self, "_protected_background_jobs", {})
        protected["studio-demo-save"] = "Saving a demonstration"
        self._announce_settled(
            (reason + " " if reason else "Recording stopped. ") + "Saving and checking it."
        )

        def work(*, cancellation_token, **_kwargs):
            try:
                return recorder.finish(cancellation_token)
            finally:
                self._release_demo_microphone(lock)

        def done(_task, verification):
            protected.pop("studio-demo-save", None)
            self._demo_busy = ""
            self._show_demo_result(verification)

        def failed(_task, error):
            protected.pop("studio-demo-save", None)
            self._demo_busy = ""
            self._restore_from_tray()
            self._announce(f"The demonstration could not be saved: {error}")
            self._show_message_box(str(error), "Record a demonstration", wx.OK | wx.ICON_ERROR)

        self._task_manager.submit(
            "Save a demonstration",
            work,
            on_success=done,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),
        )

    def discard_demonstration(self) -> None:
        recorder = self._require_demo()
        if recorder is None:
            return
        answer = self._show_message_box(
            "Delete this recording? Everything recorded so far is removed and cannot be recovered.",
            "Discard this recording",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if answer not in (wx.YES, wx.ID_YES):
            return
        self._demo = None
        self._demo_cleanup(recorder)
        lock = getattr(self, "_demo_lock", None)
        self._demo_lock = None

        def work(**_kwargs):
            recorder.discard()

        def done(_task, _result):
            self._release_demo_microphone(lock)
            self._announce_settled("Recording discarded.")

        def failed(_task, error):
            self._release_demo_microphone(lock)
            self._announce(f"The recording was stopped but not fully deleted: {error}")

        self._task_manager.submit(
            "Discard a demonstration",
            work,
            on_success=done,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),
        )

    def _show_demo_result(self, verification, *, title: str = "", temporary: Path | None = None):
        from quill.ui.studio_demo_result import DemoResultDialog

        path = Path(verification.path)
        self._studio_last_verification = verification  # Ask's "Last recording check"
        self._restore_from_tray()
        self._announce(verification.sentence)
        from quill.ui.outcome_report import keep_outcome  # reachable after the window (FUX-04)

        keep_outcome(
            "Record a demonstration", verification.sentence, object_name=path.name, path=path
        )
        lines = [verification.state, "", verification.sentence, "", "Checks:"]
        lines += [
            f"- {'Passed' if check.passed else 'Problem'}: {check.name}. {check.detail}"
            for check in verification.checks
        ]
        lines += ["", f"File: {path}", f"SHA-256: {verification.sha256}"]

        def play():
            os.startfile(str(path))  # noqa: S606 - the user's own video in their player

        def open_folder():
            from quill.stability.safe_subprocess import run_subprocess_safely

            try:
                run_subprocess_safely(["explorer.exe", f"/select,{path}"], timeout_seconds=10)
            except Exception:  # noqa: BLE001 - explorer returns 1 even on success
                pass

        def copy_path():
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(str(path)))
                finally:
                    wx.TheClipboard.Close()
                self._announce("Path copied.")

        dialog = DemoResultDialog(
            self.frame,
            "\n".join(lines),
            play=play,
            open_folder=open_folder,
            copy_path=copy_path,
            inspect_frame=None
            if temporary or path.suffix.lower() != ".mp4"
            else (lambda: self._inspect_demo_frame(path)),
            title=title or f"Demonstration: {verification.state}",
            ask_ai=None
            if temporary or path.suffix.lower() != ".mp4"
            else (lambda: wx.CallAfter(self.ask_ai_about_video, str(path))),
            make_captions=None
            if temporary
            else (lambda: wx.CallAfter(self._caption_recording, path)),
            make_video=None
            if temporary or path.suffix.lower() == ".mp4"
            else (lambda: wx.CallAfter(self.make_picture_video, str(path))),
        )
        try:
            self._show_modal_dialog(dialog, dialog.GetTitle())
        finally:
            dialog.Destroy()
            if temporary is not None:
                shutil.rmtree(temporary, ignore_errors=True)

    def _caption_recording(self, path: Path) -> None:
        from quill.ui.audio_studio.captions_command import generate_captions

        generate_captions(self, source=path)

    def _inspect_demo_frame(self, video: Path) -> None:
        from quill.core.studio_capture import verify_capture
        from quill.stability.safe_subprocess import run_subprocess_safely

        ffmpeg = self._demo_ffmpeg()
        folder = app_data_dir() / "studio-captures"
        folder.mkdir(parents=True, exist_ok=True)
        frame = folder / f"{video.stem} - frame.png"
        middle = 0.0
        try:
            from quill.core.speech.ffmpeg import probe_duration_ms

            middle = probe_duration_ms(video) / 2000
        except Exception:  # noqa: BLE001 - the first frame is still a frame
            middle = 0.0
        try:
            run_subprocess_safely(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{middle:.2f}",
                    "-i",
                    str(video),
                    "-frames:v",
                    "1",
                    "-update",
                    "1",
                    str(frame),
                ],
                timeout_seconds=60,
            )
            evidence = verify_capture(frame, f"Frame from {video.name}")
        except Exception as error:  # noqa: BLE001
            self._announce(f"No frame could be taken from the video: {error}")
            return
        self._last_capture = evidence
        self._review_capture(evidence)

    def _demo_folders(self) -> list[Path]:
        folders = [self._demo_default_folder()]
        saved = str(self._demo_preferences().get("folder") or "")
        if saved and Path(saved) not in folders:
            folders.append(Path(saved))
        return folders

    def _offer_demo_recovery(self) -> None:
        """At launch: name the unfinished recordings once; never open a modal.

        Said aloud the first time a set of unfinished recordings is found, then
        only written to the status bar on later launches, so a recording left
        for later is not announced at every start. Capture, Recover unfinished
        recordings is always the way back to it.
        """
        try:
            from quill.platform.windows.focus_guard import restore_after_crash

            if restore_after_crash(app_data_dir()):
                self._set_status_quiet(
                    "Do Not Disturb was put back after an interrupted recording."
                )
        except Exception:  # noqa: BLE001 - never disturb a launch
            pass
        try:
            found = [describe_unfinished(work) for work in find_unfinished(self._demo_folders())]
        except Exception:  # noqa: BLE001 - recovery must never disturb a launch
            _log.warning("could not look for unfinished recordings", exc_info=True)
            return
        waiting = [item for item in found if item.needs_finishing]
        if not waiting:
            return
        noun = (
            "an unfinished recording"
            if len(waiting) == 1
            else f"{len(waiting)} unfinished recordings"
        )
        sentence = (
            f"Studio found {noun}: {'; '.join(item.label for item in waiting)}. "
            "Capture, Recover unfinished recordings finishes or discards "
            f"{'it' if len(waiting) == 1 else 'them'}."
        )
        said = app_data_dir() / _RECOVERY_SAID_FILE
        names = sorted(item.work.name for item in waiting)
        if read_json(said, None) == names:
            self._set_status_quiet(sentence)
            return
        self._set_status(sentence)
        try:
            write_json_atomic(said, names)
        except OSError:
            pass  # said again next launch: the harmless direction to fail

    def _ask_unfinished(self, item: Unfinished) -> str:
        """``"finish"``, ``"discard"`` or ``"skip"`` for one unfinished recording."""
        if item.needs_finishing:
            where = f" in {item.output.parent.name}" if item.output is not None else ""
            message = (
                f"{item.label}.\n\n"
                f"Finish joins, checks and saves it as {item.name}{where}. "
                "Discard deletes what was recorded. Skip leaves it for later."
            )
            labels = ("&Finish", "&Discard...", "&Skip")
            style = wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_QUESTION
        else:
            message = (
                f"{item.label}.\n\nIts recorded pieces are still kept. Discard deletes "
                "those pieces; "
                + ("the saved file stays. " if item.saved is not None else "")
                + "Skip leaves them for later."
            )
            labels = ("", "&Discard...", "&Skip")
            style = wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        dialog = wx.MessageDialog(self.frame, message, "Recover unfinished recordings", style)
        if labels[0]:
            dialog.SetYesNoCancelLabels(labels[0], labels[1], labels[2])
        else:
            dialog.SetYesNoLabels(labels[1], labels[2])
        try:
            answer = self._show_modal_dialog(dialog, "Recover unfinished recordings")
        finally:
            dialog.Destroy()
        if labels[0]:
            return {wx.ID_YES: "finish", wx.ID_NO: "discard"}.get(answer, "skip")
        return "discard" if answer == wx.ID_YES else "skip"

    def _discard_unfinished(self, item: Unfinished) -> None:
        """Delete one unfinished recording's pieces, after a confirmation that says so."""
        answer = self._show_message_box(
            f"Delete the recorded pieces of {item.name}? They do not go to the Recycle Bin "
            "and cannot be recovered."
            + (f" The saved file {item.saved.name} is not touched." if item.saved else ""),
            "Discard an unfinished recording",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if answer not in (wx.YES, wx.ID_YES):
            self._announce(f"{item.name} is kept.")
            return
        shutil.rmtree(item.work, ignore_errors=True)
        if item.work.exists():
            self._announce(f"{item.name} could not be fully deleted. Try again later.")
        else:
            self._announce(f"Discarded {item.name}.")

    def recover_demonstrations(self) -> None:
        if getattr(self, "_demo", None) is not None or getattr(self, "_demo_busy", ""):
            self._announce("Finish the current recording first.")
            return
        items = [describe_unfinished(work) for work in find_unfinished(self._demo_folders())]
        if not items:
            self._announce("No unfinished recordings were found.")
            return
        to_finish: list[Unfinished] = []
        for item in items:
            choice = self._ask_unfinished(item)
            if choice == "discard":
                self._discard_unfinished(item)
            elif choice == "finish" and item.needs_finishing:
                to_finish.append(item)
        if not to_finish:
            return
        ffmpeg = self._demo_ffmpeg()
        if not ffmpeg:
            self._announce("Recovering a recording needs FFmpeg. Use Voices, Get FFmpeg.")
            return
        caps = self._demo_caps(ffmpeg)
        self._demo_busy = "Unfinished recordings are being recovered"

        def work(*, cancellation_token, **_kwargs):
            from quill.platform.windows.screen_recorder_finish import finalize

            results = []
            for item in to_finish:
                try:
                    results.append(
                        finalize(
                            item.work, ffmpeg=ffmpeg, caps=caps, cancellation=cancellation_token
                        )
                    )
                except Exception as error:  # noqa: BLE001 - one bad folder never stops the rest
                    _log.warning("could not finish %s: %s", item.work, error)
                    results.append(item)
            return results

        def done(_task, results: list[Any]):
            self._demo_busy = ""
            for result in results:
                if isinstance(result, Unfinished):
                    self._announce(_not_finished(result))
                else:
                    self._show_demo_result(result, title=f"Recovered: {result.state}")

        def failed(_task, error):
            self._demo_busy = ""
            _log.warning("recovering demonstrations failed: %s", error)
            self._announce(
                "The unfinished recordings could not be finished. Their recorded pieces are "
                "kept; Capture, Recover unfinished recordings tries again."
            )

        self._task_manager.submit(
            "Recover demonstrations",
            work,
            on_success=done,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),
        )

    def _demo_shutdown(self) -> None:
        """On exit mid-recording: close the segment so the next launch can recover it."""
        self._stream_shutdown()
        recorder = getattr(self, "_demo", None)
        if recorder is None:
            return
        self._demo = None
        try:
            recorder.stop_capture()
        except Exception:  # noqa: BLE001 - shutting down regardless
            pass
        self._demo_cleanup(recorder)
        self._release_demo_microphone(getattr(self, "_demo_lock", None))
