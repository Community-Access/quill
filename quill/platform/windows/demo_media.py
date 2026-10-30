"""FFmpeg processes, capabilities and the camera for Record a Demonstration.

Long-running capture needs more than ``run_subprocess_safely`` offers: a
process that runs until told to stop, whose progress lines are read as they
arrive and whose standard input takes the ``q`` that ends it cleanly (so the
Matroska segment is closed properly). Every command is still an argument
list from :mod:`quill.core.demo_recording_ffmpeg`, never a shell string, and
runs without a console window. Short probes go through the safe wrapper.

The camera is FFmpeg's DirectShow input. The camera check reads small grey
frames from it and runs Windows' own face detector on them; during a
recording the same FFmpeg process that records the camera also hands those
frames over, because a camera can generally be opened by one program at a
time. Windows-only.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any

from quill.core.demo_camera import Framing, framing
from quill.core.demo_recording_ffmpeg import (
    FACE_FRAME_SIZE,
    Capabilities,
    StartEstimator,
    camera_preview_command,
    list_cameras_command,
    parse_dshow_devices,
    parse_listing,
    parse_stats,
)
from quill.stability.safe_subprocess import run_subprocess_safely

logger = logging.getLogger(__name__)

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

FACE_FAILURES_BEFORE_GIVING_UP = 3
FACE_DETECTION_STOPPED = (
    "Face detection stopped answering, so framing advice has stopped. "
    "Close the camera check and open it again, or restart the computer if it keeps happening."
)


def probe_capabilities(ffmpeg: str) -> Capabilities:
    """What this FFmpeg can actually do -- probed, never assumed (REC-009)."""

    def listing(flag: str) -> frozenset[str]:
        try:
            result = run_subprocess_safely([ffmpeg, "-hide_banner", flag], timeout_seconds=20)
        except (OSError, subprocess.TimeoutExpired, ValueError):
            return frozenset()
        return parse_listing((result.stdout or "") + (result.stderr or ""))

    return Capabilities(listing("-encoders"), listing("-filters"), listing("-devices"))


def list_cameras(ffmpeg: str) -> list[str]:
    try:
        result = run_subprocess_safely(list_cameras_command(ffmpeg), timeout_seconds=20)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return []
    text = (result.stdout or "") + (result.stderr or "")
    return [name for name, kind in parse_dshow_devices(text) if kind == "video"]


class FFmpegProcess:
    """One FFmpeg run: started, its progress followed, stopped with ``q``."""

    def __init__(
        self,
        command: list[str],
        *,
        log_path: Path | None = None,
        on_frame: Callable[[bytes], None] | None = None,
        frame_bytes: int = 0,
    ) -> None:
        self.command = command
        self.log_path = log_path
        self.on_frame = on_frame
        self.frame_bytes = frame_bytes
        self.start = StartEstimator()
        self.launched = 0.0
        self.last_stats: Any = None
        self.child: subprocess.Popen[bytes] | None = None
        self._log: IO[str] | None = None
        self._threads: list[threading.Thread] = []
        self._stopping = False
        self.tail: list[str] = []

    def launch(self) -> None:
        if self.log_path is not None:
            self._log = self.log_path.open("a", encoding="utf-8", errors="replace")
        self.launched = time.time()
        try:
            self.child = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE if self.on_frame else subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=_NO_WINDOW,
            )
        except OSError as error:
            raise OSError(f"Could not run FFmpeg: {error}") from error
        reader = threading.Thread(target=self._read_stderr, daemon=True, name="ffmpeg-stderr")
        reader.start()
        self._threads.append(reader)
        if self.on_frame is not None:
            frames = threading.Thread(target=self._read_frames, daemon=True, name="ffmpeg-frames")
            frames.start()
            self._threads.append(frames)

    def _read_stderr(self) -> None:
        child = self.child
        if child is None or child.stderr is None:
            return
        buffer = b""
        while True:
            chunk = (
                child.stderr.read1(4096)
                if hasattr(child.stderr, "read1")
                else child.stderr.read(4096)
            )
            if not chunk:
                break
            buffer += chunk
            # Progress lines end in a carriage return, everything else in a newline.
            parts = buffer.replace(b"\r", b"\n").split(b"\n")
            buffer = parts.pop()
            for raw in parts:
                line = raw.decode("utf-8", "replace").strip()
                if not line:
                    continue
                stats = parse_stats(line)
                if stats is not None:
                    self.last_stats = stats
                    self.start.report(time.time(), stats.seconds)
                    continue
                self.tail = (self.tail + [line])[-20:]
                if self._log is not None:
                    self._log.write(line + "\n")

    def _read_frames(self) -> None:
        child = self.child
        if child is None or child.stdout is None or self.on_frame is None:
            return
        while True:
            data = child.stdout.read(self.frame_bytes)
            if not data or len(data) < self.frame_bytes:
                return
            try:
                self.on_frame(data)
            except Exception:  # noqa: BLE001 - a frame consumer must never stop capture
                logger.exception("Camera frame consumer failed")

    @property
    def running(self) -> bool:
        return self.child is not None and self.child.poll() is None

    @property
    def returncode(self) -> int | None:
        return None if self.child is None else self.child.poll()

    @property
    def stopping(self) -> bool:
        return self._stopping

    def stop(self, timeout: float = 10.0) -> int | None:
        """Ask FFmpeg to finish its file (``q``), then insist if it does not."""
        self._stopping = True
        child = self.child
        if child is None:
            return None
        if child.poll() is None:
            try:
                assert child.stdin is not None
                child.stdin.write(b"q")
                child.stdin.flush()
            except (OSError, ValueError):
                pass
            try:
                child.wait(timeout)
            except subprocess.TimeoutExpired:
                child.terminate()
                try:
                    child.wait(3)
                except subprocess.TimeoutExpired:
                    child.kill()
        for thread in self._threads:
            thread.join(2)
        if self._log is not None:
            self._log.close()
            self._log = None
        return child.poll()

    def kill(self) -> None:
        self._stopping = True
        if self.child is not None and self.child.poll() is None:
            self.child.kill()


class FaceWatcher:
    """Runs the face detector on frames from FFmpeg, on its own thread.

    Frames arrive faster than detection sometimes runs; only the newest is
    kept, so advice is never about where the presenter was seconds ago.
    """

    def __init__(self, on_framing: Callable[[Framing], None], *, mirrored: bool = False) -> None:
        self.on_framing = on_framing
        self.mirrored = mirrored
        self._latest: bytes | None = None
        self._ready = threading.Event()
        self._stop = threading.Event()
        self.error = ""
        self._thread = threading.Thread(target=self._run, daemon=True, name="face-watcher")

    def start(self) -> None:
        self._thread.start()

    def feed(self, frame: bytes) -> None:
        self._latest = frame
        self._ready.set()

    def stop(self) -> None:
        self._stop.set()
        self._ready.set()
        self._thread.join(3)

    def _run(self) -> None:
        from quill.platform.windows.face_detect import FaceDetectionError, FaceDetector

        width, height = FACE_FRAME_SIZE
        try:
            detector = FaceDetector()
        except FaceDetectionError as error:
            self.error = str(error)
            self.on_framing(Framing(0, f"Face detection is unavailable: {error}"))
            return
        # A detector that stops answering is replaced, not asked again, and after
        # three failures in a row the advice stops with one sentence rather than
        # going quiet. Learned from Kelly Ford's Quick Describe, whose Windows AI
        # helper kept reporting itself ready while it had stopped answering.
        failures = 0
        try:
            while not self._stop.is_set():
                self._ready.wait(1.0)
                self._ready.clear()
                frame, self._latest = self._latest, None
                if frame is None or self._stop.is_set():
                    continue
                try:
                    boxes = detector.detect(frame, width, height)
                except FaceDetectionError as error:
                    self.error = str(error)
                    failures += 1
                    detector.close()
                    try:
                        if failures >= FACE_FAILURES_BEFORE_GIVING_UP:
                            raise FaceDetectionError(str(error))
                        detector = FaceDetector()
                    except FaceDetectionError:
                        self.on_framing(Framing(0, FACE_DETECTION_STOPPED))
                        return
                    continue
                failures = 0
                self.on_framing(framing(boxes, width, height, mirrored=self.mirrored))
        finally:
            detector.close()


class CameraCheck:
    """The camera check: live framing advice with nothing written to disk."""

    def __init__(
        self, ffmpeg: str, device: str, on_framing: Callable[[Framing], None], *, mirrored: bool
    ) -> None:
        self.watcher = FaceWatcher(on_framing, mirrored=mirrored)
        width, height = FACE_FRAME_SIZE
        self.process = FFmpegProcess(
            camera_preview_command(ffmpeg, device),
            on_frame=self.watcher.feed,
            frame_bytes=width * height,
        )

    def start(self) -> None:
        self.watcher.start()
        self.process.launch()

    def stop(self) -> None:
        self.process.kill()
        self.process.stop(timeout=2)
        self.watcher.stop()

    @property
    def failure(self) -> str:
        code = self.process.returncode
        if code is not None and code != 0 and not self.process.stopping:
            detail = self.process.tail[-1] if self.process.tail else f"exit code {code}"
            return f"The camera could not be opened: {detail}"
        return ""


def free_bytes(folder: Path) -> int:
    import shutil

    try:
        return int(shutil.disk_usage(folder).free)
    except OSError:
        return -1


def folder_problem(folder: Path) -> str:
    """Why *folder* cannot take a recording, or ``""``."""
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / f".studio-write-test-{os.getpid()}"
        probe.write_bytes(b"ok")
        probe.unlink()
    except OSError as error:
        return error.strerror or str(error)
    return ""
