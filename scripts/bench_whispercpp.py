"""whisper.cpp in dictbench: QUILL's Locked Dictation default, measured like the rest.

dictbench measures the sherpa-onnx engines in-process. whisper.cpp is a separate
program (``whisper-cli``) that QUILL runs once per recording through
:mod:`quill.core.speech.providers.whispercpp`, so it is measured the same way:
the provider's own :func:`~quill.core.speech.providers.whispercpp.build_whisper_command`
and :func:`~quill.core.speech.providers.whispercpp.parse_whisper_json`, the
pinned ``whisper-cli`` from QUILL's assets-v1 release (v1.9.1) and the
SHA-256-pinned GGML model QUILL downloads, with no initial prompt.

**What the numbers include.** Each recording is one run of the program, as in
the app, so the compute time includes loading the model every time; it is
reported as is, and the load alone (a one-second recording of silence) is
reported beside it as ``startup_seconds``. Peak memory is the program's own
(sampled while it runs), not this script's. ``--threads`` is passed as
``-t``; the app passes none, which lets whisper.cpp use up to four.

Usage::

    python scripts/dictbench.py --dataset fleurs-en --engine whispercpp:base \\
        --whispercpp-exe D:/engines/whispercpp/whisper-cli.exe
"""

from __future__ import annotations

import tempfile
import time
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any

PREFIX = "whispercpp:"
_RATE = 16_000
_POLL_SECONDS = 0.02


def is_whispercpp(engine: str) -> bool:
    return engine.startswith(PREFIX)


def model_id(engine: str) -> str:
    return engine[len(PREFIX) :]


def executable(configured: str | None) -> str:
    from quill.core.speech.providers.whispercpp import resolve_whisper_executable

    found = resolve_whisper_executable(configured)
    if found is None:
        raise SystemExit(
            "whisper-cli was not found. Give --whispercpp-exe, or install whisper.cpp "
            "from QUILL's Speech Hub."
        )
    return found


def model_path(model: str) -> Path:
    from quill.core.speech.providers.whispercpp import _model_path

    path = _model_path(model)
    if not path.is_file():
        raise SystemExit(
            f"The whisper.cpp '{model}' model is not downloaded. Download it in QUILL's "
            "Manage Speech Models, or with WhisperCppProvider().download_model."
        )
    return path


def transcribe(
    exe: str, model: Path, wav: Path, language: str, threads: int
) -> tuple[str, float, float]:
    """``(text, seconds, peak megabytes)`` for one run of whisper-cli on *wav*."""
    import psutil  # type: ignore[import-untyped,import-not-found,unused-ignore]

    from quill.core.speech.provider import TranscriptionRequest
    from quill.core.speech.providers.whispercpp import build_whisper_command, parse_whisper_json

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "out"
        request = TranscriptionRequest(source_path=wav, model_id="", language=language)
        argv = [*build_whisper_command(exe, model, wav, output, request), "-t", str(threads), "-np"]
        began = time.perf_counter()
        process = psutil.Popen(argv, stdout=-3, stderr=-3)  # DEVNULL
        peak = 0
        while process.poll() is None:
            try:
                info = process.memory_info()
                peak = max(peak, getattr(info, "peak_wset", 0) or info.rss)
            except psutil.Error:
                pass
            time.sleep(_POLL_SECONDS)
        seconds = time.perf_counter() - began
        if process.returncode != 0:
            raise RuntimeError(f"whisper-cli exited with code {process.returncode}")
        text = parse_whisper_json(
            output.with_suffix(".json").read_text(encoding="utf-8", errors="replace")
        ).full_text
    return text.strip(), seconds, peak / 1_048_576


def _silence(folder: Path) -> Path:
    path = folder / "silence.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(_RATE)
        out.writeframes(b"\0\0" * _RATE)
    return path


def run_files(
    engine: str,
    language: str,
    folder: Path,
    transcripts: dict[str, str],
    threads: int,
    *,
    exe_path: str | None,
    score: Callable[[str, str, str], Any],
    audio_seconds: Callable[[Path], float],
) -> tuple[list[Any], float, float]:
    """``(results, startup seconds, peak megabytes)`` for every recording."""
    exe = executable(exe_path)
    model = model_path(model_id(engine))
    print(f"whisper.cpp {model_id(engine)}, language {language}, {threads} thread(s), CPU only")
    with tempfile.TemporaryDirectory() as tmp:
        _text, startup, peak = transcribe(exe, model, _silence(Path(tmp)), language, threads)
    results: list[Any] = []
    for name, reference in transcripts.items():
        wav = folder / name
        try:
            heard, seconds, used = transcribe(exe, model, wav, language, threads)
            failure = ""
        except Exception as error:  # noqa: BLE001 - counted, and the run goes on
            heard, seconds, used, failure = "", 0.0, 0.0, str(error)
        peak = max(peak, used)
        result = score(name, reference, heard)
        result.compute_seconds = result.final_seconds = result.first_word_seconds = seconds
        result.audio_seconds = audio_seconds(wav)
        result.failed = failure
        results.append(result)
    return results, startup, round(peak, 1)
