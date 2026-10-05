"""Benchmark dictation's built-in engines on real recordings, in one command.

Feeds every WAV in a folder to an engine, the way dictation does (one phrase at
a time, quiet padding either side, **one CPU thread** -- the speed budget in
dict.md section 1 is per thread), and compares what it wrote with what was
said::

    python scripts/dictbench.py RECORDINGS_DIR                       # English, Moonshine
    python scripts/dictbench.py RECORDINGS_DIR --engine whisper
    python scripts/dictbench.py RECORDINGS_DIR --language es         # Spanish: multilingual Whisper
    python scripts/dictbench.py RECORDINGS_DIR --language es --json results.json

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
* memory: the process's peak working set, when ``psutil`` is installed.

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
    said = words(reference)
    return FileResult(
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
        )
    return sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(folder / "encoder.int8.onnx"),
        decoder=str(folder / "decoder.int8.onnx"),
        tokens=str(folder / "tokens.txt"),
        language=language,
        num_threads=threads,
    )


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
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path, help="recordings plus transcripts.txt")
    parser.add_argument("--engine", default="moonshine", choices=("moonshine", "whisper"))
    parser.add_argument("--language", default="en", help="en or es")
    parser.add_argument("--threads", type=int, default=1, help="1 is the budget's measure")
    parser.add_argument("--json", type=Path, help="also write every result here")
    args = parser.parse_args(argv)

    language = coerce_speech_language(args.language)
    transcripts = read_transcripts(args.folder)
    recognizer = load_engine(args.engine, language, args.threads)
    model = model_for(args.engine, language)
    print(f"{model.label}, language {language}, {args.threads} thread(s)")
    results: list[FileResult] = []
    for name, reference in transcripts.items():
        samples = read_wav(args.folder / name)
        started = time.perf_counter()
        heard = recognise(recognizer, samples)
        result = score(name, reference, heard)
        result.compute_seconds = time.perf_counter() - started
        result.audio_seconds = len(samples) / RATE
        results.append(result)
        print(f"  {name}: {result.errors}/{result.words} word errors")
        print(f"    said:  {reference}")
        print(f"    heard: {heard}")
    overall = summary(results)
    overall["peak_memory_mb"] = peak_memory_mb()
    overall["engine"], overall["language"] = model.id, language
    for key, value in overall.items():
        print(f"{key}: {value}")
    if args.json:
        payload = {"summary": overall, "files": [asdict(r) for r in results]}
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
