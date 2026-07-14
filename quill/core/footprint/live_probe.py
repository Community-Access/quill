"""Live per-engine footprint probes (cold-start / first-output timings).

The missing half of the Phase-0 footprint baseline (PRD §5.25f): the static
inventory in ``scripts/footprint_report.py`` measures installed size; this module
measures how long an engine takes to *load* (cold start) and produce its *first
output*, using each engine's real interface on a tiny synthetic input.

Design constraints (mirroring the static report):

- **Degrades, never crashes.** An absent engine, a missing model, or a failed
  import becomes a recorded note on the result, not a traceback. On a machine
  with no models installed every probe returns ``available`` with a note and no
  timings — never a fabricated number.
- **No fabrication.** A timing is either really measured or ``None``.
- **Peak RSS is measured by the parent.** Isolating an engine's peak memory
  needs its own process; :mod:`scripts.footprint_live` runs each probe in a
  subprocess and samples its RSS. This module fills every field except
  ``peak_rss_bytes``, which the parent attaches.

Wx-free and import-light: heavy engine imports happen only inside a probe.
"""

from __future__ import annotations

import contextlib
import tempfile
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

# A short, silent mono PCM clip is enough to exercise model load + one inference
# without shipping an audio fixture; every STT engine accepts 16 kHz mono WAV.
_PROBE_SECONDS = 1
_PROBE_RATE = 16000


@dataclass
class EngineTiming:
    """One engine's measured (or unavailable) footprint timings."""

    engine_id: str
    display_name: str
    available: bool
    model_id: str | None = None
    cold_start_s: float | None = None
    first_output_s: float | None = None
    total_s: float | None = None
    peak_rss_bytes: int | None = None  # filled by the parent (subprocess sampler)
    note: str = ""

    def to_json(self) -> dict[str, object]:
        return asdict(self)


def write_silent_wav(path: Path, *, seconds: int = _PROBE_SECONDS, rate: int = _PROBE_RATE) -> Path:
    """Write a mono 16-bit silent WAV of ``seconds`` — the probe's synthetic input."""
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * rate * seconds)
    return path


def probe_speech_provider(provider: object) -> EngineTiming:
    """Measure cold-start (model load) and first-output (one transcription).

    ``provider`` is a ``SpeechToTextProvider``. Returns an ``EngineTiming`` that
    is always safe to serialize: unavailable engines and model-less installs are
    reported via ``note`` with ``None`` timings, never a raised exception.
    """
    engine_id = str(getattr(provider, "id", "unknown"))
    display_name = str(getattr(provider, "display_name", engine_id))
    timing = EngineTiming(engine_id=engine_id, display_name=display_name, available=False)

    try:
        if not provider.is_available():  # type: ignore[attr-defined]
            timing.note = "engine not available (runtime/library missing)"
            return timing
        timing.available = True
        models = provider.list_installed_models()  # type: ignore[attr-defined]
        if not models:
            timing.note = "no model installed; nothing to time"
            return timing
        model_id = str(models[0].id)
        timing.model_id = model_id

        started = perf_counter()
        # Cold start: load the model if the engine exposes a warm() step.
        warm = getattr(provider, "warm", None)
        if callable(warm):
            cold0 = perf_counter()
            warm(model_id)
            timing.cold_start_s = round(perf_counter() - cold0, 3)

        from quill.core.speech.provider import TranscriptionRequest

        with tempfile.TemporaryDirectory() as tmp:
            wav = write_silent_wav(Path(tmp) / "probe.wav")
            first0 = perf_counter()
            provider.transcribe_file(  # type: ignore[attr-defined]
                TranscriptionRequest(source_path=wav, model_id=model_id)
            )
            timing.first_output_s = round(perf_counter() - first0, 3)
        timing.total_s = round(perf_counter() - started, 3)
    except Exception as exc:  # noqa: BLE001 - degrade to a note, never crash the run
        timing.note = f"probe failed: {exc.__class__.__name__}: {exc}".strip()
    finally:
        with contextlib.suppress(Exception):
            provider.unload()  # type: ignore[attr-defined]
    return timing


def list_speech_engine_ids() -> list[str]:
    """Ids of the registered speech providers (available or not)."""
    try:
        from quill.core.speech.service import default_registry

        return list(default_registry().ids())
    except Exception:  # noqa: BLE001 - no speech stack => nothing to probe
        return []


def run_engine_probe(engine_id: str) -> EngineTiming:
    """Resolve ``engine_id`` in the speech registry and probe it (child-process entry)."""
    try:
        from quill.core.speech.service import default_registry

        provider = default_registry().get(engine_id)
    except Exception as exc:  # noqa: BLE001
        return EngineTiming(
            engine_id=engine_id,
            display_name=engine_id,
            available=False,
            note=f"registry unavailable: {exc.__class__.__name__}",
        )
    if provider is None:
        return EngineTiming(
            engine_id=engine_id,
            display_name=engine_id,
            available=False,
            note="engine id not registered",
        )
    return probe_speech_provider(provider)


def merge_timings_into_baseline(
    baseline: dict[str, object], timings: list[EngineTiming]
) -> dict[str, object]:
    """Attach an ``engine_timings`` block to a footprint baseline dict (pure)."""
    merged = dict(baseline)
    merged["engine_timings"] = [t.to_json() for t in timings]
    return merged


__all__ = [
    "EngineTiming",
    "list_speech_engine_ids",
    "merge_timings_into_baseline",
    "probe_speech_provider",
    "run_engine_probe",
    "write_silent_wav",
]
