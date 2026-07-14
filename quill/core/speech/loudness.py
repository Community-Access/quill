"""ACX loudness measurement and one-click normalization (§1.5 audiobook).

Audiobook platforms (ACX / Audible) require each delivered file to sit in a narrow
loudness window: integrated **RMS between -23 dB and -18 dB**, **peak no higher than
-3 dB**, and a noise floor below -60 dB RMS. This module measures a finished master
with ffmpeg's ``volumedetect`` filter and reports whether it meets the ACX window;
the one-click fix re-encodes through ffmpeg's ``loudnorm`` filter (applied during the
audiobook build) to pull RMS and true-peak into range in a single pass.

wx-free, strict-typed. Only the RMS and peak constraints are evaluated and fixed
automatically — the noise-floor requirement depends on the source recording quality
and is left to the author's judgement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# ACX delivery window, in decibels relative to full scale.
ACX_RMS_MIN = -23.0
ACX_RMS_MAX = -18.0
ACX_PEAK_MAX = -3.0
# The one-click fix aims for the middle of the RMS window with true-peak just under
# the ceiling. ``loudnorm`` works in LUFS / dBTP, a close proxy for ACX's RMS/peak.
ACX_TARGET_RMS = -20.0
ACX_TARGET_TP = -3.1
ACX_TARGET_LRA = 11.0

_MEAN_RE = re.compile(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB")
_MAX_RE = re.compile(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB")


@dataclass(slots=True)
class LoudnessStats:
    """Measured integrated RMS (``mean_db``) and peak (``max_db``) of one file."""

    mean_db: float
    max_db: float

    @property
    def rms_ok(self) -> bool:
        return ACX_RMS_MIN <= self.mean_db <= ACX_RMS_MAX

    @property
    def peak_ok(self) -> bool:
        return self.max_db <= ACX_PEAK_MAX

    @property
    def acx_compliant(self) -> bool:
        return self.rms_ok and self.peak_ok

    def summary(self) -> str:
        """A one-line, speakable verdict for the status bar / a screen reader."""
        rms = f"RMS {self.mean_db:.1f} dB"
        peak = f"peak {self.max_db:.1f} dB"
        if self.acx_compliant:
            return f"Output is within ACX loudness range ({rms}, {peak})."
        problems: list[str] = []
        if not self.rms_ok:
            problems.append(f"{rms} is outside ACX's -23 to -18 dB")
        if not self.peak_ok:
            problems.append(f"{peak} exceeds the -3 dB ceiling")
        tail = " — rebuild with Normalize to ACX loudness enabled."
        return "; ".join(problems) + tail


def loudnorm_filter() -> str:
    """The ffmpeg ``loudnorm`` filter string that targets the ACX window."""
    return f"loudnorm=I={ACX_TARGET_RMS}:TP={ACX_TARGET_TP}:LRA={ACX_TARGET_LRA}"


# Two-pass loudnorm (the ChapterForge / ACB method): a first pass *measures* the
# input, a second pass applies ``loudnorm`` seeded with those measured values for
# accurate linear normalization. Keys are the ones ffmpeg prints as JSON.
_LOUDNORM_KEYS = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")


def build_loudnorm_measure_command(ffmpeg: str, path: Path) -> list[str]:
    """ffmpeg argv that measures *path* with loudnorm and prints the JSON to stderr."""
    return [
        ffmpeg,
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-vn",
        "-af",
        f"{loudnorm_filter()}:print_format=json",
        "-f",
        "null",
        "-",
    ]


def parse_loudnorm_json(stderr: str) -> dict[str, str] | None:
    """Parse the measured loudnorm values from ffmpeg's JSON block (None if absent)."""
    import json
    import re

    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr or "", re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not all(key in data for key in _LOUDNORM_KEYS):
        return None
    return {key: str(data[key]) for key in _LOUDNORM_KEYS}


def build_loudnorm_apply_command(
    ffmpeg: str, src: Path, out: Path, measured: dict[str, str]
) -> list[str]:
    """ffmpeg argv that applies loudnorm to *src* using the *measured* values (PCM WAV out)."""
    flt = (
        f"{loudnorm_filter()}"
        f":measured_I={measured['input_i']}"
        f":measured_TP={measured['input_tp']}"
        f":measured_LRA={measured['input_lra']}"
        f":measured_thresh={measured['input_thresh']}"
        f":offset={measured['target_offset']}"
        ":linear=true"
    )
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
        "-c:a",
        "pcm_s16le",
        "-y",
        str(out),
    ]


def normalize_wav_loudness(path: Path, *, timeout_seconds: float = 1800.0) -> bool:
    """Normalize *path* (a PCM WAV) to the ACX loudness window in place; True on success.

    Two-pass ``loudnorm`` (measure then apply with ``linear=true``, which preserves
    duration so chapter timing stays valid). Falls back to a single pass if the
    measurement can't be parsed. Returns ``False`` (leaving the file untouched) when
    ffmpeg is missing or the encode fails — the caller keeps the un-normalized audio.
    """
    import tempfile

    from quill.core.speech.ffmpeg import find_ffmpeg
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None or not path.is_file():
        return False
    try:
        measured_run = run_subprocess_safely(
            build_loudnorm_measure_command(ffmpeg, path), timeout_seconds=timeout_seconds
        )
        measured = parse_loudnorm_json(measured_run.stderr or "")
        with tempfile.TemporaryDirectory(prefix="quill_loudnorm_") as tmp:
            out = Path(tmp) / "norm.wav"
            if measured is not None:
                args = build_loudnorm_apply_command(ffmpeg, path, out, measured)
            else:  # single-pass fallback when the measurement JSON is unavailable
                args = [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(path),
                    "-vn",
                    "-af",
                    loudnorm_filter(),
                    "-c:a",
                    "pcm_s16le",
                    "-y",
                    str(out),
                ]
            completed = run_subprocess_safely(args, timeout_seconds=timeout_seconds)
            if completed.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
                return False
            import shutil

            shutil.copyfile(out, path)
        return True
    except OSError:
        return False


def build_volumedetect_command(ffmpeg: str, path: Path) -> list[str]:
    """ffmpeg argv that prints a file's mean/max volume (to stderr), decoding to null."""
    return [
        ffmpeg,
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-vn",
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ]


def parse_volumedetect(stderr: str) -> LoudnessStats | None:
    """Parse ``mean_volume`` / ``max_volume`` from ffmpeg ``volumedetect`` output."""
    mean = _MEAN_RE.search(stderr or "")
    peak = _MAX_RE.search(stderr or "")
    if not mean or not peak:
        return None
    return LoudnessStats(mean_db=float(mean.group(1)), max_db=float(peak.group(1)))


def measure_loudness(path: Path, *, timeout_seconds: float = 600.0) -> LoudnessStats | None:
    """Measure *path*'s loudness via ffmpeg ``volumedetect`` (None when unavailable).

    Decodes the whole file, so callers run it on the background task pool, never on
    the UI thread. Returns ``None`` if ffmpeg is missing, the file is absent, or the
    output could not be parsed.
    """
    from quill.core.speech.ffmpeg import find_ffmpeg
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None or not path.is_file():
        return None
    try:
        completed = run_subprocess_safely(
            build_volumedetect_command(ffmpeg, path), timeout_seconds=timeout_seconds
        )
    except OSError:
        return None
    # volumedetect prints its histogram to stderr; safe_subprocess captures it.
    return parse_volumedetect(completed.stderr or "")


# ---------------------------------------------------------------------- ACX check

# ACX audition targets for the per-file compliance check (loudnorm analysis):
# integrated loudness near -20 LUFS (±3), true peak at or under -3 dBTP, and a
# gating threshold (approximating the noise floor) at or under -60 dB.
ACX_LUFS_TARGET = -20.0
ACX_LUFS_RANGE = 3.0
ACX_NOISE_MAX = -60.0


@dataclass(slots=True)
class AcxCheck:
    """One file's ACX compliance measurement, with speakable recommendations."""

    integrated_lufs: float
    true_peak_db: float
    noise_floor_db: float
    loudness_ok: bool
    peak_ok: bool
    noise_ok: bool

    @property
    def ok(self) -> bool:
        return self.loudness_ok and self.peak_ok and self.noise_ok

    def recommendations(self) -> list[str]:
        """Plain sentences telling the user what to fix (empty when compliant)."""
        recs: list[str] = []
        if not self.loudness_ok:
            diff = ACX_LUFS_TARGET - self.integrated_lufs
            direction = "louder" if diff > 0 else "quieter"
            recs.append(
                f"Integrated loudness is {self.integrated_lufs:.1f} LUFS (need "
                f"{ACX_LUFS_TARGET} plus or minus {ACX_LUFS_RANGE}). Enable loudness "
                f"normalization and rebuild, or make the recording {abs(diff):.1f} dB "
                f"{direction}."
            )
        if not self.peak_ok:
            recs.append(
                f"True peak is {self.true_peak_db:.1f} dBFS (max {ACX_PEAK_MAX}). "
                "Enable peak limiting or reduce the recording level."
            )
        if not self.noise_ok:
            recs.append(
                f"Noise floor is {self.noise_floor_db:.1f} dBFS (max {ACX_NOISE_MAX}). "
                "Record in a quieter environment or apply noise reduction."
            )
        return recs


def acx_check_from_measurement(measured: dict[str, str]) -> AcxCheck:
    """Build an :class:`AcxCheck` from parsed loudnorm-analysis JSON (pure)."""

    def _f(key: str, fallback: float = -99.0) -> float:
        try:
            return float(measured.get(key, fallback))
        except (TypeError, ValueError):
            return fallback

    lufs = _f("input_i")
    peak = _f("input_tp")
    # input_thresh is loudnorm's gating threshold; it approximates the noise
    # floor well enough for a compliance report.
    noise = _f("input_thresh")
    return AcxCheck(
        integrated_lufs=lufs,
        true_peak_db=peak,
        noise_floor_db=noise,
        loudness_ok=abs(lufs - ACX_LUFS_TARGET) <= ACX_LUFS_RANGE,
        peak_ok=peak <= ACX_PEAK_MAX,
        noise_ok=noise <= ACX_NOISE_MAX,
    )


def acx_check_file(path: Path, *, timeout_seconds: float = 1800.0) -> AcxCheck | None:
    """Measure *path* against the ACX submission window (None when unmeasurable).

    Runs loudnorm in analysis mode (decodes the whole file — background pool
    only) and folds the measurement into pass/fail flags plus recommendations.
    """
    from quill.core.speech.ffmpeg import find_ffmpeg
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None or not path.is_file():
        return None
    try:
        completed = run_subprocess_safely(
            build_loudnorm_measure_command(ffmpeg, path), timeout_seconds=timeout_seconds
        )
    except OSError:
        return None
    measured = parse_loudnorm_json(completed.stderr or "")
    if measured is None:
        return None
    return acx_check_from_measurement(measured)
