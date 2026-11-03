"""Phonon 31m: Gradium's offline neural voice for Read Aloud and Studio narration.

The engine is the ``ptts`` wheel (a Rust extension, no PyTorch, no espeak),
which ships in the shared runtime; the model and its 37 English voices ship
beside it at ``phonon-models/en`` (``scripts/fetch_build_deps.py --only
phonon``). Nothing here downloads: the model is always constructed from a
local folder and the voice catalogue is always the local ``voices.jsonl``, so
the library's Hugging Face fetch path is never reached (phononprd.md R-9,
R-40).

Two guards come before the import, because the wheel is built for AVX2 and a
CPU without it dies with an illegal-instruction fault Python cannot catch:
:func:`cpu_supported` asks Windows (``IsProcessorFeaturePresent``) rather than
spawning a probe process, which is the same answer at no cost.

Rate is the model's ``duration_delta`` condition. Measured on the 31m model
(2026-11-02), it moves speech from about 0.85 to 1.3 times normal speed and
breaks up past that, so :func:`duration_delta_for_speed` clamps to that range
and the settings say so rather than pretending to reach 2x.

wx-free.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys
import threading
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "DEFAULT_VOICE",
    "MAX_SPEED",
    "MIN_SPEED",
    "PhononVoice",
    "clear_phonon_cache",
    "cpu_supported",
    "default_phonon_model_dir",
    "duration_delta_for_speed",
    "list_phonon_voices",
    "phonon_engine_ready",
    "phonon_model_ready",
    "phonon_status",
    "voice_options",
    "ptts_importable",
    "require_ready",
    "run_live",
    "synthesize_with_phonon",
]

#: The voice id that means "the model's own default voice".
DEFAULT_VOICE = "default"
MIN_SPEED = 0.85
MAX_SPEED = 1.3

MODEL_FILE = "model.q8.gguf"
_REQUIRED = (MODEL_FILE, "config.json", "tokenizer.json", "default-voice.safetensors")
_MODEL_SUBDIR = Path("phonon-models") / "en"
_QUANT = "q8_0"

# (speed, duration_delta) measured on the 31m model; linear between points.
_RATE_POINTS: tuple[tuple[float, float], ...] = (
    (0.85, 0.5),
    (0.9, 0.25),
    (1.0, 0.0),
    (1.13, -0.1),
    (1.2, -0.25),
    (1.3, -0.5),
)

# PF_AVX2_INSTRUCTIONS_AVAILABLE, winnt.h. True only when the OS also saves
# the AVX state, which is the condition that actually matters.
_PF_AVX2 = 40


@dataclass(frozen=True)
class PhononVoice:
    id: str
    name: str
    description: str = ""
    gender: str = ""


def _has_model(directory: Path) -> bool:
    return all((directory / name).is_file() for name in _REQUIRED)


def _candidate_dirs() -> list[Path]:
    from quill.core.paths import app_data_dir

    dirs = [app_data_dir() / _MODEL_SUBDIR]
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root) / _MODEL_SUBDIR)
    bundle = getattr(sys, "_MEIPASS", "")
    if bundle:
        dirs.append(Path(bundle) / _MODEL_SUBDIR)
    # A source checkout: where scripts/fetch_build_deps.py stages it.
    dirs.append(Path(__file__).resolve().parents[3] / "build" / "deps" / "phonon-31m-en")
    return dirs


def default_phonon_model_dir() -> Path | None:
    """The first folder holding a complete model, or None."""
    for directory in _candidate_dirs():
        if _has_model(directory):
            return directory
    return None


def phonon_model_ready(model_dir: Path | None = None) -> bool:
    directory = model_dir or default_phonon_model_dir()
    return directory is not None and _has_model(directory)


def ptts_importable() -> bool:
    """True when the ``ptts`` wheel is installed, without importing it."""
    try:
        return importlib.util.find_spec("ptts") is not None
    except (ImportError, ValueError):
        return False


def cpu_supported() -> bool:
    """True when this processor can run the AVX2 build of ``ptts``."""
    machine = platform.machine().lower()
    if machine not in {"amd64", "x86_64", "x64", "i386", "i686", "x86"}:
        return True  # Arm builds carry no AVX2 requirement
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32")
            return bool(kernel32.IsProcessorFeaturePresent(_PF_AVX2))
        except (OSError, AttributeError):
            return False
    if sys.platform.startswith("linux"):
        try:
            return " avx2" in Path("/proc/cpuinfo").read_text(encoding="utf-8")
        except OSError:
            return False
    return True  # Intel Macs that run current macOS all have AVX2


def phonon_status(model_dir: Path | None = None) -> str:
    """``ready``, or the plain reason it is not: ``cpu``, ``model`` or ``engine``."""
    if not cpu_supported():
        return "cpu"
    if not phonon_model_ready(model_dir):
        return "model"
    if not ptts_importable():
        return "engine"
    return "ready"


def phonon_engine_ready(model_dir: Path | None = None) -> bool:
    return phonon_status(model_dir) == "ready"


def unavailable_message(status: str) -> str:
    if status == "cpu":
        return (
            "Phonon needs a processor from about 2015 or later, and this computer's "
            "processor is older. Piper works here and sounds similar for most reading."
        )
    if status == "model":
        return "The Phonon voice files are missing. Reinstall the app to restore them."
    if status == "engine":
        return "The Phonon speech engine is missing. Reinstall the app to restore it."
    return ""


def require_ready() -> None:
    """Raise ``PhononUnavailableError`` with the plain reason when Phonon cannot run."""
    status = phonon_status()
    if status != "ready":
        from quill.core.read_aloud import PhononUnavailableError

        raise PhononUnavailableError(unavailable_message(status))


def voice_options() -> list[Any]:
    """The voices as Read Aloud ``VoiceOption`` rows; ``installed`` only when it can run here."""
    from quill.core.read_aloud import VoiceOption

    ready = phonon_engine_ready()
    return [
        VoiceOption(
            id=v.id, name=v.name, accent="English", description=v.description, installed=ready
        )
        for v in list_phonon_voices()
    ]


def run_live(
    controller: Any,
    spans: list[Any],
    text: str,
    voice: str,
    speed: float,
    on_progress: Callable[[int, int], None] | None,
) -> None:
    """Read Aloud's live path: each sentence to a cached WAV, played in turn."""

    def gen(sentence: str, out: Path) -> None:
        synthesize_with_phonon(sentence, out, voice=voice, speed=speed)

    controller._cache_seed = ("phonon", voice, speed)
    controller._run_wav_sentences(spans, text, on_progress=on_progress, generate_sentence_wav=gen)


def list_phonon_voices(model_dir: Path | None = None) -> list[PhononVoice]:
    """The default voice, then the catalogue's voices sorted by name."""
    voices = [PhononVoice(DEFAULT_VOICE, "Default", "The model's own voice.")]
    directory = model_dir or default_phonon_model_dir()
    if directory is None:
        return voices
    catalogue = directory / "voices.jsonl"
    try:
        lines = catalogue.read_text(encoding="utf-8").splitlines()
    except OSError:
        return voices
    found: list[PhononVoice] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        name = str(entry.get("name", "")).strip()
        if name and (directory / str(entry.get("filename", ""))).is_file():
            found.append(
                PhononVoice(
                    name,
                    name,
                    str(entry.get("description", "")).strip(),
                    str(entry.get("gender", "")).strip(),
                )
            )
    return voices + sorted(found, key=lambda v: v.name.lower())


def clamp_speed(speed: float) -> float:
    return max(MIN_SPEED, min(MAX_SPEED, float(speed)))


def duration_delta_for_speed(speed: float) -> float:
    """The ``duration_delta`` condition for a speed multiplier (1.0 = normal)."""
    s = clamp_speed(speed)
    for (s0, d0), (s1, d1) in zip(_RATE_POINTS, _RATE_POINTS[1:], strict=False):
        if s0 <= s <= s1:
            return round(d0 + (d1 - d0) * (s - s0) / (s1 - s0), 4)
    return 0.0


def _threads(cores: int | None = None) -> int:
    from quill.core.onnx_threads import kokoro_threads

    return kokoro_threads(cores)


_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {}
_THREADS_SET = False


def _get_cached_phonon(model_dir: Path) -> Any:
    """A shared ``ptts.TTS`` for *model_dir*, built once and kept warm."""
    global _THREADS_SET
    from quill.core import lifecycle_service

    key = str(model_dir)
    with _LOCK:
        instance = _CACHE.get(key)
        if instance is None:
            status = phonon_status(model_dir)
            if status != "ready":
                from quill.core.read_aloud import PhononUnavailableError

                raise PhononUnavailableError(unavailable_message(status))
            import ptts  # type: ignore[import-not-found,import-untyped,unused-ignore]

            lifecycle_service.reserve("tts:phonon")
            if not _THREADS_SET:
                # Sizes a global pool that is built once, so only the first call counts.
                ptts.set_num_threads(_threads())
                _THREADS_SET = True
            instance = ptts.TTS(
                model=str(model_dir),
                lang="en",
                quant=_QUANT,
                voice_catalog=str(model_dir / "voices.jsonl"),
            )
            _CACHE[key] = instance
            lifecycle_service.note_loaded("tts:phonon", clear_phonon_cache)
    lifecycle_service.touch("tts:phonon")
    return instance


def clear_phonon_cache() -> None:
    """Drop the loaded model (about 280 MB); the next call reloads it."""
    from quill.core import lifecycle_service

    with _LOCK:
        _CACHE.clear()
    lifecycle_service.note_unloaded("tts:phonon")


# Phonon reads one passage per call; very long passages are split here so a
# single failure costs a sentence, not a chapter (phononprd.md R-33).
_MAX_CHARS = 600


def _pieces(text: str) -> list[str]:
    if len(text) <= _MAX_CHARS:
        return [text]
    from quill.core.sentence_split import sentence_spans

    out: list[str] = []
    current = ""
    for span in sentence_spans(text):
        part = text[span.start : span.end]
        if current and len(current) + len(part) > _MAX_CHARS:
            out.append(current)
            current = ""
        current += part
    if current:
        out.append(current)
    return [p for p in out if p.strip()] or [text]


def synthesize_with_phonon(
    text: str,
    output_path: Path,
    *,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
    model_dir: Path | None = None,
) -> Path:
    """Speak *text* into a mono 16-bit WAV at *output_path*."""
    import numpy as np

    directory = model_dir or default_phonon_model_dir()
    if directory is None:
        from quill.core.read_aloud import PhononUnavailableError

        raise PhononUnavailableError(unavailable_message("model"))
    tts = _get_cached_phonon(directory)
    chosen = None if not voice or voice == DEFAULT_VOICE else voice
    parts: list[Any] = []
    with _LOCK:  # one model, one set of conditions: callers take turns
        tts.set_conditions({"duration_delta": duration_delta_for_speed(speed)})
        for piece in _pieces(text):
            parts.append(np.asarray(tts.synth(piece, voice=chosen), dtype=np.float32).reshape(-1))
        rate = int(tts.sample_rate)
    audio = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm)
    return output_path
