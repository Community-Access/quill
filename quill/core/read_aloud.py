from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.punctuation_speech import normalize_punctuation_level, verbalize_punctuation
from quill.core.sentence_split import SentenceSpan, sentence_spans
from quill.core.speech.text_polish import clean_markdown_text
from quill.core.tts_cache import cached_sentence_generator

# The static voice tables live in voice_catalog (GATE-11 extract). Only the
# names this module itself uses are imported; catalog-only consumers import
# straight from quill.core.voice_catalog.
from quill.core.voice_catalog import (
    ESPEAK_ACCENTS,
    ESPEAK_ENGLISH_VOICES,
    ESPEAK_WORLD_VOICES,
    KOKORO_ACCENTS,
    KOKORO_LANG_BY_LETTER,
    KOKORO_VOICES,
    PIPER_ACCENTS_BY_LANG,
    PIPER_VOICES,
    kokoro_lang_for_voice,
)

# Windows system speech (SAPI 5) is reached through
# quill.platform.windows.sapi5, imported lazily inside the functions that need
# it so quill.core stays importable on non-Windows and keeps no import-time
# dependency on the platform layer.

try:
    import winsound as _winsound  # type: ignore[import]
except ImportError:  # pragma: no cover - non-Windows
    _winsound = None  # type: ignore[assignment]


def _detect_live_wav_backend() -> str:
    """Return the live WAV playback backend: ``'winsound'``, ``'afplay'``, or ``''``.

    Read Aloud plays generated per-sentence WAVs through this. ``winsound`` is
    Windows-only; on macOS there is no stdlib equivalent, so without an
    ``afplay`` fallback Piper/Kokoro/ElevenLabs synthesized a WAV and then
    silently deleted it without ever playing it (finding #28). ``afplay`` ships
    with macOS, so no new dependency is added.
    """
    if _winsound is not None:
        return "winsound"
    if sys.platform == "darwin" and shutil.which("afplay"):
        return "afplay"
    return ""


class _LiveWavPlayer:
    """Play one WAV file at a time, blocking, with cross-thread interrupt.

    Wraps the platform's synchronous WAV playback so :meth:`_run_wav_sentences`
    can stay platform-neutral: ``play(path)`` blocks until the sound finishes
    (or is stopped), and ``stop()`` interrupts an in-progress playback from
    another thread.
    """

    def __init__(self, backend: str | None = None) -> None:
        self._backend = backend if backend is not None else _detect_live_wav_backend()
        self._proc: subprocess.Popen[bytes] | None = None
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self._backend != ""

    def play(self, path: Path) -> None:
        if self._backend == "winsound" and _winsound is not None:
            _winsound.PlaySound(  # type: ignore[union-attr]
                str(path),
                _winsound.SND_FILENAME | _winsound.SND_NODEFAULT,
            )
        elif self._backend == "afplay":
            try:
                with self._lock:
                    self._proc = subprocess.Popen(  # noqa: S603
                        ["afplay", str(path)]
                    )
                try:
                    self._proc.wait()
                finally:
                    with self._lock:
                        self._proc = None
            except OSError:
                pass
        # No backend: play() is a silent no-op (matches the prior winsound-None
        # behavior, but now _detect_live_wav_backend makes that an edge case
        # rather than the entire macOS platform).

    def stop(self) -> None:
        if self._backend == "winsound" and _winsound is not None:
            try:
                _winsound.PlaySound(None, _winsound.SND_PURGE)
            except Exception:  # noqa: BLE001
                pass
        with self._lock:
            proc = self._proc
        if proc is not None:
            try:
                proc.terminate()
            except Exception:  # noqa: BLE001
                pass


@dataclass(frozen=True, slots=True)
class VoiceOption:
    id: str
    name: str
    accent: str = ""
    description: str = ""
    installed: bool = True
    language: str = ""  # ISO base subtag when known (e.g. "es" for a Spanish voice)


_MAX_SYNTHESIS_SECONDS: float = 120.0

DECTALK_VOICE_COMMANDS: dict[str, str] = {
    "paul": "[:np]",
    "harry": "[:nh]",
    "dennis": "[:nd]",
    "frank": "[:nf]",
    "betty": "[:nb]",
    "ursula": "[:nu]",
    "rita": "[:nr]",
    "wendy": "[:nw]",
    "kit": "[:nk]",
}

KOKORO_ONNX_MODEL_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download"
    "/model-files-v1.0/kokoro-v1.0.int8.onnx"
)
KOKORO_ONNX_VOICES_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
)
KOKORO_ONNX_MODEL_FILENAME = "kokoro-v1.0.int8.onnx"
KOKORO_ONNX_VOICES_FILENAME = "voices-v1.0.bin"


def default_piper_model_dir() -> Path:
    from quill.core.paths import app_data_dir

    return app_data_dir() / "piper-models"


def resolve_piper_model_path(voice_id: str, model_dir: Path | None = None) -> Path:
    """The on-disk ``.onnx`` file for a catalog voice id.

    Mirrors the exact check :func:`list_piper_catalog_voices` uses to decide a
    voice is installed, so callers that synthesize from a voice id resolve the
    same file the catalog already confirmed exists -- a bare voice id (e.g.
    ``"en_GB-alan-medium"``) is not itself a usable path.
    """
    d = model_dir if model_dir is not None else default_piper_model_dir()
    return d / f"{voice_id}.onnx"


def list_piper_catalog_voices(model_dir: Path | None = None) -> list[VoiceOption]:
    """Return all catalog Piper voices with download status and accent metadata."""
    d = model_dir if model_dir is not None else default_piper_model_dir()
    result = []
    for voice_id, display_name in PIPER_VOICES:
        downloaded = (d / f"{voice_id}.onnx").exists()
        accent = PIPER_ACCENTS_BY_LANG.get(voice_id.split("-", 1)[0], "English")
        # Extract quality from name, e.g. "medium" from "Alan (British, medium)"
        desc = ""
        if "(" in display_name and ")" in display_name:
            inner = display_name[display_name.index("(") + 1 : display_name.rindex(")")]
            parts = [p.strip() for p in inner.split(",")]
            desc = parts[-1] if len(parts) > 1 else ""
        short_name = display_name.split(" (")[0]
        suffix = "" if downloaded else " [not downloaded]"
        result.append(
            VoiceOption(
                id=voice_id,
                name=f"{short_name}{suffix}",
                accent=accent,
                description=desc,
                installed=downloaded,
            )
        )
    return result


def _validate_configured_executable(
    configured_path: str, expected_names: tuple[str, ...]
) -> Path | None:
    """Validate a user-configured speech-engine executable path.

    A tampered settings file must not be able to launch an arbitrary program.
    The configured value is accepted only when it points at an existing regular
    file whose name matches one of the canonical executable names for this
    engine; anything else (a missing file, a directory, or an unexpected
    binary such as ``cmd.exe``) is rejected.
    """
    raw = configured_path.strip()
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    try:
        if not candidate.is_file():
            return None
    except OSError:
        return None
    allowed = {name.lower() for name in expected_names}
    if candidate.name.lower() not in allowed:
        return None
    return candidate.resolve()


def discover_dectalk_executable(configured_path: str = "") -> Path | None:
    """Locate the DECtalk synthesis runtime, returning the ``DECtalk.dll`` path.

    Synthesis is driven through ``DECtalk.dll`` directly (see
    :mod:`quill.core.speech.dectalk_say`), never through ``speak.exe`` -- the
    package's ``AMD64/speak.exe`` is the *graphical* "Sample Speak Window" and
    fast-fails (0xC000041D) when launched as a console program. A configured
    path may point at ``DECtalk.dll`` or at the folder containing it; a
    configured ``speak.exe`` is rejected rather than silently honoured.

    The historical name is kept because callers thread the returned path back in
    as ``executable_path``; it is now the DLL, which the worker understands.
    """
    raw = configured_path.strip()
    if raw:
        candidate = Path(raw).expanduser()
        if candidate.is_dir():
            candidate = candidate / "DECtalk.dll"
        if candidate.name.lower() == "dectalk.dll" and candidate.is_file():
            return candidate.resolve()
        # A stale speak.exe path (or anything else) falls through to discovery.

    relatives = (
        "DECtalk.dll",
        "AMD64/DECtalk.dll",
        "IA32/DECtalk.dll",
        "release/AMD64/DECtalk.dll",
        "release/DECtalk.dll",
    )
    roots: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        roots.append(Path(app_root) / "tools" / "speech" / "dectalk")
    from quill.core.paths import app_data_dir

    roots.append(app_data_dir() / "speech" / "dectalk")
    for root in roots:
        for relative in relatives:
            probe = root / relative
            if probe.is_file():
                return probe.resolve()
    return None


def discover_piper_executable(configured_path: str = "") -> Path | None:
    validated = _validate_configured_executable(configured_path, ("piper.exe", "piper"))
    if validated is not None:
        return validated
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        bundled = Path(app_root) / "tools" / "speech" / "piper"
        for relative in ("piper.exe", "piper/piper.exe"):
            probe = bundled / relative
            if probe.exists():
                return probe.resolve()
    # Also check the user-data download location (set by in-app Piper download).
    from quill.core.paths import app_data_dir

    managed = app_data_dir() / "speech" / "piper"
    for relative in ("piper.exe", "piper/piper.exe"):
        probe = managed / relative
        if probe.exists():
            return probe.resolve()
    found = shutil.which("piper") or shutil.which("piper.exe")
    if found:
        return Path(found).resolve()
    return None


def build_piper_command(
    executable_path: Path,
    model_path: Path,
    output_path: Path,
    *,
    length_scale: float | None = None,
    noise_scale: float | None = None,
    noise_w: float | None = None,
) -> list[str]:
    """Build the Piper argv, appending the optional synthesis-shaping flags.

    ``length_scale`` slows (>1) or speeds (<1) speech; ``noise_scale`` and
    ``noise_w`` vary timbre/cadence. Each is omitted when None so Piper uses the
    model's defaults. Pure and unit-tested.
    """
    command = [
        str(executable_path),
        "--model",
        str(model_path),
        "--output_file",
        str(output_path),
    ]
    if length_scale is not None:
        command += ["--length_scale", f"{float(length_scale):g}"]
    if noise_scale is not None:
        command += ["--noise_scale", f"{float(noise_scale):g}"]
    if noise_w is not None:
        command += ["--noise_w", f"{float(noise_w):g}"]
    return command


def synthesize_with_piper(
    text: str,
    output_path: Path,
    *,
    executable_path: Path,
    model_path: Path,
    length_scale: float | None = None,
    noise_scale: float | None = None,
    noise_w: float | None = None,
) -> None:
    if not text.strip():
        raise ReadAloudUnavailableError("Cannot generate speech from empty text")
    if not executable_path.exists():
        raise ReadAloudUnavailableError("Piper executable was not found")
    if not model_path.exists():
        raise ReadAloudUnavailableError("Piper model file was not found")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        suffix=".txt",
        encoding="utf-8",
        errors="replace",
    ) as handle:
        handle.write(text)
        input_path = Path(handle.name)
    try:
        with input_path.open("rb") as stdin_fh:
            completed = subprocess.run(
                build_piper_command(
                    executable_path,
                    model_path,
                    output_path,
                    length_scale=length_scale,
                    noise_scale=noise_scale,
                    noise_w=noise_w,
                ),
                stdin=stdin_fh,
                capture_output=True,
                check=False,
                timeout=_MAX_SYNTHESIS_SECONDS,
                # No console window flash for screen-reader users (subprocess hardening).
                creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0)),
            )
    except subprocess.TimeoutExpired as exc:
        raise ReadAloudUnavailableError(
            f"Piper did not complete within {_MAX_SYNTHESIS_SECONDS:.0f} seconds."
        ) from exc
    finally:
        try:
            input_path.unlink(missing_ok=True)
        except OSError:
            pass
    if completed.returncode != 0:
        raw = completed.stderr or completed.stdout or b""
        detail = (raw.decode(errors="replace") if isinstance(raw, bytes) else str(raw)).strip()
        if detail:
            raise ReadAloudUnavailableError(f"Piper failed: {detail}")
        raise ReadAloudUnavailableError(
            f"Piper exited with code {completed.returncode}. Check executable and model settings."
        )


def discover_espeak_executable(configured_path: str = "") -> Path | None:
    validated = _validate_configured_executable(configured_path, ("espeak-ng.exe", "espeak-ng"))
    if validated is not None:
        return validated
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        bundled = Path(app_root) / "tools" / "speech" / "espeak-ng"
        for relative in (
            "espeak-ng.exe",
            "espeak-ng/espeak-ng.exe",
            "eSpeak NG/espeak-ng.exe",
        ):
            probe = bundled / relative
            if probe.exists():
                return probe.resolve()
    # Also check common user-data locations (installer or future in-app download).
    from quill.core.paths import app_data_dir

    managed = app_data_dir() / "speech" / "espeak-ng"
    for relative in (
        "espeak-ng.exe",
        "espeak-ng/espeak-ng.exe",
        "eSpeak NG/espeak-ng.exe",
    ):
        probe = managed / relative
        if probe.exists():
            return probe.resolve()
    import shutil as _shutil

    found = _shutil.which("espeak-ng")
    if found:
        return Path(found).resolve()
    return None


def list_kokoro_voices() -> list[VoiceOption]:
    ready = kokoro_onnx_ready()
    result = []
    for vid, display_name in KOKORO_VOICES:
        accent = KOKORO_ACCENTS.get(vid[:2], "English")
        # Extract style note: "warm" from "Heart (American Female, warm)"
        desc = ""
        if "(" in display_name and ")" in display_name:
            inner = display_name[display_name.index("(") + 1 : display_name.rindex(")")]
            parts = [p.strip() for p in inner.split(",")]
            desc = parts[-1] if len(parts) > 1 else ""
        result.append(
            VoiceOption(
                id=vid,
                name=display_name.split(" (")[0],
                accent=accent,
                description=desc,
                installed=ready,
            )
        )
    return result


def list_piper_voices(model_search_path: str = "") -> list[VoiceOption]:
    """Return ONNX model files found under model_search_path as voice options."""
    if not model_search_path.strip():
        return []
    root = Path(model_search_path).expanduser()
    if not root.exists():
        return []
    voices: list[VoiceOption] = []
    for onnx_file in sorted(root.rglob("*.onnx")):
        voices.append(VoiceOption(id=str(onnx_file), name=onnx_file.stem))
    return voices


def list_espeak_english_voices() -> list[VoiceOption]:
    return [
        VoiceOption(id=vid, name=name, accent=ESPEAK_ACCENTS.get(vid, "English"))
        for vid, name in ESPEAK_ENGLISH_VOICES
    ]


def list_espeak_voices() -> list[VoiceOption]:
    """The full eSpeak catalog: English variants plus the world languages."""
    world = [
        VoiceOption(id=vid, name=name, accent=name.split(" (")[0])
        for vid, name in ESPEAK_WORLD_VOICES
    ]
    return list_espeak_english_voices() + world


def _kokoro_dir_has_models(d: Path) -> bool:
    return (d / KOKORO_ONNX_MODEL_FILENAME).exists() and (d / KOKORO_ONNX_VOICES_FILENAME).exists()


def _bundled_kokoro_model_dir() -> Path | None:
    """A bundled kokoro-models dir shipped with the app, if present.

    Lets QUILL ship Kokoro in the installer (``{app}/kokoro-models``) so users
    don't have to download it, and lets a source run discover an installed
    copy via QUILL_APP_ROOT. Returns None when no bundled copy exists.
    """
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        bundled = Path(app_root) / "kokoro-models"
        if _kokoro_dir_has_models(bundled):
            return bundled
    return None


def default_kokoro_model_dir() -> Path:
    """Where Kokoro models live: a user-downloaded copy if present, else the
    bundled copy shipped with the app, else the (download target) data dir."""
    from quill.core.paths import app_data_dir

    data_dir = app_data_dir() / "kokoro-models"
    if _kokoro_dir_has_models(data_dir):
        return data_dir
    bundled = _bundled_kokoro_model_dir()
    return bundled if bundled is not None else data_dir


def kokoro_onnx_ready(model_dir: Path | None = None) -> bool:
    return _kokoro_dir_has_models(model_dir or default_kokoro_model_dir())


def kokoro_engine_ready(model_dir: Path | None = None) -> bool:
    """True when Kokoro can actually synthesize right now.

    ``kokoro_onnx_ready`` alone only checks that model *files* exist on disk --
    it says nothing about whether the ``kokoro_onnx`` pip package actually
    imports. A caller (a UI availability flag, or the synthesis path below)
    that trusts it alone can claim Kokoro is ready when the package install
    was skipped or failed, discovering the gap only at synthesis time (#2,
    beta-2 fix pass).
    """
    if not kokoro_onnx_ready(model_dir):
        return False
    from quill.core.speech.engine_install import is_kokoro_onnx_available

    return is_kokoro_onnx_available()


# Cache the loaded kokoro-onnx model so repeated synthesis (every section and,
# with a sentence pause, every sentence of a batch) reuses one ~88 MB model load
# instead of reloading it per call. The instance is stateless across calls
# (voice/speed are per-``create``); a lock serializes (re)creation so concurrent
# callers do not each build their own. Keyed by (model_path, voices_path).
_KOKORO_ONNX_LOCK = threading.Lock()
_KOKORO_ONNX_CACHE: dict[tuple[str, str], Any] = {}


def _get_cached_kokoro_onnx(model_dir: Path) -> Any:
    """Return a shared, lazily-built ``kokoro_onnx.Kokoro`` for *model_dir*."""
    from kokoro_onnx import Kokoro as _KokoroOnnx  # type: ignore[import-not-found,import-untyped]

    from quill.core import lifecycle_service

    model_path = str(model_dir / KOKORO_ONNX_MODEL_FILENAME)
    voices_path = str(model_dir / KOKORO_ONNX_VOICES_FILENAME)
    key = (model_path, voices_path)
    with _KOKORO_ONNX_LOCK:
        instance = _KOKORO_ONNX_CACHE.get(key)
        if instance is None:
            # Low-resource mode may evict another engine before we build this one.
            lifecycle_service.reserve("tts:kokoro")
            instance = _KokoroOnnx(model_path, voices_path)
            _KOKORO_ONNX_CACHE[key] = instance
            lifecycle_service.note_loaded("tts:kokoro", clear_kokoro_cache)
    lifecycle_service.touch("tts:kokoro")
    return instance


def clear_kokoro_cache() -> None:
    """Drop the cached kokoro-onnx model (frees ~88 MB); the next call reloads it."""
    from quill.core import lifecycle_service

    with _KOKORO_ONNX_LOCK:
        _KOKORO_ONNX_CACHE.clear()
    lifecycle_service.note_unloaded("tts:kokoro")


def warm_kokoro_onnx() -> bool:
    """Load the Kokoro ONNX model into the shared cache now (best-effort).

    Returns True when a model was available and loaded (or already cached), so a
    startup prewarm makes the first preview/synthesis fast instead of paying the
    ~88 MB load on the first user action.
    """
    model_dir = default_kokoro_model_dir()
    if not kokoro_onnx_ready(model_dir):
        return False
    try:
        _get_cached_kokoro_onnx(model_dir)
        return True
    except Exception:  # noqa: BLE001 - prewarm is best-effort
        # Best-effort, but log why: a prewarm failure here is the same
        # onnxruntime/model load error that will otherwise surface only as the
        # generic fallback message at first synthesis (#kokoro-onnx).
        logging.getLogger(__name__).debug("Kokoro onnx prewarm failed", exc_info=True)
        return False


def synthesize_with_kokoro(
    text: str,
    output_path: Path,
    *,
    voice: str = "af_heart",
    speed: float = 1.0,
) -> None:
    if not text.strip():
        raise ReadAloudUnavailableError("Cannot generate speech from empty text")

    # Try kokoro-onnx first — no torch required, just onnxruntime (~20 MB).
    # Uses the int8 quantized model downloaded to the default model directory.
    model_dir = default_kokoro_model_dir()
    if kokoro_engine_ready(model_dir):
        try:
            import numpy as _np  # type: ignore[import]
            import soundfile as _sf  # type: ignore[import]

            output_path.parent.mkdir(parents=True, exist_ok=True)
            lang = kokoro_lang_for_voice(voice)
            _k = _get_cached_kokoro_onnx(model_dir)
            samples, sample_rate = _k.create(text, voice=voice, speed=float(speed), lang=lang)
            _sf.write(str(output_path), _np.array(samples), sample_rate)
            return
        except Exception:  # noqa: BLE001 - fall through to kokoro + torch
            # The onnx path is the primary route once kokoro_engine_ready() is
            # True (models present + kokoro_onnx importable). If it still throws
            # -- e.g. onnxruntime cannot load its native DLL, or the model is
            # unreadable -- the fallback below raises a generic "needs a
            # component" error that hides the real cause (a freshly downloaded
            # Kokoro that will not speak). Log the true error so Help > Save
            # Diagnostics captures it instead of losing it here (#kokoro-onnx).
            logging.getLogger(__name__).exception(
                "Kokoro onnx synthesis failed; falling back to kokoro+torch"
            )

    # Fall back to kokoro + torch.
    try:
        from kokoro import KPipeline  # type: ignore[attr-defined]
    except ImportError as exc:
        raise ReadAloudUnavailableError(
            "Kokoro voices need one more component. "
            "Tools > Speech > Install Kokoro ONNX will fetch it (~114 MB).\n"
            "(Advanced: the 'kokoro' package with torch also works, but needs "
            "~2 GB: pip install kokoro)"
        ) from exc
    try:
        import numpy as np  # type: ignore[import]
    except ImportError as exc:
        raise ReadAloudUnavailableError("Kokoro TTS requires the 'numpy' package") from exc
    try:
        import soundfile as sf  # type: ignore[import]
    except ImportError as exc:
        raise ReadAloudUnavailableError(
            "Kokoro audio saving requires the 'soundfile' package (pip install soundfile)"
        ) from exc
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lang_code = voice[:1].lower() if voice[:1].lower() in KOKORO_LANG_BY_LETTER else "a"
    pipeline = KPipeline(lang_code=lang_code)
    samples_list: list[np.ndarray] = []
    for _g, _p, audio in pipeline(text, voice=voice, speed=float(speed)):
        if audio is not None and len(audio) > 0:
            samples_list.append(audio)
    if not samples_list:
        raise ReadAloudUnavailableError("Kokoro produced no audio output")
    sf.write(str(output_path), np.concatenate(samples_list), 24000)


def synthesize_with_espeak(
    text: str,
    output_path: Path,
    *,
    executable_path: Path,
    voice: str = "en",
    rate: int = 175,
    pitch: int | None = None,
    word_gap_ms: int | None = None,
) -> None:
    if not text.strip():
        raise ReadAloudUnavailableError("Cannot generate speech from empty text")
    if not executable_path.exists():
        raise ReadAloudUnavailableError("eSpeak-NG executable was not found")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bounded_rate = max(80, min(450, int(rate)))
    command = [
        str(executable_path),
        "-v",
        voice,
        "-s",
        str(bounded_rate),
        "-w",
        str(output_path),
    ]
    # Optional voice shaping: -p pitch (0-99), -g word gap in 10 ms units.
    if pitch is not None:
        command += ["-p", str(max(0, min(99, int(pitch))))]
    if word_gap_ms is not None:
        command += ["-g", str(max(0, int(word_gap_ms) // 10))]
    # SSML/markup input (an assembled <speak> utterance) needs eSpeak-NG's markup
    # mode (-m); otherwise the tags would be read aloud literally.
    if text.lstrip().startswith("<speak"):
        command.append("-m")
    # A portable / managed eSpeak-NG (the in-app download and the bundled copy)
    # ships its espeak-ng-data beside the executable. Without --path eSpeak-NG
    # falls back to a compiled-in/registry data path that does not exist for a
    # portable copy and crashes (access violation) instead of failing cleanly,
    # so point it explicitly at the co-located data directory when present.
    if (executable_path.parent / "espeak-ng-data").is_dir():
        command.append(f"--path={executable_path.parent}")
    command.append(text)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            timeout=_MAX_SYNTHESIS_SECONDS,
            # No console window flash for screen-reader users (subprocess hardening).
            creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0)),
        )
    except subprocess.TimeoutExpired as exc:
        raise ReadAloudUnavailableError(
            f"eSpeak-NG did not complete within {_MAX_SYNTHESIS_SECONDS:.0f} seconds."
        ) from exc
    if completed.returncode != 0:
        raw = completed.stderr or completed.stdout or b""
        detail = (
            raw.decode("utf-8", errors="replace").strip()
            if isinstance(raw, bytes)
            else str(raw).strip()
        )
        raise ReadAloudUnavailableError(
            f"eSpeak-NG failed: {detail}"
            if detail
            else f"eSpeak-NG exited with code {completed.returncode}."
        )


def sapi5_available() -> bool:
    """True when Windows SAPI 5 speech can be reached on this machine."""
    try:
        from quill.platform.windows import sapi5

        return sapi5.available()
    except Exception:  # noqa: BLE001 - any failure means SAPI is unusable
        return False


def synthesize_to_file_with_sapi5(
    text: str,
    output_path: Path,
    *,
    voice: str = "",
    rate: int = 200,
    volume: float = 1.0,
) -> None:
    """Synthesize ``text`` to a WAV file via Windows SAPI 5 (the system voice)."""
    if not text.strip():
        raise ReadAloudUnavailableError("Cannot generate speech from empty text")
    from quill.platform.windows import sapi5

    if not sapi5.available():
        raise ReadAloudUnavailableError("Windows SAPI 5 speech is not available")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        sapi5.synthesize_to_wav(
            text, output_path, voice_id=voice, rate_wpm=int(rate), volume=float(volume)
        )
    except RuntimeError as exc:
        raise ReadAloudUnavailableError(str(exc)) from exc


_DECTALK_SAY_WORKER = Path(__file__).resolve().parent / "speech" / "dectalk_say.py"


def build_dectalk_payload(text: str, voice: str, rate: int) -> str:
    """Compose a DECtalk command string: voice + rate command + text."""
    voice_cmd = DECTALK_VOICE_COMMANDS.get(voice.strip().lower(), "")
    bounded_rate = max(75, min(650, int(rate)))
    return f"{voice_cmd} [:ra {bounded_rate}] {text}".strip()


def synthesize_to_file_with_dectalk(
    text: str,
    output_path: Path,
    *,
    executable_path: Path,
    voice: str = "paul",
    rate: int = 180,
    dictionary_path: Path | None = None,  # noqa: ARG001 - kept for call compatibility
) -> None:
    """Synthesize DECtalk speech to ``output_path`` (WAV) via ``DECtalk.dll``.

    ``executable_path`` is the ``DECtalk.dll`` produced by
    :func:`discover_dectalk_executable`. Synthesis is delegated to the
    out-of-process console worker (:mod:`quill.core.speech.dectalk_say`), which
    loads the DLL with the audio device disabled and validates the wave output.
    ``dictionary_path`` is accepted but unused: DECtalk locates ``dtalk_us.dic``
    from its own runtime folder, and it is the system dictionary, not a ``-d``
    user dictionary.
    """
    if not text.strip():
        raise ReadAloudUnavailableError("Cannot generate speech from empty text")
    if not executable_path.exists():
        raise ReadAloudUnavailableError(
            f"DECtalk runtime (DECtalk.dll) was not found at {executable_path}."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_dectalk_payload(text, voice, rate)
    _run_dectalk_say(executable_path, payload, output_path)


def _worker_python_executable() -> str:
    """A real Python interpreter for running helper scripts (e.g. dectalk_say.py).

    In a bundled build ``sys.executable`` is the QUILL launcher (``quill.exe``),
    not a Python interpreter -- launching it with a bare script path makes QUILL
    *open the script as a document* instead of running it (the "DECtalk opens a
    Python file" bug). The embedded runtime ships ``pythonw.exe``/``python.exe``
    beside the launcher, so prefer one of those when the launcher isn't itself
    Python.
    """
    exe = Path(sys.executable)
    if exe.stem.lower() in ("python", "pythonw"):
        return str(exe)
    for name in ("pythonw.exe", "python.exe"):
        candidate = exe.with_name(name)
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _run_dectalk_say(dll_path: Path, payload: str, output_path: Path) -> None:
    """Drive the DECtalk console worker; raise with a rich diagnostic on failure.

    The payload is encoded as Windows-1252 (replacing unsupported characters),
    the encoding the legacy ``char *`` DECtalk API expects; UTF-8 bytes would be
    mis-spoken for non-ASCII text.
    """
    if not _DECTALK_SAY_WORKER.exists():
        raise ReadAloudUnavailableError(f"DECtalk worker script is missing: {_DECTALK_SAY_WORKER}")
    create_no_window = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        completed = subprocess.run(
            [
                _worker_python_executable(),
                str(_DECTALK_SAY_WORKER),
                "--dll",
                str(dll_path),
                "-w",
                str(output_path),
            ],
            input=payload.encode("cp1252", errors="replace"),
            capture_output=True,
            creationflags=create_no_window,
            check=False,
            timeout=_MAX_SYNTHESIS_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ReadAloudUnavailableError(
            f"DECtalk did not complete within {_MAX_SYNTHESIS_SECONDS:.0f} seconds."
        ) from exc
    if completed.returncode != 0:
        detail = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
        code = completed.returncode & 0xFFFFFFFF
        raise ReadAloudUnavailableError(
            f"DECtalk synthesis failed (exit 0x{code:08X})."
            + (f" {detail}" if detail else "")
            + f" [dll={dll_path}]"
        )


def list_dectalk_voices() -> list[VoiceOption]:
    return [
        VoiceOption(id="paul", name="Paul", accent="American English", description="Male"),
        VoiceOption(id="harry", name="Harry", accent="American English", description="Male"),
        VoiceOption(id="dennis", name="Dennis", accent="American English", description="Male"),
        VoiceOption(id="frank", name="Frank", accent="American English", description="Male"),
        VoiceOption(id="betty", name="Betty", accent="American English", description="Female"),
        VoiceOption(id="ursula", name="Ursula", accent="American English", description="Female"),
        VoiceOption(id="rita", name="Rita", accent="American English", description="Female"),
        VoiceOption(id="wendy", name="Wendy", accent="American English", description="Female"),
        VoiceOption(id="kit", name="Kit", accent="American English", description="Child"),
    ]


def list_voices() -> list[VoiceOption]:
    """Return the installed Windows SAPI 5 voices as read-aloud options."""
    from quill.platform.windows import sapi5

    return [
        VoiceOption(id=v.id, name=v.name, language=getattr(v, "language", ""))
        for v in sapi5.list_voices()
    ]


def list_elevenlabs_voices(api_key: str) -> list[VoiceOption]:
    """The ElevenLabs account's voices as read-aloud options, or ``[]``.

    A read-only network call. Returns ``[]`` when there is no key, the optional SDK is
    absent, or the call fails, so the caller can offer ElevenLabs voices without ever
    raising into the UI. The actual synthesis is gated by per-session consent and Safe
    Mode at the point of use.
    """
    key = (api_key or "").strip()
    if not key:
        return []
    from quill.core.ai import elevenlabs_tts

    if not elevenlabs_tts.available():
        return []
    try:
        return [
            VoiceOption(id=vid, name=name, language="")
            for vid, name in elevenlabs_tts.list_voices(key)
        ]
    except Exception:  # noqa: BLE001 - listing voices must never raise into the UI
        return []


class ReadAloudUnavailableError(RuntimeError):
    pass


class ReadAloudController:
    def __init__(self) -> None:
        self._state = "idle"
        self._cursor = 0
        self._thread: threading.Thread | None = None
        self._active_process: subprocess.Popen[bytes] | None = None
        self._active_wav_thread: threading.Thread | None = None
        self._wav_player = _LiveWavPlayer()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()
        self._sentence_pause_ms = 0
        self._punctuation_level = "some"
        self._cache_seed: tuple[object, ...] = ()
        self._pron_dicts: list[Any] = []
        self._pron_engine = "sapi5"

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def cursor(self) -> int:
        with self._lock:
            return self._cursor

    def start(  # noqa: PLR0912,PLR0913
        self,
        text: str,
        cursor: int,
        voice_id: str,
        *,
        engine_name: str = "sapi5",
        rate: int | None = None,
        volume: float | None = None,
        pitch: int | None = None,
        dectalk_executable: str = "",
        dectalk_voice: str = "",
        dectalk_rate: int = 180,
        dectalk_dictionary: str = "",
        piper_executable: str = "",
        piper_model: str = "",
        kokoro_voice: str = "af_heart",
        kokoro_speed: float = 1.0,
        espeak_executable: str = "",
        espeak_voice: str = "en",
        espeak_rate: int = 175,
        elevenlabs_api_key: str = "",
        elevenlabs_voice: str = "",
        elevenlabs_model: str = "",
        sentence_pause_ms: int = 0,
        punctuation_level: str = "some",
        end: int | None = None,
        pronunciation_dictionaries: list[Any] | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        on_state_change: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        normalized_engine = engine_name.strip().lower() or "sapi5"
        if normalized_engine == "pyttsx3":  # migrate the retired engine id
            normalized_engine = "sapi5"
        _valid_engines = {
            "sapi5",
            "dectalk",
            "piper",
            "kokoro",
            "espeak",
            "elevenlabs",
        }
        if normalized_engine == "sapi5" and not sapi5_available():
            raise ReadAloudUnavailableError("Windows SAPI 5 speech is not available")
        if normalized_engine == "dectalk":
            if discover_dectalk_executable(dectalk_executable) is None:
                raise ReadAloudUnavailableError("DECtalk executable was not found")
        if normalized_engine == "piper":
            if discover_piper_executable(piper_executable) is None:
                raise ReadAloudUnavailableError("Piper executable was not found")
            _mdl = Path(piper_model).expanduser() if piper_model.strip() else None
            if _mdl is None or not _mdl.exists():
                raise ReadAloudUnavailableError("Piper model (.onnx) file was not found")
        if normalized_engine == "espeak" and discover_espeak_executable(espeak_executable) is None:
            raise ReadAloudUnavailableError(
                "eSpeak-NG executable was not found. "
                "Install eSpeak-NG or configure the path in Read Aloud Settings."
            )
        if normalized_engine == "elevenlabs":
            from quill.core.ai import elevenlabs_tts

            if os.environ.get("QUILL_SAFE_MODE") == "1":
                raise ReadAloudUnavailableError("ElevenLabs Read Aloud is disabled in Safe Mode.")
            if not elevenlabs_api_key.strip():
                raise ReadAloudUnavailableError("Connect ElevenLabs to use its Read Aloud voice.")
            if not elevenlabs_tts.available():
                raise ReadAloudUnavailableError(
                    "ElevenLabs support needs the optional SDK. "
                    "Install it with: pip install quill[elevenlabs]"
                )
        if normalized_engine not in _valid_engines:
            raise ReadAloudUnavailableError(f"Unsupported read-aloud engine: {normalized_engine}")
        self.stop()
        self._sentence_pause_ms = max(0, int(sentence_pause_ms))
        self._punctuation_level = normalize_punctuation_level(punctuation_level)
        self._pron_dicts = pronunciation_dictionaries or []
        self._pron_engine = normalized_engine
        spans = [span for span in sentence_spans(text) if span.end > cursor]
        if end is not None:
            spans = [span for span in spans if span.start < end]
        if not spans:
            stop_at = len(text) if end is None else min(len(text), max(cursor, end))
            spans = [SentenceSpan(cursor, stop_at)]
        with self._lock:
            self._state = "playing"
            self._cursor = cursor
        self._stop_event.clear()
        self._pause_event.clear()

        def worker() -> None:
            try:
                if normalized_engine == "sapi5":
                    self._run_sapi5(
                        spans,
                        text,
                        voice_id=voice_id,
                        rate=rate,
                        volume=volume,
                        on_progress=on_progress,
                    )
                elif normalized_engine == "dectalk":
                    self._run_dectalk(
                        spans,
                        text,
                        executable=discover_dectalk_executable(dectalk_executable)
                        or Path(dectalk_executable).expanduser(),
                        voice_id=dectalk_voice,
                        rate=dectalk_rate,
                        dictionary_path=Path(dectalk_dictionary).expanduser()
                        if dectalk_dictionary.strip()
                        else None,
                        on_progress=on_progress,
                    )
                elif normalized_engine == "piper":
                    self._run_piper_live(
                        spans,
                        text,
                        executable=discover_piper_executable(piper_executable)
                        or Path(piper_executable).expanduser(),
                        model=Path(piper_model).expanduser(),
                        on_progress=on_progress,
                    )
                elif normalized_engine == "kokoro":
                    self._run_kokoro_live(
                        spans,
                        text,
                        voice=kokoro_voice,
                        speed=kokoro_speed,
                        on_progress=on_progress,
                    )
                elif normalized_engine == "espeak":
                    self._run_espeak_live(
                        spans,
                        text,
                        executable=discover_espeak_executable(espeak_executable)
                        or Path(espeak_executable).expanduser(),
                        voice=espeak_voice,
                        rate=espeak_rate,
                        on_progress=on_progress,
                    )
                elif normalized_engine == "elevenlabs":
                    self._run_elevenlabs_live(
                        spans,
                        text,
                        api_key=elevenlabs_api_key,
                        voice=elevenlabs_voice,
                        model=elevenlabs_model,
                        on_progress=on_progress,
                    )
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._state = "idle"
                if on_error is not None:
                    on_error(str(exc))
                if on_state_change is not None:
                    on_state_change("error")
                return

            with self._lock:
                if self._pause_event.is_set():
                    self._state = "paused"
                else:
                    self._state = "idle"
            if on_state_change is not None:
                on_state_change(self.state)

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def _inter_sentence_pause(self) -> None:
        """Wait the configured gap between sentences, interruptibly.

        Returns immediately if no pause is configured or as soon as a stop or
        pause is requested so the gap never delays a stop/pause response.
        """
        pause_ms = self._sentence_pause_ms
        if pause_ms <= 0:
            return
        deadline = time.monotonic() + pause_ms / 1000.0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            if self._stop_event.is_set() or self._pause_event.is_set():
                return
            time.sleep(min(0.05, remaining))

    def _run_sapi5(
        self,
        spans: list[SentenceSpan],
        text: str,
        *,
        voice_id: str,
        rate: int | None,
        volume: float | None,
        on_progress: Callable[[int, int], None] | None,
    ) -> None:
        """Play Windows SAPI 5 speech by synthesizing each sentence to WAV.

        Routing through the shared WAV-sentence player (like Piper/Kokoro/eSpeak)
        gives consistent pause/stop and sentence-cache behaviour. SAPI 5 has no
        pitch control via the simple property API, so ``pitch`` is not used.
        """
        effective_rate = 200 if rate is None else int(rate)
        effective_volume = 1.0 if volume is None else float(volume)

        def gen(sentence: str, out: Path) -> None:
            synthesize_to_file_with_sapi5(
                sentence, out, voice=voice_id, rate=effective_rate, volume=effective_volume
            )

        self._cache_seed = ("sapi5", voice_id, effective_rate, effective_volume)
        self._run_wav_sentences(spans, text, on_progress=on_progress, generate_sentence_wav=gen)

    def _run_dectalk(
        self,
        spans: list[SentenceSpan],
        text: str,
        *,
        executable: Path,
        voice_id: str,
        rate: int,
        dictionary_path: Path | None,  # noqa: ARG002 - kept for call compatibility
        on_progress: Callable[[int, int], None] | None,
    ) -> None:
        """Play DECtalk speech by synthesizing each sentence to WAV and playing it.

        ``executable`` is the ``DECtalk.dll`` runtime path. Synthesis goes
        through the out-of-process console worker (see
        :func:`synthesize_to_file_with_dectalk`), so the broken graphical
        ``speak.exe`` is never launched and live playback shares the same
        engine path as preview generation.
        """

        def gen(sentence: str, out: Path) -> None:
            synthesize_to_file_with_dectalk(
                sentence, out, executable_path=executable, voice=voice_id, rate=rate
            )

        self._cache_seed = ("dectalk", str(executable), voice_id, rate)
        self._run_wav_sentences(spans, text, on_progress=on_progress, generate_sentence_wav=gen)

    # ------------------------------------------------------------------
    # WAV-based engine helpers
    # ------------------------------------------------------------------

    def _apply_pronunciation(self, sentence: str) -> str:
        """Apply the active pronunciation dictionaries to one spoken sentence.

        Wired so corrections made in the manager are heard in live Read Aloud too,
        not just batch export (the shared-pipeline, "live everywhere" design). A
        no-op when no dictionaries are active.
        """
        dicts = getattr(self, "_pron_dicts", None)
        if not dicts:
            return sentence
        from quill.core.speech.pronunciation import apply_pronunciations

        try:
            return apply_pronunciations(sentence, self._pron_engine, dicts).text
        except Exception:  # noqa: BLE001 - a bad dictionary must never break read-aloud
            return sentence

    def _interrupt_wav(self) -> None:
        """Stop any in-progress WAV playback immediately (winsound or afplay)."""
        self._wav_player.stop()

    def _run_wav_sentences(
        self,
        spans: list[SentenceSpan],
        text: str,
        *,
        on_progress: Callable[[int, int], None] | None,
        generate_sentence_wav: Callable[[str, Path], None],
    ) -> None:
        """Generate per-sentence WAV then play via winsound."""
        generate_sentence_wav = cached_sentence_generator(self._cache_seed, generate_sentence_wav)
        first = True
        for span in spans:
            if self._stop_event.is_set() or self._pause_event.is_set():
                break
            sentence = text[span.start : span.end].strip()
            if not sentence:
                continue
            sentence = clean_markdown_text(sentence).strip()
            if not sentence:
                continue
            sentence = self._apply_pronunciation(sentence)
            if not sentence.lstrip().startswith("<speak"):
                # SSML utterances must reach the engine intact; verbalizing their
                # punctuation would corrupt the markup.
                sentence = verbalize_punctuation(sentence, self._punctuation_level)
            if not first:
                self._inter_sentence_pause()
            first = False
            if on_progress is not None:
                on_progress(span.start, span.end)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
                wav_path = Path(fh.name)
            try:
                generate_sentence_wav(sentence, wav_path)
                if self._stop_event.is_set() or self._pause_event.is_set():
                    break
                if self._wav_player.available and wav_path.exists():
                    play_done = threading.Event()

                    def _play(
                        p: Path = wav_path,
                        done: threading.Event = play_done,
                    ) -> None:
                        try:
                            self._wav_player.play(p)
                        except Exception:  # noqa: BLE001
                            pass
                        finally:
                            done.set()

                    wav_thread = threading.Thread(target=_play, daemon=True)
                    self._active_wav_thread = wav_thread
                    wav_thread.start()
                    while not play_done.wait(timeout=0.05):
                        if self._stop_event.is_set() or self._pause_event.is_set():
                            self._interrupt_wav()
                            play_done.wait(timeout=0.5)
                            break
                    self._active_wav_thread = None
            finally:
                try:
                    wav_path.unlink(missing_ok=True)
                except OSError:
                    pass
            with self._lock:
                self._cursor = span.end

    def _run_piper_live(
        self,
        spans: list[SentenceSpan],
        text: str,
        *,
        executable: Path,
        model: Path,
        on_progress: Callable[[int, int], None] | None,
    ) -> None:
        def gen(sentence: str, out: Path) -> None:
            synthesize_with_piper(sentence, out, executable_path=executable, model_path=model)

        self._cache_seed = ("piper", str(executable), str(model))
        self._run_wav_sentences(spans, text, on_progress=on_progress, generate_sentence_wav=gen)

    def _run_kokoro_live(
        self,
        spans: list[SentenceSpan],
        text: str,
        *,
        voice: str,
        speed: float,
        on_progress: Callable[[int, int], None] | None,
    ) -> None:
        def gen(sentence: str, out: Path) -> None:
            synthesize_with_kokoro(sentence, out, voice=voice, speed=speed)

        self._cache_seed = ("kokoro", voice, speed)
        self._run_wav_sentences(spans, text, on_progress=on_progress, generate_sentence_wav=gen)

    def _run_elevenlabs_live(
        self,
        spans: list[SentenceSpan],
        text: str,
        *,
        api_key: str,
        voice: str,
        model: str,
        on_progress: Callable[[int, int], None] | None,
    ) -> None:
        """ElevenLabs cloud voice: synthesize each sentence to WAV, then play it.

        Reuses the cached WAV runner, so a repeated sentence is not re-synthesized -
        saving cost and latency, since each fresh sentence is one billable ElevenLabs
        call. Stop/pause interrupt between sentences exactly as for the local engines.
        """
        from quill.core.ai import elevenlabs_tts

        chosen_voice = voice.strip() or elevenlabs_tts.DEFAULT_VOICE
        chosen_model = model.strip() or elevenlabs_tts.DEFAULT_MODEL

        def gen(sentence: str, out: Path) -> None:
            out.write_bytes(
                elevenlabs_tts.synthesize_wav(
                    sentence, api_key, voice=chosen_voice, model=chosen_model
                )
            )

        self._cache_seed = ("elevenlabs", chosen_voice, chosen_model)
        self._run_wav_sentences(spans, text, on_progress=on_progress, generate_sentence_wav=gen)

    def _run_espeak_live(
        self,
        spans: list[SentenceSpan],
        text: str,
        *,
        executable: Path,
        voice: str,
        rate: int,
        on_progress: Callable[[int, int], None] | None,
    ) -> None:
        """eSpeak-NG plays audio directly - track process for pause/stop."""
        create_no_window = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
        first = True
        for span in spans:
            if self._stop_event.is_set() or self._pause_event.is_set():
                break
            sentence = text[span.start : span.end].strip()
            if not sentence:
                continue
            sentence = clean_markdown_text(sentence).strip()
            if not sentence:
                continue
            sentence = self._apply_pronunciation(sentence)
            if not sentence.lstrip().startswith("<speak"):
                # SSML utterances must reach the engine intact; verbalizing their
                # punctuation would corrupt the markup.
                sentence = verbalize_punctuation(sentence, self._punctuation_level)
            if not first:
                self._inter_sentence_pause()
            first = False
            if on_progress is not None:
                on_progress(span.start, span.end)
            bounded_rate = max(80, min(450, int(rate)))
            process = subprocess.Popen(
                [str(executable), "-v", voice, "-s", str(bounded_rate), sentence],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=create_no_window,
            )
            self._active_process = process
            start = time.monotonic()
            while process.poll() is None:
                if self._stop_event.is_set() or self._pause_event.is_set():
                    process.terminate()
                    break
                if time.monotonic() - start >= _MAX_SYNTHESIS_SECONDS:
                    process.kill()
                    raise ReadAloudUnavailableError(
                        f"eSpeak-NG did not complete within {_MAX_SYNTHESIS_SECONDS:.0f} seconds."
                    )
                time.sleep(0.05)
            self._active_process = None
            exit_code = process.wait(timeout=2)
            if exit_code != 0 and not (self._stop_event.is_set() or self._pause_event.is_set()):
                raise ReadAloudUnavailableError(f"eSpeak-NG exited with code {exit_code}.")
            with self._lock:
                self._cursor = span.end

    def pause(self) -> None:
        with self._lock:
            if self._state != "playing":
                return
            self._state = "paused"
        self._pause_event.set()
        process = self._active_process
        if process is not None and process.poll() is None:
            process.terminate()
        self._interrupt_wav()

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.clear()
        process = self._active_process
        if process is not None and process.poll() is None:
            process.terminate()
        self._interrupt_wav()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=0.2)
        with self._lock:
            self._state = "idle"
        self._thread = None
