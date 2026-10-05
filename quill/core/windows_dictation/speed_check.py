"""The two-second check: can this computer keep up with a bigger speech model?

dict.md section 1 promised it and nothing had built it until the optional
models arrived (2026-10-05). It times the bundled Moonshine tiny, on one
processor thread, on two seconds of generated sound, and turns that into an
estimate for each optional model: Moonshine tiny's time here multiplied by the
model's measured cost relative to tiny
(:attr:`~quill.core.windows_dictation.model_catalog.DownloadableModel.cost_factor`,
measured on one machine on the same recordings).

Three answers, in plain words:

* within dict.md's budget (0.25 seconds of computing per second of speech on
  one thread) -- "should keep up comfortably";
* over the budget but able to keep up on the two threads dictation uses --
  it keeps up, but takes processor time the screen reader would otherwise have;
* well over -- "may lag behind your speech on this computer".

The person can still download and choose any model; the check only says what
to expect. No model is kept loaded afterwards: idle cost stays nothing.

Without the bundled model (a copy that lacks it) the check falls back to the
processor count and memory size, and says less.

wx-free; sherpa-onnx and numpy imported lazily, and the timing function is
injectable for tests.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass

from quill.core.windows_dictation.model_catalog import DownloadableModel

__all__ = [
    "BUDGET",
    "LAG_LIMIT",
    "LAG_SENTENCE",
    "SpeedCheck",
    "estimate",
    "run",
    "verdict",
]

#: dict.md section 1: seconds of computing per second of speech, one thread.
BUDGET = 0.25
#: Above this per-thread estimate even two threads fall behind a talker.
LAG_LIMIT = 1.2
LAG_SENTENCE = "may lag behind your speech on this computer"
_CLIP_SECONDS = 2.0
#: Moonshine tiny on speech, divided by Moonshine tiny on the generated probe,
#: on the measuring machine (2026-10-05: 0.054 / 0.019). The probe is shorter
#: work for the decoder than real words, and this puts it back.
_PROBE_TO_SPEECH = 2.8
#: What the fallback assumes Moonshine tiny costs on a weak and a capable machine.
_WEAK_TINY, _CAPABLE_TINY = 0.12, 0.05


@dataclass(frozen=True, slots=True)
class SpeedCheck:
    """What the check found: Moonshine tiny's speed here, cores and memory."""

    #: Seconds of computing per second of speech for Moonshine tiny on one
    #: thread here, or ``None`` when it could not be timed.
    tiny: float | None
    cores: int
    memory_gb: float | None

    @property
    def weak(self) -> bool:
        # 8 GB machines report 7.4 to 7.9 once Windows has reserved its share.
        return self.cores < 4 or (self.memory_gb is not None and self.memory_gb < 7.0)


def _memory_gb() -> float | None:
    try:
        import ctypes

        class _Status(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("load", ctypes.c_ulong),
                ("total", ctypes.c_ulonglong),
                ("free", ctypes.c_ulonglong),
                ("page_total", ctypes.c_ulonglong),
                ("page_free", ctypes.c_ulonglong),
                ("virtual_total", ctypes.c_ulonglong),
                ("virtual_free", ctypes.c_ulonglong),
                ("extended", ctypes.c_ulonglong),
            ]

        status = _Status()
        status.length = ctypes.sizeof(_Status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
            return None
        return round(float(status.total) / 1_073_741_824, 1)
    except Exception:  # noqa: BLE001 - not Windows, or no answer
        return None


def _probe() -> list[float]:
    """Two seconds of voice-like sound: a buzzing vowel that rises and falls."""
    import numpy as np

    t = np.arange(int(16_000 * _CLIP_SECONDS)) / 16_000
    voice = sum(np.sin(2 * np.pi * 140 * k * t) / k for k in range(1, 6))
    envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 3 * t)
    return list((0.2 * voice * envelope).astype(np.float32))


def _time_tiny() -> float | None:
    """Moonshine tiny's seconds per second of speech, one thread, or ``None``."""
    from quill.core.windows_dictation.engines import model_dir

    folder = model_dir("moonshine")
    if folder is None:
        return None
    from quill.core.windows_dictation.local_recognizer import _import_sherpa

    sherpa_onnx = _import_sherpa()
    recognizer = sherpa_onnx.OfflineRecognizer.from_moonshine(
        preprocessor=str(folder / "preprocess.onnx"),
        encoder=str(folder / "encode.int8.onnx"),
        uncached_decoder=str(folder / "uncached_decode.int8.onnx"),
        cached_decoder=str(folder / "cached_decode.int8.onnx"),
        tokens=str(folder / "tokens.txt"),
        num_threads=1,
        provider="cpu",
    )
    samples = _probe()
    best = None
    for _attempt in range(2):  # the first decode warms caches; keep the better
        stream = recognizer.create_stream()
        stream.accept_waveform(16_000, samples)
        started = time.perf_counter()
        recognizer.decode_stream(stream)
        took = time.perf_counter() - started
        best = took if best is None else min(best, took)
    assert best is not None
    return best / _CLIP_SECONDS * _PROBE_TO_SPEECH


def run(timer: Callable[[], float | None] | None = None) -> SpeedCheck:
    """Run the check. Blocking (about two seconds): call it on a worker."""
    try:
        tiny = (timer or _time_tiny)()
    except Exception:  # noqa: BLE001 - no engine, no numpy: fall back to the hardware
        tiny = None
    return SpeedCheck(tiny=tiny, cores=os.cpu_count() or 1, memory_gb=_memory_gb())


def estimate(model: DownloadableModel, check: SpeedCheck) -> float:
    """*model*'s expected seconds of computing per second of speech, one thread."""
    tiny = check.tiny
    if tiny is None:
        tiny = _WEAK_TINY if check.weak else _CAPABLE_TINY
    return tiny * model.cost_factor


def verdict(model: DownloadableModel, check: SpeedCheck | None) -> str:
    """One sentence about *model* on this computer, or ``""`` before the check."""
    if check is None:
        return ""
    speed = estimate(model, check)
    if speed > LAG_LIMIT:
        return f"On this computer, {model.name} {LAG_SENTENCE}."
    if speed > BUDGET:
        return (
            f"{model.name} should keep up on this computer, but it uses more of the "
            "processor than the built-in engines, so your screen reader may answer a "
            "little more slowly while you dictate."
        )
    return f"{model.name} should keep up comfortably on this computer."
