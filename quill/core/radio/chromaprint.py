"""Chromaprint's ``fpcalc``: turning a few seconds of audio into a fingerprint.

Song recognition (:mod:`quill.core.radio.song_recognition`) never sends audio
anywhere. It sends a *fingerprint* -- a compact summary of the sound that
AcoustID can match and nobody can play back -- and Chromaprint's ``fpcalc``
tool is what computes one. It is LGPL, a single small executable, and it is
**not bundled** with Quill Radio today: finding it follows the same "a
managed tools folder first, then the PATH" route as ffmpeg
(``quill/core/speech/ffmpeg.py``), and its absence is a sentence the command
says, never a crash.

Only an executable actually named ``fpcalc`` is ever run, through
``run_subprocess_safely`` with a fixed argument list. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from quill.core.error_codes import CodedError

_ALLOWED = frozenset({"fpcalc", "fpcalc.exe"})

#: Where Chromaprint comes from, and where Quill Radio looks for it.
DOWNLOAD_URL = "https://acoustid.org/chromaprint"

#: What the command says when fpcalc is nowhere to be found.
MISSING_SENTENCE = (
    "Song recognition needs Chromaprint's fpcalc program, which is not installed. "
    f"Download it from {DOWNLOAD_URL}, then put fpcalc.exe in a folder named "
    "chromaprint inside the tools folder of your Quill data folder, or anywhere "
    "on your PATH."
)

#: How much of the sample fpcalc reads. AcoustID matches on up to two minutes.
SAMPLE_SECONDS = 120

_TIMEOUT_SECONDS = 60.0

#: The runner signature fpcalc is invoked through (``run_subprocess_safely``).
Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class ChromaprintError(CodedError):
    """fpcalc could not fingerprint the sample."""

    code = "QUILL-RADIO-CHROMAPRINT-FINGERPRINT"
    listener_facing = True


@dataclass(frozen=True, slots=True)
class Fingerprint:
    """What AcoustID needs: the fingerprint and the sample's length in seconds."""

    fingerprint: str
    duration: int


def search_dirs() -> list[Path]:
    """Quill-managed folders to look in before the PATH, most specific first."""
    from quill.core.paths import app_data_dir

    dirs: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root) / "tools" / "chromaprint")
    exe_dir = Path(sys.executable).parent / "tools" / "chromaprint"
    if exe_dir not in dirs:
        dirs.append(exe_dir)
    dirs.append(app_data_dir() / "tools" / "chromaprint")
    return dirs


def find_fpcalc(dirs: Sequence[Path] | None = None) -> str | None:
    """The path to an ``fpcalc`` executable, or ``None`` when there is none.

    Looked up every time rather than cached: somebody who reads the "not
    installed" sentence and drops the file in should not have to restart.
    """
    exe = "fpcalc.exe" if os.name == "nt" else "fpcalc"
    for directory in dirs if dirs is not None else search_dirs():
        candidate = directory / exe
        if candidate.is_file() and candidate.name.lower() in _ALLOWED:
            return str(candidate)
    found = shutil.which("fpcalc")
    if found and Path(found).name.lower() in _ALLOWED:
        return found
    return None


def build_command(fpcalc: str, sample: Path) -> list[str]:
    """The fixed argument list fpcalc is run with (pure)."""
    return [fpcalc, "-json", "-length", str(SAMPLE_SECONDS), str(sample)]


def parse_output(text: str) -> Fingerprint:
    """fpcalc's ``-json`` answer as a :class:`Fingerprint` (pure).

    Raises :class:`ChromaprintError` for anything that is not a usable
    fingerprint, because sending AcoustID an empty one would only come back as
    a confusing "no match".
    """
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as error:
        raise ChromaprintError("Chromaprint did not return a fingerprint.") from error
    if not isinstance(data, dict):
        raise ChromaprintError("Chromaprint did not return a fingerprint.")
    fingerprint = str(data.get("fingerprint", "") or "").strip()
    try:
        duration = int(float(data.get("duration", 0) or 0))
    except (TypeError, ValueError):
        duration = 0
    if not fingerprint or duration <= 0:
        raise ChromaprintError("Chromaprint could not hear enough audio to fingerprint.")
    return Fingerprint(fingerprint=fingerprint, duration=duration)


def fingerprint(sample: Path, *, fpcalc: str, run: Runner | None = None) -> Fingerprint:
    """Fingerprint *sample* with *fpcalc*. Raises :class:`ChromaprintError`."""
    if run is None:
        from quill.stability.safe_subprocess import run_subprocess_safely

        run = run_subprocess_safely
    try:
        result = run(build_command(fpcalc, sample), timeout_seconds=_TIMEOUT_SECONDS)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        raise ChromaprintError("Chromaprint's fpcalc could not be run.") from error
    if int(getattr(result, "returncode", 1) or 0) != 0:
        raise ChromaprintError("Chromaprint could not read the audio sample.")
    return parse_output(str(getattr(result, "stdout", "") or ""))
