"""What Quill Converter's commands do: convert, stop, preview, join, split, report.

Split out of :mod:`quill.apps.converter` so the window file stays the window
(GATE-11). Mixed into :class:`~quill.apps.converter.QuillConverterFrame`,
which supplies the queue (``_entries``), the choices on screen, and the shell
(``_announce``, ``_set_status``, ``_show_message_box``, ``frame``).

Every long job runs on a worker thread and reports back through
``wx.CallAfter`` -- the family's threading rule -- and every one can be
stopped: a batch stops before its next file, a Join before its next source.
The file being encoded when you press Stop is allowed to finish, because a
half-written file is worse than a finished one, and the announcement says so.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import wx

from quill.core.audio.convert import (
    BatchResult,
    CancelToken,
    ConversionJob,
    ConversionSpec,
    JobResult,
    OnExisting,
    default_destination,
    plan_jobs,
    run_conversion_batch,
)
from quill.core.audio.effect_recipes import CUSTOM_RECIPE_ID, recipe_by_id, recipe_filters
from quill.core.audio.formats import AUDIO_EXTENSIONS, format_label
from quill.core.audio.presets import preset_by_id, preset_spec

_TITLE = "Quill Converter"


class ConverterActionsMixin:
    """The Converter's commands. See the module docstring for the contract."""

    # -- the recipe on screen ---------------------------------------------------

    def _chosen_format(self) -> str:
        return self._formats[max(0, self._format.GetSelection())]

    def _chosen_preset_id(self) -> str:
        return self._preset_ids[max(0, self._preset.GetSelection())]

    def _chosen_effect_id(self) -> str:
        return self._effect_ids[max(0, self._effect.GetSelection())]

    def current_spec(self) -> ConversionSpec:
        """Format + preset + effects + keep-only-part, as the window says now."""
        fmt = self._chosen_format()
        spec = replace(preset_spec(self._chosen_preset_id()), fmt=fmt)
        effects = recipe_filters(self._chosen_effect_id(), self._settings.custom_effects)
        merged = list(spec.filters)
        merged += [f for f in effects if f not in merged]
        from quill.apps import converter_advanced

        spec = replace(
            spec,
            filters=tuple(merged),
            start_s=self._settings.start_s,
            end_s=self._settings.end_s,
            chapter_source=self._chosen_chapters(),
        )
        return converter_advanced.apply(self, spec)

    def _chosen_chapters(self) -> str:
        return self._chapter_ids[max(0, self._chapters.GetSelection())]

    def describe_choices(self) -> str:
        """One line naming what Convert will do (spoken, and heads the report)."""
        preset = preset_by_id(self._chosen_preset_id())
        effect_id = self._chosen_effect_id()
        if effect_id == CUSTOM_RECIPE_ID:
            from quill.core.audio.effect_recipes import describe_custom

            effect = f"custom effects ({describe_custom(self._settings.custom_effects)})"
        else:
            recipe = recipe_by_id(effect_id)
            effect = recipe.name.lower() if recipe else "no effects"
        part = ""
        if self._settings.start_s or self._settings.end_s:
            until = f" to {self._settings.end_s:g}" if self._settings.end_s else " to the end"
            part = f", keeping {self._settings.start_s:g} seconds{until}"
        from quill.core.audio.chapter_plan import CHAPTER_SOURCES

        chapters = dict(CHAPTER_SOURCES).get(self._chosen_chapters(), "").split(" (")[0]
        return (
            f"{format_label(self._chosen_format()).split(' -- ')[0]}, "
            f"{preset.name if preset else 'default'} preset, {effect}{part}. "
            f"Chapters: {chapters.lower()}"
        )

    def _destination(self) -> Path:
        dest = self._dest.GetValue().strip()
        return Path(dest) if dest else default_destination(self._entries[0][0])

    # -- convert / stop -------------------------------------------------------

    def convert_or_stop(self) -> None:
        """Convert (Ctrl+Enter) -- or, while a batch runs, Stop."""
        if self._busy:
            self.stop_work()
            return
        if not self._entries:
            self._show_message_box("Add some files or a folder first.", _TITLE)
            return
        ffmpeg = self._ffmpeg()
        if ffmpeg is None:
            return
        spec = self.current_spec()
        if spec.copy_video and spec.filters:
            self._announce(
                "Change the container only copies the sound untouched, so effects are skipped."
            )
            spec = replace(spec, filters=())
        dest = self._destination()
        jobs, skipped = plan_jobs(
            self._entries,
            dest,
            spec,
            recurse=self._recurse.GetValue(),
            on_existing=OnExisting(self._settings.on_existing or "rename"),
        )
        notes = self._skip_notes(spec, skipped)
        if not jobs:
            message = "Nothing to convert." + (f" {notes}" if notes else "")
            self._set_status(message)
            self._announce(message)
            return
        self._remember()
        self._run_jobs(ffmpeg, jobs, f"Converting {len(jobs)} file(s)", dest, notes=notes)

    def _skip_notes(self, spec: ConversionSpec, skipped: list[Path]) -> str:
        if not skipped:
            return ""
        if spec.is_video() and all(p.suffix.lower() in AUDIO_EXTENSIONS for p in skipped):
            return (
                f"{len(skipped)} sound file(s) skipped: a video format needs a picture to convert."
            )
        return f"{len(skipped)} file(s) skipped because a file of that name already exists."

    def _run_jobs(
        self, ffmpeg: str, jobs: list[ConversionJob], label: str, dest: Path, *, notes: str = ""
    ) -> None:
        cancel = CancelToken()
        self._begin_work(label, cancel)
        # Video encoders use every core on their own; running several at once
        # only makes each one slower and the machine unresponsive.
        workers = 1 if any(job.spec.is_video() for job in jobs) else 0
        total = len(jobs)
        started = time.monotonic()

        def on_progress(done: int, total_jobs: int, job: ConversionJob) -> None:
            wx.CallAfter(
                self._note_progress,
                f"Converted {done} of {total_jobs}: {job.source.name}",
                done,
                total_jobs,
            )

        def worker() -> None:
            try:
                result = run_conversion_batch(
                    ffmpeg, jobs, workers=workers, on_progress=on_progress, cancel=cancel
                )
            except Exception as error:  # noqa: BLE001 - reported on the UI thread
                result = BatchResult(results=[JobResult(job=jobs[0], ok=False, error=str(error))])
            wx.CallAfter(self._finish_batch, result, total, dest, notes, time.monotonic() - started)

        threading.Thread(target=worker, daemon=True, name="converter-batch").start()

    def _finish_batch(
        self, result: BatchResult, total: int, dest: Path, notes: str, seconds: float
    ) -> None:
        self._end_work()
        summary = result.summary(total)
        if notes:
            summary += f" {notes}"
        if result.failed:
            summary += " Press Ctrl+R for the report."
        self._last_report = self._report_text(result, total, dest, notes, seconds)
        self._last_output = dest
        self._set_status(summary)
        self._announce(summary, force=True)
        if result.converted and self._settings.open_folder_when_done:
            self.open_output_folder()

    def _report_text(
        self, result: BatchResult, total: int, dest: Path, notes: str, seconds: float
    ) -> str:
        lines = [
            f"Conversion report, {time.strftime('%Y-%m-%d %H:%M')}",
            f"Settings: {self.describe_choices()}",
            f"Output folder: {dest}",
            f"Took {int(seconds)} seconds.",
            result.summary(total),
        ]
        if notes:
            lines.append(notes)
        lines.append("")
        for item in result.results:
            if item.skipped:
                lines.append(f"Skipped (stopped): {item.job.source.name}")
            elif item.ok:
                lines.append(f"Converted: {item.job.source.name} -> {item.job.dest.name}")
            else:
                lines.append(f"FAILED: {item.job.source}")
                lines.append(f"  Reason: {item.error}")
        return "\n".join(lines)

    def stop_work(self) -> None:
        if self._cancel is not None:
            self._cancel.cancel()
            self._announce("Stopping after the file in progress.", force=True)

    def _begin_work(self, label: str, cancel: CancelToken) -> None:
        self._busy = True
        self._cancel = cancel
        self._milestone = 0
        self._convert_btn.SetLabel("Stop Converting")
        self._set_status(f"{label} started")
        self._announce(f"{label}. Press Ctrl+Enter or the Stop button to stop.")

    def _end_work(self) -> None:
        self._busy = False
        self._cancel = None
        self._convert_btn.SetLabel("Convert")
        self._refresh_statusbar()

    def _note_progress(self, text: str, current: int, total: int) -> None:
        self._set_status(text)
        pct = int(current * 100 / total) if total else 0
        milestone = pct - pct % 25
        if 0 < milestone < 100 and milestone > self._milestone:
            self._milestone = milestone
            self._announce(f"{milestone} percent")
        if self._tray_icon is not None:
            try:
                icon = self._app_icon or wx.ArtProvider.GetIcon(
                    wx.ART_INFORMATION, wx.ART_OTHER, (16, 16)
                )
                self._tray_icon.SetIcon(icon, f"{_TITLE} -- {text}")
            except Exception:  # noqa: BLE001 - a tooltip must never break a run
                pass

    def _finish_simple(self, message: str, folder: Path) -> None:
        self._end_work()
        self._last_output = folder
        self._last_report = message
        self._set_status(message)
        self._announce(message, force=True)

    # -- preview --------------------------------------------------------------

    def preview(self, *, original: bool) -> None:
        """Play fifteen seconds of the highlighted (or first) file; again stops."""
        if self._previewing:
            self.stop_preview(announce=True)
            return
        source = self._preview_source()
        if source is None:
            self._announce("Add a file to preview first.")
            return
        ffmpeg = self._ffmpeg()
        if ffmpeg is None:
            return
        from quill.core.audio.assemble import render_preview

        spec = self.current_spec()
        if spec.copy_video:
            spec = replace(spec, copy_video=False, filters=())
        what = "the original" if original else "with your settings"
        self._previewing = True
        self._announce(f"Preparing a preview of {source.name}, {what}.")
        out_wav = Path(tempfile.gettempdir()) / f"quill-converter-preview-{os.getpid()}.wav"

        def worker() -> None:
            try:
                render_preview(ffmpeg, source, spec, out_wav, original=original)
                wx.CallAfter(self._play_preview, out_wav, what)
            except Exception as error:  # noqa: BLE001 - said out loud
                wx.CallAfter(self._preview_failed, str(error))

        threading.Thread(target=worker, daemon=True, name="converter-preview").start()

    def _preview_source(self) -> Path | None:
        from quill.core.audio.assemble import join_inputs

        index = self._list.GetSelection()
        entries = self._entries
        if index != wx.NOT_FOUND and 0 <= index < len(entries):
            entries = [entries[index]]
        files = join_inputs(entries, recurse=self._recurse.GetValue())
        return files[0] if files else None

    def _play_preview(self, wav: Path, what: str) -> None:
        if not self._previewing:
            return
        try:
            import winsound

            winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as error:  # noqa: BLE001 - no sound device, or not Windows
            self._preview_failed(f"Could not play the preview: {error}")
            return
        self._announce(f"Playing 15 seconds {what}. Press the same key again to stop.")
        wx.CallLater(16000, self._preview_ended)

    def _preview_ended(self) -> None:
        self._previewing = False

    def _preview_failed(self, reason: str) -> None:
        self._previewing = False
        self._announce(f"Preview failed. {reason}", force=True)

    def stop_preview(self, *, announce: bool = False) -> None:
        self._previewing = False
        try:
            import winsound

            winsound.PlaySound(None, 0)
        except Exception:  # noqa: BLE001 - nothing to stop
            pass
        if announce:
            self._announce("Preview stopped.")

    # -- information ----------------------------------------------------------

    def show_properties(self) -> None:
        """File Properties (Alt+Enter) for the highlighted file."""
        source = self._preview_source()
        if source is None:
            self._announce("Highlight a file in the queue first.")
            return
        from quill.core.audio.media_probe import describe, probe
        from quill.ui.converter_dialogs import show_text

        wx.BeginBusyCursor()
        try:
            text = "\n".join(describe(probe(source)))
        finally:
            wx.EndBusyCursor()
        show_text(self, "File Properties", text)

    def show_report(self) -> None:
        """The last conversion's full report (Ctrl+R)."""
        from quill.ui.converter_dialogs import show_text

        if not self._last_report:
            self._announce("Nothing has been converted yet in this session.")
            return
        show_text(self, "Conversion Report", self._last_report)

    def open_output_folder(self) -> None:
        """Open the folder the last run wrote to (or will write to) in Explorer."""
        folder = self._last_output
        if folder is None:
            if not self._entries and not self._dest.GetValue().strip():
                self._announce("There is no output folder yet.")
                return
            folder = self._destination()
        if not folder.is_dir():
            self._announce(
                "The output folder does not exist yet; it is made by the first conversion."
            )
            return
        try:
            os.startfile(str(folder))  # type: ignore[attr-defined]  # Windows only
        except (AttributeError, OSError) as error:
            self._announce(f"Could not open the folder: {error}")

    # -- background task (for the shared URL-import orchestration) ---------------

    def _run_background_task(
        self,
        label: str,
        work: Any,
        on_success: Any,
        *,
        notify_on_success: bool = False,
        notify_on_error: bool = True,
        notification_category: str = "",
        protect_on_close: bool = False,
    ) -> None:
        """Run ``work(progress)`` off the UI thread; deliver on the UI thread."""
        del notify_on_success, notify_on_error, notification_category, protect_on_close
        self._set_status(f"{label} started")

        def progress(message: str, current: int, total: int) -> None:
            wx.CallAfter(self._note_progress, message or label, current, total)

        def worker() -> None:
            try:
                result = work(progress)
            except Exception as error:  # noqa: BLE001 - surfaced on the UI thread
                wx.CallAfter(self._finish_task, label, error, None, on_success)
                return
            wx.CallAfter(self._finish_task, label, None, result, on_success)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_task(self, label: str, error: Any, result: Any, on_success: Any) -> None:
        if error is not None:
            self._set_status(f"{label} failed")
            self._show_message_box(f"{label} failed.\n\n{error}", label, wx.ICON_ERROR | wx.OK)
            self._refresh_statusbar()
            return
        self._set_status(f"{label} finished")
        try:
            on_success(result)
        finally:
            self._refresh_statusbar()

    def show_context_help(self) -> None:
        from quill.ui import app_context_help

        app_context_help.show_help(self.frame)

    def show_keyboard_shortcuts(self) -> None:
        from quill.apps.converter_menu import shortcut_list
        from quill.ui.converter_dialogs import show_text

        show_text(self, "Keyboard Shortcuts", shortcut_list(self.frame.GetMenuBar()))

    def _show_about(self) -> None:
        self._show_message_box(
            f"{_TITLE} {_version()}\n\n"
            "Convert audio and video between formats -- sound to sound, video to "
            "sound, and video to video -- with presets, effects you can preview, "
            "Join into One File and Split by Chapters. Everything happens on this "
            "computer; nothing is uploaded.\n\n"
            "Includes FFmpeg (LGPL/GPL), yt-dlp (Unlicense) and mutagen (GPL).\n\n"
            "Support: support@community-access.org",
            f"About {_TITLE}",
        )

    # -- single instance: a second launch hands over its files ---------------------

    def _start_ipc_poll(self) -> None:
        """Poll the hand-over queue, so the Explorer verb on ten selected files --
        ten launches -- ends as ten rows in this one window, not nine lost."""
        self._ipc_timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_ipc_timer, self._ipc_timer)
        self._ipc_timer.Start(600)

    def _on_ipc_timer(self, _event: object) -> None:
        from quill.core.ipc import drain_open_requests

        requests = drain_open_requests(slot="converter")
        if not requests:
            return
        paths = [request.path for request in requests if request is not None]
        if paths:
            self.add_paths(paths)
        frame = self.frame
        if not frame.IsShown():
            self._restore_from_tray()
        frame.Iconize(False)
        frame.Raise()
        self._list.SetFocus()

    def queue_downloaded(self, path: Path) -> None:
        """Convert from URL: the downloaded file joins this window's queue."""
        self.add_paths([path], announce=False)
        self._announce(
            f"Downloaded {path.name}. It is in the queue; press Ctrl+Enter to convert it."
        )

    def _ffmpeg(self) -> str | None:
        from quill.core.speech.ffmpeg import find_ffmpeg

        found = find_ffmpeg()
        if found is None:
            self._show_message_box(
                "Quill Converter cannot find FFmpeg, which does the converting. It is "
                "normally installed with the app; Help > Get FFmpeg puts it back.",
                _TITLE,
            )
        return found


def _version() -> str:
    from quill.apps.converter import _VERSION

    return _VERSION
