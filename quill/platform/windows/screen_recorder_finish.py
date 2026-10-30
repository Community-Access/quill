"""Finishing a demonstration: join, mix, check independently, report (REC-014).

Split from :mod:`quill.platform.windows.screen_recorder` (GATE-11). Also the
recovery path: :func:`finalize` needs only the hidden work folder, so a
recording a crash interrupted is finished the same way as one stopped
normally.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from quill.core.demo_recording import DemoPlan, DemoRecordingError, MarkerLog, unique_path
from quill.core.demo_recording_ffmpeg import (
    AudioInput,
    Capabilities,
    concat_command,
    concat_list,
    finish_segment_command,
    finish_sound_segment_command,
    sound_file_command,
)
from quill.core.demo_recording_session import (
    SessionRecord,
    markers_from_session,
    plan_from_dict,
)
from quill.core.demo_recording_verify import (
    ProbeResult,
    SourceLevel,
    Verification,
    black_check_command,
    build_probe_command,
    classify,
    decode_check_command,
    decode_positions,
    parse_black,
    parse_probe,
    save_reports,
    sha256_file,
)
from quill.platform.windows.demo_audio import level_from_wav
from quill.stability.safe_subprocess import run_subprocess_safely


def _run(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return run_subprocess_safely(command, timeout_seconds=timeout)


def _probe_duration(ffprobe: str | None, path: Path, fps: int) -> float:
    if not ffprobe:
        return 0.0
    try:
        result = _run(build_probe_command(ffprobe, path), 120)
    except (OSError, subprocess.TimeoutExpired):
        return 0.0
    probe = parse_probe(result.stdout or "")
    if probe.duration > 0:
        return probe.duration
    return probe.video_packets / fps if fps else 0.0


def finalize(
    work: Path,
    *,
    ffmpeg: str,
    caps: Capabilities,
    dropped: int = 0,
    cancellation: Any = None,
) -> Verification:
    """Join, mix, check and report the recording in *work*; remove *work* if it passed."""
    from quill.core.speech.ffmpeg import find_ffprobe

    session = SessionRecord.load(work)
    plan = plan_from_dict(session.plan)
    markers = markers_from_session(session)
    output = Path(session.output)
    ffprobe = find_ffprobe()
    encoder = caps.h264_encoder or "libx264"
    session.state = "finalizing"
    session.save(work)
    parts: list[Path] = []
    expected = 0.0
    labels = {source.source_id: source for source in plan.enabled_sources()}
    stems: dict[str, list[Path]] = {key: [] for key in labels}
    for segment in session.segments:
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        folder = Path(segment.folder)
        video = folder / ("video.mkv" if plan.screen else "camera.mkv")
        if plan.has_picture:
            if not video.is_file() or video.stat().st_size == 0:
                continue
            duration = segment.duration or _probe_duration(ffprobe, video, plan.fps)
        else:
            duration = segment.duration
        if duration <= 0:
            continue
        video_start = segment.video_start
        sources = []
        for source_id in labels:
            wav = folder / f"{source_id}.wav"
            if not wav.is_file():
                continue
            stems[source_id].append(wav)
            start = segment.audio_starts.get(source_id, video_start)
            offset = (start - video_start) if video_start else 0.0
            sources.append(AudioInput(wav, labels[source_id].level_db, offset))
        if not plan.has_picture:
            if not sources:
                continue
            part = folder / "part.wav"
            command = finish_sound_segment_command(ffmpeg, part, sources=sources, duration=duration)
        else:
            # A camera corner only when the screen is the picture.
            camera = folder / "camera.mkv"
            has_camera = plan.screen and camera.is_file() and camera.stat().st_size > 0
            camera_offset = (
                (segment.camera_start - video_start) if (has_camera and video_start) else 0.0
            )
            part = folder / "part.mp4"
            command = finish_segment_command(
                ffmpeg,
                plan,
                video,
                part,
                sources=sources,
                camera=camera if has_camera else None,
                camera_offset=camera_offset,
                duration=duration,
                encoder=encoder,
            )
        result = _run(command, max(120.0, duration * 4 + 60))
        if result.returncode != 0 or not part.is_file():
            lines = (result.stderr or "").strip().splitlines()
            raise DemoRecordingError(
                f"Segment {segment.index} could not be finished: "
                + (lines[-1] if lines else f"exit code {result.returncode}")
                + f". The recorded pieces are kept in {work}."
            )
        parts.append(part)
        expected += duration
    if not parts:
        session.state = "failed"
        session.save(work)
        raise DemoRecordingError(f"Nothing was recorded. The pieces are kept in {work}.")
    list_file = work / "parts.txt"
    list_file.write_text(concat_list(parts), encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    final = unique_path(output) if output.exists() else output
    join = (
        concat_command(ffmpeg, list_file, final)
        if plan.has_picture
        else sound_file_command(ffmpeg, list_file, final, plan.sound_format)
    )
    result = _run(join, max(120.0, expected * 2 + 60))
    if result.returncode != 0 or not final.is_file():
        lines = (result.stderr or "").strip().splitlines()
        raise DemoRecordingError(
            "The parts could not be joined: " + (lines[-1] if lines else "unknown error")
        )
    levels = _levels(stems, labels)
    verification = verify(
        final, plan, expected, levels, markers, ffmpeg=ffmpeg, ffprobe=ffprobe, dropped=dropped
    )
    if plan.keep_stems:
        _write_stems(ffmpeg, final, stems, labels)
    save_reports(final, verification, plan, markers)
    if verification.state == "Failed":
        session.state = "failed"
        session.save(work)
    else:
        session.state = "finished"
        shutil.rmtree(work, ignore_errors=True)
    return verification


def _levels(stems: dict[str, list[Path]], labels: dict[str, Any]) -> list[SourceLevel]:
    levels = []
    for source_id, files in stems.items():
        if not files:
            continue
        measured = [level_from_wav(path, labels[source_id].label) for path in files]
        peak = max(level.peak_dbfs for level in measured)
        rms = max(level.rms_dbfs for level in measured)
        silent = all(level.digital_silence for level in measured)
        levels.append(
            SourceLevel(
                labels[source_id].label, peak, rms, silent, sum(level.seconds for level in measured)
            )
        )
    return levels


def _write_stems(
    ffmpeg: str, final: Path, stems: dict[str, list[Path]], labels: dict[str, Any]
) -> None:
    from quill.core.demo_recording import short_target_name

    for source_id, files in stems.items():
        if not files:
            continue
        name = short_target_name(labels[source_id].label)
        target = unique_path(final.with_name(f"{final.stem} - {name}.wav"))
        if len(files) == 1:
            shutil.copyfile(files[0], target)
            continue
        listing = files[0].parent.parent / f"stem-{source_id}.txt"
        listing.write_text(concat_list(files), encoding="utf-8")
        _run(
            [
                ffmpeg,
                "-hide_banner",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(listing),
                "-c",
                "copy",
                str(target),
            ],
            600,
        )


def verify(
    path: Path,
    plan: DemoPlan,
    expected: float,
    levels: list[SourceLevel],
    markers: MarkerLog,
    *,
    ffmpeg: str,
    ffprobe: str | None,
    dropped: int = 0,
) -> Verification:
    """Reopen *path* independently and judge it (REC-014)."""
    if ffprobe:
        try:
            probe = parse_probe(_run(build_probe_command(ffprobe, path), 600).stdout or "")
        except (OSError, subprocess.TimeoutExpired) as error:
            probe = ProbeResult(error=str(error))
    else:
        probe = ProbeResult(error="ffprobe was not found beside FFmpeg")
    errors = []
    for start in decode_positions(probe.duration or expected):
        try:
            result = _run(decode_check_command(ffmpeg, path, start), 120)
            text = (result.stderr or "").strip()
            if result.returncode != 0 or text:
                detail = text.splitlines()[-1] if text else f"exit code {result.returncode}"
                errors.append(f"at {start:.0f} seconds: {detail}")
        except (OSError, subprocess.TimeoutExpired) as error:
            errors.append(str(error))
    try:
        black = parse_black(_run(black_check_command(ffmpeg, path), 900).stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        black = []
    folder_label = _spoken_folder(path.parent)
    verification = classify(
        plan,
        probe,
        expected_duration=expected,
        decode_errors=errors,
        black=black,
        levels=levels,
        markers=markers,
        dropped_frames=dropped,
        folder_label=folder_label,
    )
    verification.sha256 = sha256_file(path)
    verification.path = str(path)
    return verification


def _spoken_folder(folder: Path) -> str:
    parts = folder.parts
    return ", ".join(parts[-2:]) if len(parts) >= 2 else str(folder)


def videos_folder() -> Path | None:
    """The user's Videos known folder, or ``None``."""
    try:

        class _Guid(ctypes.Structure):
            _fields_ = [
                ("a", ctypes.c_uint32),
                ("b", ctypes.c_uint16),
                ("c", ctypes.c_uint16),
                ("d", ctypes.c_ubyte * 8),
            ]

        guid = _Guid(
            0x18989B1D,
            0x99B5,
            0x455B,
            (ctypes.c_ubyte * 8)(0x84, 0x1C, 0xAB, 0x7C, 0x74, 0xE4, 0xDD, 0xFC),
        )
        path = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(guid), 0, None, ctypes.byref(path)
        ):
            return None
        try:
            return Path(path.value) if path.value else None
        finally:
            ctypes.windll.ole32.CoTaskMemFree(path)
    except (AttributeError, OSError):
        return None


def studio_process_id() -> int:
    return os.getpid()
