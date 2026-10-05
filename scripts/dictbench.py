"""Benchmark dictation's engines -- built in or downloaded -- on real recordings.

Feeds every WAV in a folder to an engine, the way dictation does (one phrase at
a time, quiet padding either side, **one CPU thread** -- the speed budget in
dict.md section 1 is per thread), and compares what it wrote with what was
said::

    python scripts/dictbench.py RECORDINGS_DIR                       # English, Moonshine
    python scripts/dictbench.py RECORDINGS_DIR --engine whisper
    python scripts/dictbench.py RECORDINGS_DIR --language es         # Spanish: multilingual Whisper
    python scripts/dictbench.py RECORDINGS_DIR --language es --json results.json
    python scripts/dictbench.py RECORDINGS_DIR --model nemotron      # a downloaded model
    python scripts/dictbench.py --list-models                        # every model it knows
    python scripts/dictbench.py --model whisper_small --fetch        # download it first

**Any optional model** (``--model ID``, the ids in
``quill/core/windows_dictation/model_catalog.py``) is benchmarked from the
shared downloads folder QUILL and QUILL Lite use; ``--fetch`` downloads it there
first, through the same pinned, checksum-verified downloader the app uses.
Every engine runs on the CPU (sherpa-onnx's ``cpu`` provider), and the result
says so.

**The folder** holds the recordings and one ``transcripts.txt``:

* ``01.wav`` ... ``10.wav`` -- 16 kHz, mono, 16-bit PCM WAV, one sentence each.
* ``transcripts.txt`` -- one line per recording: the file name, a tab (or a
  space), and exactly what was said, written as it should appear, with
  punctuation, capitals and accents: ``03.wav	¿Dónde está la biblioteca?``

**What it reports**, per file and overall:

* word errors (WER), ignoring capitals and punctuation -- and again ignoring
  accents too, so a recogniser that writes "esta" for "está" is visible as such;
* punctuation: of the marks the reference has (``. , ? ! ¿ ¡``), how many the
  engine wrote -- the open question in dict.md 9.4 D is whether multilingual
  Whisper writes the opening ``¿`` and ``¡`` itself;
* speed: seconds of computing per second of speech (the budget is 0.25 or less);
* first-word and final latency: for a phrase engine both are the time from the
  end of the phrase to its text; for a streaming one (Nemotron) the first is how
  far into the speech the first word appeared, fed at real-time pace;
* commands: a reference written ``!new paragraph`` is a spoken command, scored
  as recognised when the words match exactly (capitals and marks ignored);
* startup (model load) time, model size, average CPU use while recognising,
  failures, and the process's peak memory (psutil when installed, otherwise
  Windows' own counter).

Needs the models (``python scripts/fetch_dictation_models.py``), ``sherpa-onnx``
and ``numpy`` -- the ``live-dictation`` extra. Reads only the folder it is
given; nothing is sent anywhere.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from quill.core.windows_dictation.engines import model_dir, model_for  # noqa: E402
from quill.core.windows_dictation.model_catalog import (  # noqa: E402
    CATALOGUE,
    downloadable,
    megabytes,
)
from quill.core.windows_dictation.speech_language import (  # noqa: E402
    coerce_speech_language,
    fold,
)

RATE = 16_000
TRANSCRIPTS = "transcripts.txt"
#: Marks counted for punctuation, including Spanish's opening pair.
MARKS = ".,?!" + chr(0xBF) + chr(0xA1)
_WORDS = re.compile(r"[\w']+")


@dataclass
class FileResult:
    name: str
    reference: str
    heard: str
    words: int
    errors: int
    errors_ignoring_accents: int
    marks_expected: dict[str, int] = field(default_factory=dict)
    marks_written: dict[str, int] = field(default_factory=dict)
    audio_seconds: float = 0.0
    compute_seconds: float = 0.0
    first_word_seconds: float = 0.0
    final_seconds: float = 0.0
    command: bool = False
    failed: str = ""


def read_transcripts(folder: Path) -> dict[str, str]:
    """``{file name: what was said}`` from *folder*'s ``transcripts.txt``."""
    path = folder / TRANSCRIPTS
    if not path.is_file():
        raise SystemExit(f"{path} is missing: one line per recording, 'name.wav<tab>text'.")
    found: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, _sep, text = line.strip().partition("\t")
        if not text:
            name, _sep, text = line.strip().partition(" ")
        if not name.lower().endswith(".wav") or not text.strip():
            raise SystemExit(f"{path}, line {number}: expected 'name.wav<tab>text'.")
        found[name] = text.strip()
    return found


def words(text: str, *, accents: bool = True) -> list[str]:
    """*text* as words for scoring: no capitals, no punctuation."""
    text = text.lower() if accents else fold(text)
    return _WORDS.findall(text.replace("_", " "))


def word_errors(reference: list[str], heard: list[str]) -> int:
    """Substitutions, insertions and deletions turning *reference* into *heard*."""
    previous = list(range(len(heard) + 1))
    for i, said in enumerate(reference, 1):
        current = [i]
        for j, got in enumerate(heard, 1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (said != got))
            )
        previous = current
    return previous[-1]


def count_marks(text: str) -> dict[str, int]:
    return {mark: text.count(mark) for mark in MARKS if mark in text}


def score(name: str, reference: str, heard: str) -> FileResult:
    command = reference.startswith("!")
    reference = reference.removeprefix("!").strip()
    said = words(reference)
    return FileResult(
        command=command,
        name=name,
        reference=reference,
        heard=heard,
        words=len(said),
        errors=word_errors(said, words(heard)),
        errors_ignoring_accents=word_errors(
            words(reference, accents=False), words(heard, accents=False)
        ),
        marks_expected=count_marks(reference),
        marks_written=count_marks(heard),
    )


def read_wav(path: Path) -> Any:
    """16 kHz mono 16-bit PCM as float samples; anything else is refused by name."""
    import numpy as np

    with wave.open(str(path), "rb") as audio:
        shape = (audio.getframerate(), audio.getnchannels(), audio.getsampwidth())
        if shape != (RATE, 1, 2):
            raise SystemExit(
                f"{path.name}: {shape[0]} Hz, {shape[1]} channel(s), {8 * shape[2]}-bit. "
                "Record (or convert) to 16 kHz, mono, 16-bit WAV."
            )
        frames = audio.readframes(audio.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def load_engine(engine_id: str, language: str, threads: int) -> Any:
    import sherpa_onnx

    downloaded = downloadable(engine_id)
    if downloaded is not None:
        from quill.core.windows_dictation import model_loader, model_store

        if not model_store.installed(downloaded):
            raise SystemExit(
                f"{downloaded.name} is not downloaded. Add --fetch, or download it in "
                "Dictation Settings, Speech Models."
            )
        return model_loader.build(
            downloaded,
            model_store.model_folder(downloaded),
            sherpa_onnx,
            language=language,
            threads=threads,
        )
    model = model_for(engine_id, language)
    folder = model_dir(engine_id, language)
    if folder is None:
        raise SystemExit(
            f"The {model.label} model is not here. Run: python scripts/fetch_dictation_models.py"
        )
    if model.id == "moonshine":
        return sherpa_onnx.OfflineRecognizer.from_moonshine(
            preprocessor=str(folder / "preprocess.onnx"),
            encoder=str(folder / "encode.int8.onnx"),
            uncached_decoder=str(folder / "uncached_decode.int8.onnx"),
            cached_decoder=str(folder / "cached_decode.int8.onnx"),
            tokens=str(folder / "tokens.txt"),
            num_threads=threads,
            provider="cpu",
        )
    return sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(folder / "encoder.int8.onnx"),
        decoder=str(folder / "decoder.int8.onnx"),
        tokens=str(folder / "tokens.txt"),
        language=language,
        num_threads=threads,
        provider="cpu",
    )


_ONLINE: dict[str, Any] = {}


def streaming_latency(engine_id: str, samples: Any, threads: int, language: str) -> float:
    """Nemotron only: seconds into the speech when its first word appeared,
    fed in 160 ms pieces as if live (computing time added to audio time)."""
    import sherpa_onnx

    from quill.core.windows_dictation import model_loader, model_store

    model = downloadable(engine_id)
    assert model is not None
    if engine_id not in _ONLINE:  # loaded once: a model per file would skew memory
        folder = model_store.model_folder(model)
        _ONLINE[engine_id] = model_loader.online(model, folder, sherpa_onnx, threads=threads)
    recognizer = _ONLINE[engine_id]
    session = model_loader.StreamingSession(recognizer, language)
    step = int(RATE * 0.16)
    computing = 0.0
    for start in range(0, len(samples), step):
        began = time.perf_counter()
        session.accept(samples[start : start + step])
        found = session.partial()
        computing += time.perf_counter() - began
        if found:
            return round((start + step) / RATE + computing, 3)
    return round(len(samples) / RATE + computing, 3)


def recognise(recognizer: Any, samples: Any) -> str:
    import numpy as np

    padded = np.concatenate([
        np.zeros(int(RATE * 0.2), dtype=np.float32),
        samples,
        np.zeros(int(RATE * 0.5), dtype=np.float32),
    ])
    stream = recognizer.create_stream()
    stream.accept_waveform(RATE, padded)
    recognizer.decode_stream(stream)
    return str(stream.result.text).strip()


def peak_memory_mb() -> float | None:
    try:
        import psutil  # type: ignore[import-untyped,import-not-found,unused-ignore]
    except ImportError:
        return None
    info = psutil.Process().memory_info()
    return round(getattr(info, "peak_wset", info.rss) / 1_048_576, 1)


def _windows_peak_mb() -> float | None:
    try:
        import ctypes

        class _Counters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("faults", ctypes.c_ulong),
                ("peak", ctypes.c_size_t),
            ] + [(f"x{i}", ctypes.c_size_t) for i in range(7)]

        counters = _Counters()
        counters.cb = ctypes.sizeof(_Counters)
        kernel = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        query = ctypes.windll.psapi.GetProcessMemoryInfo  # type: ignore[attr-defined]
        query.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        query(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
        return round(counters.peak / 1_048_576, 1)
    except Exception:  # noqa: BLE001 - not Windows
        return None


def summary(results: list[FileResult]) -> dict[str, Any]:
    total_words = sum(r.words for r in results) or 1
    audio = sum(r.audio_seconds for r in results) or 1.0
    expected: dict[str, int] = {}
    written: dict[str, int] = {}
    for result in results:
        for mark, count in result.marks_expected.items():
            expected[mark] = expected.get(mark, 0) + count
            written[mark] = written.get(mark, 0) + min(count, result.marks_written.get(mark, 0))
    return {
        "files": len(results),
        "word_error_rate": round(sum(r.errors for r in results) / total_words, 3),
        "word_error_rate_ignoring_accents": round(
            sum(r.errors_ignoring_accents for r in results) / total_words, 3
        ),
        "punctuation_found": {mark: f"{written[mark]}/{n}" for mark, n in expected.items()},
        "speed_per_thread": round(sum(r.compute_seconds for r in results) / audio, 3),
        "first_word_seconds_average": round(
            sum(r.first_word_seconds for r in results) / max(1, len(results)), 3
        ),
        "final_seconds_average": round(
            sum(r.final_seconds for r in results) / max(1, len(results)), 3
        ),
        "commands_recognised": (
            f"{sum(1 for r in results if r.command and not r.errors)}/"
            f"{sum(1 for r in results if r.command)}"
        ),
        "failures": sum(1 for r in results if r.failed),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path, nargs="?", help="recordings plus transcripts.txt")
    parser.add_argument("--engine", default="moonshine", help="moonshine, whisper, or a model id")
    parser.add_argument("--model", help="a downloadable model's id (see --list-models)")
    parser.add_argument("--list-models", action="store_true", help="list the optional models")
    parser.add_argument("--fetch", action="store_true", help="download --model first if needed")
    parser.add_argument("--language", default="en", help="en or es")
    parser.add_argument("--threads", type=int, default=1, help="1 is the budget's measure")
    parser.add_argument("--json", type=Path, help="also write every result here")
    args = parser.parse_args(argv)

    if args.list_models:
        for item in CATALOGUE:
            size = megabytes(item.download_bytes)
            print(f"{item.id:18} {size:>9}  {item.name} ({item.language_names})")
        return 0
    engine = args.model or args.engine
    if engine not in {"moonshine", "whisper"} and downloadable(engine) is None:
        raise SystemExit(f"Unknown engine or model: {engine}. Try --list-models.")
    if args.fetch and downloadable(engine) is not None:
        fetch_model(engine)
    if args.folder is None:
        return 0
    language = coerce_speech_language(args.language)
    transcripts = read_transcripts(args.folder)
    started = time.perf_counter()
    recognizer = load_engine(engine, language, args.threads)
    startup = time.perf_counter() - started
    model = model_for(engine, language)
    print(f"{model.label}, language {language}, {args.threads} thread(s), CPU only")
    results: list[FileResult] = []
    cpu_before, wall_before = time.process_time(), time.perf_counter()
    for name, reference in transcripts.items():
        samples = read_wav(args.folder / name)
        started = time.perf_counter()
        try:
            heard, failure = recognise(recognizer, samples), ""
        except Exception as error:  # noqa: BLE001 - counted, and the run goes on
            heard, failure = "", str(error)
        result = score(name, reference, heard)
        result.compute_seconds = result.final_seconds = time.perf_counter() - started
        result.first_word_seconds = result.final_seconds
        result.failed = failure
        if model.id == "nemotron" and not failure:
            result.first_word_seconds = streaming_latency(engine, samples, args.threads, language)
        result.audio_seconds = len(samples) / RATE
        results.append(result)
        print(f"  {name}: {result.errors}/{result.words} word errors")
        print(f"    said:  {reference}")
        print(f"    heard: {heard}")
    wall = time.perf_counter() - wall_before
    overall = summary(results)
    cpu = time.process_time() - cpu_before
    overall["average_cpu_percent"] = round(100 * cpu / max(wall, 1e-9))
    overall["startup_seconds"] = round(startup, 2)
    overall["peak_memory_mb"] = peak_memory_mb() or _windows_peak_mb()
    downloaded = downloadable(model.id)
    overall["model_size"] = megabytes(downloaded.download_bytes) if downloaded else "built in"
    overall["execution_provider"] = "cpu"
    overall["engine"], overall["language"] = model.id, language
    for key, value in overall.items():
        print(f"{key}: {value}")
    if args.json:
        payload = {"summary": overall, "files": [asdict(r) for r in results]}
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


def fetch_model(model_id: str) -> None:
    """Download *model_id* into the shared folder, printing progress."""
    from quill.core.windows_dictation import model_store

    model = downloadable(model_id)
    assert model is not None
    if model_store.installed(model):
        return
    problem = model_store.free_space_problem(model)
    if problem:
        raise SystemExit(problem)
    where = model_store.model_folder(model)
    print(f"Downloading {model.name} ({megabytes(model.download_bytes)}) to {where}")
    model_store.download(model, progress=lambda f, _m: print(f"  {int(f * 100)}%", end="\r"))
    print(f"\n{model.name} is ready.")


if __name__ == "__main__":
    sys.exit(main())
