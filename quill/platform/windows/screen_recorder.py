"""Record a Demonstration: the running session, its checks and its finish.

The plan and every rule are in :mod:`quill.core.demo_recording`; this module
does the work on Windows -- gathers the facts the spoken check judges, runs
FFmpeg for the screen and camera, runs the sound sources, watches for the
REC-015 failures while recording, and on Stop joins, mixes, checks and
reports the file. Nothing here touches wx: the Studio mixin calls in from a
task-manager worker and hears back through ``on_event`` callbacks.

A recording lives in a hidden ``.studio-recording-<id>`` folder beside the
output until the final file passes its check. ``session.json`` there is
rewritten at every segment boundary and marker, so a crash or power cut
leaves everything needed for :func:`finalize` to finish it on next launch.
"""

from __future__ import annotations

import ctypes
import logging
import shutil
import threading
import time
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from quill.core.demo_camera import FirstFrameGrace, Framing, FramingAnnouncer
from quill.core.demo_recording import (
    LOW_SPACE_STOP_BYTES,
    DemoPlan,
    DemoRecordingError,
    MarkerLog,
    demo_file_name,
    format_timestamp,
    minutes_left,
    unique_path,
)
from quill.core.demo_recording_ffmpeg import (
    FACE_FRAME_SIZE,
    Capabilities,
    camera_capture_command,
    screen_capture_command,
)
from quill.core.demo_recording_session import (
    SegmentRecord,
    SessionRecord,
    plan_to_dict,
    work_folder,
)
from quill.core.demo_recording_verify import (
    Verification,
)
from quill.platform.windows.demo_audio import make_source
from quill.platform.windows.demo_media import (
    FaceWatcher,
    FFmpegProcess,
    free_bytes,
)
from quill.platform.windows.screen_recorder_check import choose_backend
from quill.platform.windows.screen_recorder_finish import finalize

logger = logging.getLogger(__name__)

EventCallback = Callable[[str, bool], None]  # (sentence, is_failure)
_WDA_NONE = 0
_WDA_EXCLUDEFROMCAPTURE = 0x11
_MONITOR_S = 1.0
_LOW_SPACE_WARN_MINUTES = 2.0
_DROP_WARN = 0.05


# -- displays and the capture backend -----------------------------------------------


# -- the spoken check's facts -------------------------------------------------------


# -- the running session ------------------------------------------------------------


class DemoRecorder:
    """One recording from Start to Stop and save (or Discard)."""

    def __init__(
        self,
        plan: DemoPlan,
        *,
        ffmpeg: str,
        caps: Capabilities,
        on_event: EventCallback,
        on_framing: Callable[[str], None] | None = None,
        when: datetime | None = None,
    ) -> None:
        self.plan, self.backend = choose_backend(plan, caps) if plan.screen else (plan, "")
        if plan.screen and not self.backend:
            raise DemoRecordingError("No screen grabber is available in this FFmpeg.")
        self.ffmpeg = ffmpeg
        self.caps = caps
        self.on_event = on_event
        self.on_framing = on_framing
        folder = Path(plan.folder)
        folder.mkdir(parents=True, exist_ok=True)
        self.output = unique_path(
            folder / demo_file_name(plan.name_label, when or datetime.now(), plan.extension)
        )
        self.work = work_folder(self.output, uuid.uuid4().hex[:12])
        self.work.mkdir(parents=True)
        _hide(self.work)
        self.session = SessionRecord(
            plan=plan_to_dict(self.plan),
            output=str(self.output),
            started=datetime.now().isoformat(),
        )
        self.markers = MarkerLog()
        # Each source reports through its own callback, so a failure is held
        # against that source by name (REC-024).
        self.sources = [
            make_source(
                source,
                self._source_callback(source.label),
                studio_pid=plan.studio_process_id,
            )
            for source in self.plan.enabled_sources()
        ]
        self.state = "idle"
        self.mic_muted = False
        self._screen: FFmpegProcess | None = None
        self._camera: FFmpegProcess | None = None
        self._faces: FaceWatcher | None = None
        self._face_announcer = FramingAnnouncer(coarse=True)
        self._segment: SegmentRecord | None = None
        self._segment_wall = 0.0
        self._closed_seconds = 0.0
        self._dropped = 0
        self._frames = 0
        self._lock = threading.RLock()
        self._stop_monitor = threading.Event()
        self._monitor: threading.Thread | None = None
        self._warned: set[str] = set()
        #: Streams that failed in the open segment, so each is reported once.
        self._failed_now: set[str] = set()
        self.stop_reason = ""
        self.auto_stop: Callable[[str], None] | None = None

    # -- events -----------------------------------------------------------------

    def _source_callback(self, name: str) -> EventCallback:
        def report(sentence: str, failure: bool) -> None:
            self._source_event(sentence, failure, stream=name)

        return report

    def _source_event(self, sentence: str, failure: bool, *, stream: str = "") -> None:
        if failure:
            self.mark(sentence, failure=True)
            if stream:
                self._note_failure(stream, sentence)
        self.on_event(sentence, failure)

    def _note_failure(self, stream: str, reason: str) -> None:
        """Hold *reason* against *stream* for the check (REC-024); the first one wins."""
        with self._lock:
            self._failed_now.add(stream)
            self.session.stream_failures.setdefault(stream, reason)
            self._save()

    def _stream_failed(self, stream: str, sentence: str) -> None:
        """*stream* stopped; say so by name, once, and let every other stream go on."""
        if stream in self._failed_now:
            return
        self._note_failure(stream, sentence)
        self.mark(sentence, failure=True)
        self.on_event(sentence, True)

    def _others_recording(self, stream: str) -> bool:
        """Whether anything but *stream* is still capturing."""
        if any(source.label not in self._failed_now for source in self.sources):
            return True
        pictures = {"Screen": self._screen, "Camera": self._camera}
        return any(
            process is not None and process.running
            for name, process in pictures.items()
            if name != stream
        )

    def _warn_once(self, key: str, sentence: str, *, failure: bool = True) -> None:
        if key in self._warned:
            return
        self._warned.add(key)
        self.mark(sentence, failure=failure)
        self.on_event(sentence, failure)

    # -- lifecycle --------------------------------------------------------------

    def open_sources(self) -> None:
        """Open every source before the countdown ends, so none starts late."""
        problems = []
        for source in self.sources:
            error = source.open()
            if error:
                problems.append(f"{source.label}: {error}")
        if problems:
            for source in self.sources:
                source.close()
            raise DemoRecordingError("A sound source could not be opened. " + "; ".join(problems))

    def start(self) -> None:
        with self._lock:
            if self.state != "idle":
                raise DemoRecordingError("This recording has already started.")
            self._start_segment()
            self.state = "recording"
            self._save()
        self._monitor = threading.Thread(target=self._watch, daemon=True, name="demo-monitor")
        self._monitor.start()

    def _start_segment(self) -> None:
        index = len(self.session.segments) + 1
        folder = self.work / f"seg-{index:03d}"
        folder.mkdir()
        segment = SegmentRecord(index, str(folder))
        # The segment's own clock: a sound-only recording aligns its sources to this.
        self._segment_wall = time.time()
        self._failed_now = set()
        for source in self.sources:
            source.begin_segment(folder / f"{source.source.source_id}.wav")
        encoder = self.caps.h264_encoder
        if self.plan.screen:
            self._screen = FFmpegProcess(
                screen_capture_command(
                    self.ffmpeg,
                    self.plan,
                    folder / "video.mkv",
                    backend=self.backend,
                    encoder=encoder,
                ),
                log_path=folder / "ffmpeg-screen.log",
            )
            self._screen.launch()
        if self.plan.camera.enabled:
            alerts = self.plan.camera.face_alerts
            width, height = FACE_FRAME_SIZE
            if alerts and self._faces is None:
                self._faces = FaceWatcher(self._framing, mirrored=self.plan.camera.mirrored)
                self._faces.start()
            if self._faces is not None:
                # VIDEO-003: every launch of the camera starts its own grace,
                # counted from the frames this launch actually delivers.
                grace = FirstFrameGrace()
                self._faces.grace = self._face_announcer.grace = grace
            self._camera = FFmpegProcess(
                camera_capture_command(
                    self.ffmpeg,
                    self.plan.camera.device,
                    folder / "camera.mkv",
                    fps=self.plan.fps,
                    encoder=encoder,
                    face_frames=alerts,
                ),
                log_path=folder / "ffmpeg-camera.log",
                on_frame=self._faces.feed if (alerts and self._faces) else None,
                frame_bytes=width * height,
            )
            try:
                self._camera.launch()
            except OSError as error:
                # REC-024: no camera is no reason not to record the rest.
                self._camera = None
                self._stream_failed("Camera", f"The camera could not start: {error}.")
        self._segment = segment
        self.session.segments.append(segment)

    def _framing(self, result: Framing) -> None:
        sentence = self._face_announcer.feed(result)
        if sentence is None:
            return
        if not result.in_view:
            self.mark("Face out of camera view")
        if self.on_framing is not None:
            self.on_framing(sentence)

    def _close_segment(self) -> None:
        segment = self._segment
        if segment is None:
            return
        end = time.time()
        screen, camera = self._screen, self._camera
        # The picture's clock is the screen, or the camera when it fills the
        # picture; with no picture it is the segment's own start.
        main = screen if screen is not None else camera
        main_name = "Screen" if screen is not None else "Camera"
        # REC-024: each stream is stopped on its own, so one that fails to
        # close cannot leave the next one unfinished.
        for name, process in (("Screen", screen), ("Camera", camera)):
            if process is None:
                continue
            try:
                process.stop()
            except Exception as error:  # noqa: BLE001 - the other streams still close
                logger.exception("Stopping the %s capture failed", name)
                self._note_failure(name, f"{name} capture did not close cleanly: {error}.")
        if camera is not None:
            segment.camera_start = camera.start.start or camera.launched
        if main is not None:
            stats = main.last_stats
            segment.video_start = main.start.start or main.launched
            if stats is not None:
                self._dropped += stats.dropped
                self._frames += stats.frames
            segment.duration = max(0.0, (stats.seconds if stats else 0.0))
            if not segment.duration or main_name in self._failed_now:
                # A picture that stopped early does not cut the sound short:
                # the segment lasts as long as the streams that kept going.
                segment.duration = max(segment.duration, end - segment.video_start)
        else:
            segment.video_start = self._segment_wall
            segment.duration = max(0.0, end - self._segment_wall)
        stop_at = segment.video_start + segment.duration
        for source in self.sources:
            try:
                stream = source.end_segment(stop_at)
            except Exception as error:  # noqa: BLE001 - the other sources still close
                logger.exception("Closing %s failed", source.label)
                self._note_failure(source.label, f"{source.label} did not close cleanly: {error}.")
                continue
            if stream is not None:
                segment.audio_starts[source.source.source_id] = stream.first_time or stop_at
        segment.closed = True
        self._closed_seconds += segment.duration
        self._segment = None
        self._screen = self._camera = None
        self._save()

    def pause(self) -> None:
        with self._lock:
            if self.state != "recording":
                raise DemoRecordingError("Nothing is recording to pause.")
            self._close_segment()
            self.state = "paused"
            self.session.state = "paused"
            self._save()

    def resume(self) -> None:
        with self._lock:
            if self.state != "paused":
                raise DemoRecordingError("The recording is not paused.")
            self._check_target_still_there()
            self._start_segment()
            self.state = "recording"
            self.session.state = "recording"
            self._save()

    def _check_target_still_there(self) -> None:
        if self.plan.screen and self.plan.target_kind == "window":
            if not ctypes.windll.user32.IsWindow(ctypes.c_void_p(self.plan.window_handle)):
                raise DemoRecordingError("The recorded window has closed. Stop and save instead.")

    def elapsed(self) -> float:
        with self._lock:
            if self._segment is not None:
                return self._closed_seconds + max(0.0, time.time() - self._segment_wall)
            return self._closed_seconds

    def mark(self, label: str, *, failure: bool = False) -> float:
        seconds = self.elapsed()
        with self._lock:
            self.markers.add(seconds, label, failure=failure)
            self.session.markers = [
                {"seconds": m.seconds, "label": m.label, "failure": m.failure}
                for m in self.markers.markers
            ]
            self._save()
        return seconds

    def set_microphone_muted(self, muted: bool) -> bool:
        mic = next((s for s in self.sources if s.source.kind == "microphone"), None)
        if mic is None:
            return False
        mic.set_muted(muted)
        self.mic_muted = muted
        self.mark("Microphone muted" if muted else "Microphone unmuted")
        return True

    def status_line(self) -> str:
        state = {"recording": "Recording", "paused": "Paused"}.get(self.state, self.state.title())
        live = [
            s.label for s in self.sources if not (s.source.kind == "microphone" and self.mic_muted)
        ]
        reader = "in" if self.plan.source("screen_reader") is not None else "out"
        parts = [f"{state}, {format_timestamp(self.elapsed())[:-2]}"]
        parts.append("sound: " + (", ".join(live) if live else "none"))
        if self.mic_muted:
            parts.append("microphone muted")
        parts.append(f"screen reader {reader}")
        dropped = self._dropped + (
            self._screen.last_stats.dropped if self._screen and self._screen.last_stats else 0
        )
        parts.append(f"{dropped} dropped frames")
        free = free_bytes(self.output.parent)
        if free >= 0:
            parts.append(f"about {int(minutes_left(free, self.plan))} minutes of space left")
        return "; ".join(parts) + "."

    def _save(self) -> None:
        try:
            self.session.save(self.work)
        except OSError:
            logger.exception("Could not save the recording session file")

    # -- watching for REC-015 failures ----------------------------------------------

    def _watch(self) -> None:
        while not self._stop_monitor.wait(_MONITOR_S):
            try:
                self._check_once()
            except Exception:  # noqa: BLE001 - the watcher must never end a recording
                logger.exception("Demonstration monitor check failed")

    def _check_once(self) -> None:
        with self._lock:
            if self.state != "recording":
                return
            screen = self._screen
        # REC-024: a picture stream that dies is reported by name and the rest
        # keep recording; the recording stops only when nothing is left.
        for name, process in (("Screen", screen), ("Camera", self._camera)):
            if process is None or process.running or process.stopping:
                continue
            if name in self._failed_now:
                continue
            detail = process.tail[-1] if process.tail else f"exit code {process.returncode}"
            if not self._others_recording(name):
                self._note_failure(name, f"{name} capture stopped: {detail}.")
                self._request_stop(f"{name} capture stopped unexpectedly: {detail}")
                return
            self._stream_failed(
                name, f"{name} capture stopped: {detail}. The rest is still recording."
            )
        if not self.plan.screen:
            pass
        elif self.plan.target_kind == "window":
            user32 = ctypes.windll.user32
            handle = ctypes.c_void_p(self.plan.window_handle)
            if not user32.IsWindow(handle):
                self._request_stop(
                    "The recorded window closed, so the recording was stopped and saved."
                )
                return
            if user32.IsIconic(handle):
                self._warn_once(
                    "minimized",
                    "The recorded window is minimized; its area shows whatever is behind it.",
                )
            else:
                self._warned.discard("minimized")
        elif not self._displays_unchanged():
            with self._lock:
                if self.state == "recording":
                    self.pause()
            self.mark("Display layout changed", failure=True)
            self.on_event(
                "The display layout changed, so the recording paused. Resume or stop.", True
            )
            return
        free = free_bytes(self.output.parent)
        if 0 <= free < LOW_SPACE_STOP_BYTES:
            self._request_stop("Disk space ran out, so the recording was stopped and saved.")
            return
        if free >= 0 and minutes_left(free, self.plan) < _LOW_SPACE_WARN_MINUTES:
            self._warn_once("space", "Disk space is low: about 2 minutes of recording left.")
        stats = screen.last_stats if screen else None
        if stats is not None and stats.frames > self.plan.fps * 10:
            if stats.dropped / max(1, stats.frames) > _DROP_WARN:
                self._warn_once(
                    "drops", "Capture is falling behind: over 5 percent of frames dropped."
                )

    def _displays_unchanged(self) -> bool:
        from quill.platform.windows.studio_capture import display_targets, physical_pixels

        try:
            with physical_pixels():
                current = {d.device: d.bounds for d in display_targets()}
        except Exception:  # noqa: BLE001
            return True
        if self.plan.target_kind == "display":
            return current.get(self.plan.display_device) == self.plan.display_bounds
        return True

    def _request_stop(self, reason: str) -> None:
        if self.stop_reason:
            return
        self.stop_reason = reason
        self.mark(reason, failure=True)
        if self.auto_stop is not None:
            self.auto_stop(reason)
        else:
            self.on_event(reason, True)

    # -- stop, save, discard ----------------------------------------------------------

    def stop_capture(self) -> None:
        """End capture (closing the open segment) and release every device."""
        self._stop_monitor.set()
        with self._lock:
            if self.state == "recording":
                self._close_segment()
            self.state = "finalizing"
            self.session.state = "finalizing"
            self._save()
        for source in self.sources:
            try:
                source.close()
            except Exception:  # noqa: BLE001 - one device's fault must not keep the others open
                logger.exception("Releasing %s failed", source.label)
        if self._faces is not None:
            self._faces.stop()
            self._faces = None

    def finish(self, cancellation: Any = None) -> Verification:
        self.stop_capture()
        return finalize(
            self.work,
            ffmpeg=self.ffmpeg,
            caps=self.caps,
            dropped=self._dropped,
            cancellation=cancellation,
        )

    def discard(self) -> None:
        self._stop_monitor.set()
        with self._lock:
            for process in (self._screen, self._camera):
                if process is not None:
                    process.kill()
                    process.stop(timeout=2)
            for source in self.sources:
                source.end_segment(time.time())
                source.close()
            if self._faces is not None:
                self._faces.stop()
            self.state = "discarded"
        shutil.rmtree(self.work, ignore_errors=True)


def _hide(folder: Path) -> None:
    try:
        ctypes.windll.kernel32.SetFileAttributesW(str(folder), 0x2)  # FILE_ATTRIBUTE_HIDDEN
    except (AttributeError, OSError):
        pass


# -- finishing (also used to recover after a crash) --------------------------------
