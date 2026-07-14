"""Optional download-time processing for podcast episodes: silence
trimming and ACX loudness normalization. Reuses the exact functions the
audiobook builder already uses (``core/speech/silence.py``,
``core/speech/loudness.py``) rather than a second implementation --
the loudness pass is adapted to keep the episode's original container
format (mp3/m4a/etc.), unlike ``normalize_wav_loudness`` which assumes a
PCM WAV (the audiobook builder's own intermediate format).

Both functions are best-effort: on any failure they leave the original
file untouched and return ``False`` rather than raising, since a failed
optional post-process must never break a completed download.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


def trim_downloaded_episode_silence(path: Path) -> bool:
    """Trim leading/trailing silence from *path* in place. True on success."""
    from quill.core.speech.ffmpeg import TranscodeError
    from quill.core.speech.silence import trim_silence

    if not path.is_file():
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="quill_podcast_trim_") as tmp:
            out = Path(tmp) / f"trimmed{path.suffix}"
            trim_silence(path, out)
            if not out.is_file() or out.stat().st_size == 0:
                return False
            shutil.copyfile(out, path)
        return True
    except (OSError, TranscodeError):
        return False


def _build_apply_command(
    ffmpeg: str, src: Path, out: Path, measured: dict[str, str] | None
) -> list[str]:
    """Like ``loudness.build_loudnorm_apply_command``, but deliberately
    omits its hardcoded ``-c:a pcm_s16le`` -- that assumes the audiobook
    builder's PCM-WAV intermediate format, which would silently corrupt a
    podcast episode still named ``.mp3``/``.m4a``. Letting ffmpeg pick the
    encoder for the output extension keeps the episode's original format."""
    from quill.core.speech.loudness import loudnorm_filter

    if measured is not None:
        flt = (
            f"{loudnorm_filter()}"
            f":measured_I={measured['input_i']}"
            f":measured_TP={measured['input_tp']}"
            f":measured_LRA={measured['input_lra']}"
            f":measured_thresh={measured['input_thresh']}"
            f":offset={measured['target_offset']}"
            ":linear=true"
        )
    else:
        flt = loudnorm_filter()
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-vn",
        "-af",
        flt,
        "-y",
        str(out),
    ]


def normalize_downloaded_episode_loudness(path: Path, *, timeout_seconds: float = 1800.0) -> bool:
    """Normalize *path* to the ACX loudness window in place, keeping its
    original format (unlike ``normalize_wav_loudness``, which assumes a
    PCM WAV). True on success; leaves *path* untouched on any failure."""
    from quill.core.speech.ffmpeg import find_ffmpeg
    from quill.core.speech.loudness import build_loudnorm_measure_command, parse_loudnorm_json
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None or not path.is_file():
        return False
    try:
        measured_run = run_subprocess_safely(
            build_loudnorm_measure_command(ffmpeg, path), timeout_seconds=timeout_seconds
        )
        measured = parse_loudnorm_json(measured_run.stderr or "")
        with tempfile.TemporaryDirectory(prefix="quill_podcast_loudnorm_") as tmp:
            out = Path(tmp) / f"normalized{path.suffix}"
            args = _build_apply_command(ffmpeg, path, out, measured)
            completed = run_subprocess_safely(args, timeout_seconds=timeout_seconds)
            if completed.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
                return False
            shutil.copyfile(out, path)
        return True
    except OSError:
        return False
