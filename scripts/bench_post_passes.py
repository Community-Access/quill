"""Measure the sherpa-onnx extras the dictation design gates on numbers (D-27 to D-30).

**Dev-only.** Never shipped, never run by the app, never run by a test (the
tests exercise the pure parts on tiny inputs). It downloads nothing and opens
no connection: the models are folders a person already has (design record
section 35 lists where each came from, its licence and its SHA-256), and the
audio is a prepared benchmark folder (``fetch_bench_audio.py``,
``bench_librivox.py``, ``bench_commands.py``). Nothing is played aloud.

One subcommand per decision, each run in its own process so its peak memory
is its own::

    # A sentencepiece model's vocabulary as sherpa-onnx's bpe.vocab (no
    # sentencepiece package needed: the protobuf is read directly)
    python scripts/bench_post_passes.py vocab MODEL/bpe.model --out MODEL/bpe.vocab

    # D-27: false triggers an hour, detection after a pause, CPU per thread
    python scripts/bench_post_passes.py kws --model KWS_DIR --soak SOAK_DIR --minutes 60 \\
        --commands CMD_DIR --mentions MENTION_DIR --json kws.json

    # D-28: names recognised with and without hotwords, and word errors
    python scripts/bench_post_passes.py hotwords --model ZIPFORMER_DIR \\
        --bpe-model KWS_DIR/bpe.model --names-set NAMES_DIR --names names.txt \\
        --b1 B1_DIR --b1-subset b1 --json hotwords.json

    # D-29: punctuation restored to unpunctuated references, scored against
    # them; --kind cased for the English model that restores capitals too
    python scripts/bench_post_passes.py punct --model CT_DIR/model.onnx --set B1A_DIR \\
        --json punct.json

    # D-29: who spoke when, on conversations built from a read-speech set
    python scripts/bench_post_passes.py speakers --segmentation SEG.onnx --embedding EMB.onnx \\
        --set LIBRISPEECH_PREPARED --json speakers.json

    # D-30: sherpa-onnx Kokoro against kokoro-onnx: voices, languages, speed,
    # memory, and intelligibility (an ASR model transcribes what each one said)
    python scripts/bench_post_passes.py tts --engine sherpa --model-dir KOKORO_DIR \\
        --json tts-sherpa.json
    python scripts/bench_post_passes.py tts --engine kokoro-onnx --model-dir KOKORO_ONNX_DIR \\
        --json tts-ko.json

What each measures, and its limits, is printed with the numbers and written
into the JSON (``limits``).
"""

from __future__ import annotations

import argparse
import json
import random
import struct
import sys
import time
import wave
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

RATE = 16_000
_SPACE = "▁"  # sentencepiece's word-start mark

# --------------------------------------------------------------------------- #
# sentencepiece without the sentencepiece package
# --------------------------------------------------------------------------- #


def _varint(data: bytes, at: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        byte = data[at]
        at += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, at
        shift += 7


def _fields(data: bytes) -> Iterable[tuple[int, int, Any]]:
    """``(field number, wire type, value)`` for each field of one protobuf message."""
    at = 0
    while at < len(data):
        key, at = _varint(data, at)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, at = _varint(data, at)
        elif wire == 1:
            value, at = data[at : at + 8], at + 8
        elif wire == 2:
            length, at = _varint(data, at)
            value, at = data[at : at + length], at + length
        elif wire == 5:
            value, at = data[at : at + 4], at + 4
        else:
            raise ValueError(f"protobuf wire type {wire} is not read here")
        yield number, wire, value


def sentencepiece_vocab(model: bytes) -> list[tuple[str, float, int]]:
    """``(piece, score, type)`` for every piece of a sentencepiece ModelProto
    (field 1, repeated SentencePiece: piece 1, score 2, type 3; type 1 is normal)."""
    pieces: list[tuple[str, float, int]] = []
    for number, wire, value in _fields(model):
        if number != 1 or wire != 2:
            continue
        piece, score, kind = "", 0.0, 1
        for inner, inner_wire, inner_value in _fields(value):
            if inner == 1 and inner_wire == 2:
                piece = inner_value.decode("utf-8")
            elif inner == 2 and inner_wire == 5:
                score = struct.unpack("<f", inner_value)[0]
            elif inner == 3 and inner_wire == 0:
                kind = int(inner_value)
        pieces.append((piece, score, kind))
    return pieces


def write_bpe_vocab(pieces: Sequence[tuple[str, float, int]], path: Path) -> Path:
    """sherpa-onnx's ``bpe.vocab``: one ``piece<TAB>score`` line per piece."""
    path.write_text("".join(f"{p}\t{s:g}\n" for p, s, _k in pieces), encoding="utf-8")
    return path


def encode(text: str, pieces: Sequence[tuple[str, float, int]]) -> list[str]:
    """*text* as unigram sentencepiece pieces (the highest-scoring split, as
    sentencepiece's own Viterbi does). Unknown characters become their own
    piece, which a keyword file then rejects -- a loud failure, not a quiet one."""
    normal = {p: s for p, s, k in pieces if k in (1, 4) and p}
    longest = max((len(p) for p in normal), default=1)
    word = _SPACE + _SPACE.join(text.split())
    best: list[tuple[float, int]] = [(0.0, -1)] + [(float("-inf"), -1)] * len(word)
    for end in range(1, len(word) + 1):
        for start in range(max(0, end - longest), end):
            piece = word[start:end]
            score = normal.get(piece)
            if score is None and end - start == 1:
                score = -100.0  # an unknown character, kept so the split completes
            if score is None or best[start][0] == float("-inf"):
                continue
            total = best[start][0] + score
            if total > best[end][0]:
                best[end] = (total, start)
    found: list[str] = []
    end = len(word)
    while end > 0:
        start = best[end][1]
        found.append(word[start:end])
        end = start
    return list(reversed(found))


# --------------------------------------------------------------------------- #
# Audio folders
# --------------------------------------------------------------------------- #


def read_wav(path: Path) -> Any:
    import numpy as np

    with wave.open(str(path), "rb") as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (RATE, 1, 2):
            raise SystemExit(f"{path.name}: expected 16 kHz mono 16-bit WAV.")
        frames = audio.readframes(audio.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def transcripts(folder: Path) -> dict[str, str]:
    from dictbench import read_transcripts

    return read_transcripts(folder)


def peak_mb() -> float | None:
    from dictbench import _windows_peak_mb, peak_memory_mb

    return peak_memory_mb() or _windows_peak_mb()


# --------------------------------------------------------------------------- #
# D-27: keyword spotting
# --------------------------------------------------------------------------- #

KWS_LIMITS = (
    "False triggers are counted on read speech (LibriSpeech), not on a person's own "
    "dictation; detection is measured on synthetic voices saying the command word after "
    "a pause, which is cleaner than a real voice in a real room. A real 60-minute B-3 "
    "soak with a person mentioning QUILL is still the acceptance test."
)


def kws_model_files(folder: Path) -> dict[str, Path]:
    """The int8 encoder, decoder and joiner (any epoch naming), and tokens.txt."""
    found: dict[str, Path] = {"tokens": folder / "tokens.txt"}
    for part in ("encoder", "decoder", "joiner"):
        matches = sorted(folder.glob(f"{part}*.int8.onnx")) or sorted(folder.glob(f"{part}*.onnx"))
        if not matches:
            raise SystemExit(f"No {part} model in {folder}.")
        found[part] = matches[0]
    return found


def keyword_file(
    phrases: Sequence[str],
    pieces: Sequence[tuple[str, float, int]],
    path: Path,
    *,
    boost: float,
    threshold: float,
) -> Path:
    from quill.core.windows_dictation.kws_keywords import keyword_lines, keyword_phrases

    wanted: list[str] = []
    for phrase in phrases:
        for item in keyword_phrases(phrase):
            if item not in wanted:
                wanted.append(item)
    lines = keyword_lines(
        wanted,
        lambda texts: [encode(text, pieces) for text in texts],
        boost=boost,
        threshold=threshold,
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _spot(
    spotter: Any, samples: Any, *, block: int = 1600
) -> tuple[list[tuple[float, str]], float]:
    """Every keyword hit in *samples* as (seconds, phrase), and the CPU seconds used."""
    stream = spotter.create_stream()
    hits: list[tuple[float, str]] = []
    started = time.process_time()
    for begin in range(0, len(samples), block):
        stream.accept_waveform(RATE, samples[begin : begin + block])
        while spotter.is_ready(stream):
            spotter.decode_stream(stream)
            result = str(spotter.get_result(stream) or "").strip()
            if result:
                hits.append(((begin + block) / RATE, result))
                spotter.reset_stream(stream)
    return hits, time.process_time() - started


def run_kws(args: argparse.Namespace) -> dict[str, Any]:  # pragma: no cover - runs a model
    import numpy as np
    import sherpa_onnx

    files = kws_model_files(args.model)
    pieces = sentencepiece_vocab((args.model / "bpe.model").read_bytes())
    keywords = keyword_file(
        [args.word],
        pieces,
        args.out_dir / "keywords.txt",
        boost=args.boost,
        threshold=args.threshold,
    )
    started = time.perf_counter()
    spotter = sherpa_onnx.KeywordSpotter(
        tokens=str(files["tokens"]),
        encoder=str(files["encoder"]),
        decoder=str(files["decoder"]),
        joiner=str(files["joiner"]),
        keywords_file=str(keywords),
        num_threads=1,
        keywords_score=args.boost,
        keywords_threshold=args.threshold,
        provider="cpu",
    )
    load = time.perf_counter() - started
    silence = np.zeros(int(RATE * 1.0), dtype=np.float32)
    report: dict[str, Any] = {
        "word": args.word,
        "boost": args.boost,
        "threshold": args.threshold,
        "keywords": keywords.read_text(encoding="utf-8").splitlines(),
        "load_seconds": round(load, 2),
        "limits": KWS_LIMITS,
    }
    # False triggers: the soak's recordings end to end, up to --minutes.
    names = sorted(transcripts(args.soak))
    random.Random(20261017).shuffle(names)
    chunks, seconds = [], 0.0
    for name in names:
        clip = read_wav(args.soak / name)
        chunks += [clip, silence[: RATE // 2]]
        seconds += len(clip) / RATE + 0.5
        if seconds >= args.minutes * 60:
            break
    soak = np.concatenate(chunks)
    hits, cpu = _spot(spotter, soak)
    hours = len(soak) / RATE / 3600
    report["soak"] = {
        "minutes": round(len(soak) / RATE / 60, 1),
        "false_triggers": len(hits),
        "false_triggers_per_hour": round(len(hits) / hours, 2),
        "hits": hits[:20],
        "cpu_per_second_of_audio": round(cpu / (len(soak) / RATE), 4),
    }
    for label, folder in (("commands", args.commands), ("mentions", args.mentions)):
        if folder is None:
            continue
        said = transcripts(folder)
        heard = 0
        rows = []
        for name in sorted(said):
            clip = np.concatenate([silence, read_wav(folder / name), silence])
            found, _cpu = _spot(spotter, clip)
            heard += bool(found)
            rows.append({"file": name, "said": said[name], "hits": [p for _t, p in found]})
        report[label] = {
            "clips": len(rows),
            "with_a_hit": heard,
            "rate": round(heard / max(1, len(rows)), 3),
            "files": rows,
        }
    report["peak_memory_mb"] = peak_mb()
    return report


# --------------------------------------------------------------------------- #
# D-28: hotwords on a Zipformer transducer
# --------------------------------------------------------------------------- #

HOTWORD_LIMITS = (
    "The names are said by synthetic voices inside short sentences; a person's own names, "
    "said by that person, are the real test. A name counts as recognised only when every "
    "one of its words is in the output (capitals and marks ignored)."
)


def name_recognised(name: str, heard: str) -> bool:
    from bench_scoring import basic_normalize

    wanted = basic_normalize(name, accents=False)
    got = set(basic_normalize(heard, accents=False))
    return bool(wanted) and all(word in got for word in wanted)


def _transducer(model: Path, *, hotwords: Path | None, vocab: Path | None, score: float) -> Any:
    import sherpa_onnx

    files = kws_model_files(model)
    options: dict[str, Any] = {}
    if hotwords is not None:
        options = {
            "decoding_method": "modified_beam_search",
            "hotwords_file": str(hotwords),
            "hotwords_score": score,
            "modeling_unit": "bpe",
            "bpe_vocab": str(vocab),
        }
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(files["encoder"]),
        decoder=str(files["decoder"]),
        joiner=str(files["joiner"]),
        tokens=str(files["tokens"]),
        num_threads=1,
        provider="cpu",
        **options,
    )


def _decode(recognizer: Any, samples: Any) -> tuple[str, float]:
    from dictbench import recognise

    started = time.perf_counter()
    text = recognise(recognizer, samples)
    return text, time.perf_counter() - started


def run_hotwords(args: argparse.Namespace) -> dict[str, Any]:  # pragma: no cover - runs a model
    from dictbench import score as score_file
    from dictbench import summary

    from quill.core.windows_dictation.hotwords import hotword_lines

    pieces = sentencepiece_vocab(args.bpe_model.read_bytes())
    vocab = write_bpe_vocab(pieces, args.out_dir / "bpe.vocab")
    names = [line.strip() for line in args.names.read_text(encoding="utf-8").splitlines()]
    names = [n for n in names if n and not n.startswith("#")]
    hotwords = args.out_dir / "hotwords.txt"
    hotwords.write_text("\n".join(hotword_lines(names)) + "\n", encoding="utf-8")
    report: dict[str, Any] = {"names": names, "limits": HOTWORD_LIMITS, "score": args.score}
    for label, words in (("without", None), ("with", hotwords)):
        recognizer = _transducer(args.model, hotwords=words, vocab=vocab, score=args.score)
        said = transcripts(args.names_set)
        recognised = 0
        rows = []
        for name in sorted(said):
            heard, _t = _decode(recognizer, read_wav(args.names_set / name))
            target = next((n for n in names if name_recognised(n, said[name])), "")
            ok = bool(target) and name_recognised(target, heard)
            recognised += ok
            rows.append({"file": name, "name": target, "heard": heard, "recognised": ok})
        entry: dict[str, Any] = {"names_recognised": recognised, "of": len(rows), "files": rows}
        if args.b1 is not None:
            b1 = transcripts(args.b1)
            if args.b1_subset:  # the same seeded subset dictbench scores
                from fetch_bench_audio import subset_names

                chosen = subset_names(args.b1.parent.name, args.b1_subset, args.b1)
            else:
                chosen = sorted(b1)[: args.b1_count]
            results = []
            for name in chosen:
                samples = read_wav(args.b1 / name)
                heard, took = _decode(recognizer, samples)
                result = score_file(name, b1[name], heard)
                result.audio_seconds = len(samples) / RATE
                result.compute_seconds = took
                results.append(result)
            numbers = summary(results)
            entry["b1"] = {
                "files": len(results),
                "word_error_rate": numbers["word_error_rate"],
                "speed_per_thread": numbers["speed_per_thread"],
                "punctuation": numbers["punctuation"],
            }
        report[label] = entry
    report["peak_memory_mb"] = peak_mb()
    return report


# --------------------------------------------------------------------------- #
# D-29: punctuation
# --------------------------------------------------------------------------- #

PUNCT_LIMITS = (
    "The reference is the author's punctuation with every mark and capital removed and "
    "the words left exactly right, so this is the best case: on a recogniser's own "
    "output the word errors come first. An author's commas are one reference, not the "
    "only correct one."
)


#: The CT-Transformer writes Chinese full-width marks into English text
#: (measured 2026-10-17); this maps them, to score what a mapping pass would give.
FULL_WIDTH = str.maketrans({"，": ", ", "。": ". ", "？": "? ", "！": "! ", "、": ", "})


def strip_marks(text: str) -> str:
    """The words of *text*, lower case, with no punctuation: what an engine that
    writes no marks gives the punctuation pass."""
    from bench_scoring import basic_normalize

    return " ".join(basic_normalize(text))


def run_punct(args: argparse.Namespace) -> dict[str, Any]:  # pragma: no cover - runs a model
    import sherpa_onnx
    from bench_scoring import Totals, is_dialogue

    from quill.core.windows_dictation.post_passes import build_punctuator, punctuate

    started = time.perf_counter()
    if args.kind == "cased":
        # The English CNN-BiLSTM, which restores capitals as well as marks.
        cased = sherpa_onnx.OnlinePunctuation(
            sherpa_onnx.OnlinePunctuationConfig(
                model_config=sherpa_onnx.OnlinePunctuationModelConfig(
                    cnn_bilstm=str(args.model),
                    bpe_vocab=str(args.model.parent / "bpe.vocab"),
                    num_threads=1,
                    provider="cpu",
                )
            )
        )
        punctuator = SimpleNamespace(add_punctuation=cased.add_punctuation_with_case)
    else:
        punctuator = build_punctuator(sherpa_onnx, args.model, threads=1)
    load = time.perf_counter() - started
    said = transcripts(args.set)
    prose, bare, ascii_marks = Totals(), Totals(), Totals()
    rows = []
    took = 0.0
    words = 0
    for name in sorted(said):
        reference = said[name]
        if is_dialogue(reference):
            continue
        plain = strip_marks(reference)
        began = time.perf_counter()
        marked = punctuate(punctuator, plain)
        took += time.perf_counter() - began
        words += len(plain.split())
        prose.add(reference, marked)
        ascii_marks.add(reference, marked.translate(FULL_WIDTH))
        bare.add(reference, plain)
        rows.append({"file": name, "reference": reference, "punctuated": marked})
    return {
        "segments": len(rows),
        "load_seconds": round(load, 2),
        "milliseconds_per_100_words": round(1000 * took / max(1, words) * 100, 1),
        "punctuated": prose.as_dict(),
        "punctuated_with_full_width_marks_mapped": ascii_marks.as_dict(),
        "unpunctuated_baseline": bare.as_dict(),
        "examples": rows[:8],
        "peak_memory_mb": peak_mb(),
        "limits": PUNCT_LIMITS,
    }


# --------------------------------------------------------------------------- #
# D-29: speaker labels
# --------------------------------------------------------------------------- #

SPEAKER_LIMITS = (
    "Conversations are built by joining read-speech recordings of different speakers with "
    "short pauses: no overlap, no crosstalk, studio-quality audio. Real meetings and "
    "interviews are harder. Accuracy is the share of recordings whose majority label "
    "matches its true speaker under the best one-to-one mapping."
)


def conversations(
    speakers: dict[str, list[str]], *, count: int, voices: int, turns: int, seed: int
) -> list[list[tuple[str, str]]]:
    """*count* conversations of *voices* speakers taking *turns* turns, as
    ``[(speaker, file), ...]``, seeded so every run builds the same ones."""
    rng = random.Random(seed)
    usable = sorted(s for s, files in speakers.items() if len(files) >= turns)
    built: list[list[tuple[str, str]]] = []
    for _ in range(count):
        chosen = rng.sample(usable, voices)
        pools = {s: rng.sample(speakers[s], len(speakers[s])) for s in chosen}
        order: list[tuple[str, str]] = []
        last = ""
        for _turn in range(turns):
            options = [s for s in chosen if s != last and pools[s]]
            if not options:
                break
            speaker = rng.choice(options)
            order.append((speaker, pools[speaker].pop()))
            last = speaker
        built.append(order)
    return built


def best_mapping_accuracy(truth: Sequence[str], labels: Sequence[str]) -> float:
    """Share of items whose label maps to their true speaker, under the best
    one-to-one mapping (greedy on the confusion counts, enough for a few voices)."""
    from collections import Counter

    pairs = Counter(zip(truth, labels, strict=True))
    used_truth: set[str] = set()
    used_label: set[str] = set()
    correct = 0
    for (who, label), n in pairs.most_common():
        if who in used_truth or label in used_label or not label:
            continue
        used_truth.add(who)
        used_label.add(label)
        correct += n
    return correct / max(1, len(truth))


def run_speakers(args: argparse.Namespace) -> dict[str, Any]:  # pragma: no cover - runs models
    import numpy as np
    import sherpa_onnx
    from fetch_bench_audio import read_speakers

    from quill.core.windows_dictation.post_passes import build_diarizer, label_spans, speaker_turns

    table = read_speakers(args.set)
    by_speaker: dict[str, list[str]] = {}
    for name, fields in table.items():
        by_speaker.setdefault(fields.get("speaker", ""), []).append(name)
    started = time.perf_counter()
    diarizer = build_diarizer(
        sherpa_onnx, args.segmentation, args.embedding, threshold=args.threshold, threads=1
    )
    load = time.perf_counter() - started
    rows = []
    for voices in args.voices:
        for index, talk in enumerate(
            conversations(
                by_speaker, count=args.count, voices=voices, turns=args.turns, seed=voices
            )
        ):
            pieces, spans, truth = [], [], []
            at = 0.0
            for speaker, name in talk:
                clip = read_wav(args.set / name)
                spans.append((at, at + len(clip) / RATE))
                truth.append(speaker)
                pieces += [clip, np.zeros(int(RATE * 0.4), dtype=np.float32)]
                at += len(clip) / RATE + 0.4
            audio = np.concatenate(pieces)
            began = time.process_time()
            turns = speaker_turns(diarizer, audio)
            cpu = time.process_time() - began
            labels = label_spans(spans, turns)
            rows.append({
                "voices": voices,
                "conversation": index,
                "seconds": round(len(audio) / RATE, 1),
                "voices_found": len({t.speaker for t in turns}),
                "accuracy": round(best_mapping_accuracy(truth, labels), 3),
                "cpu_per_second_of_audio": round(cpu / (len(audio) / RATE), 4),
            })
    by_voices: dict[str, Any] = {}
    for voices in args.voices:
        mine = [r for r in rows if r["voices"] == voices]
        by_voices[str(voices)] = {
            "conversations": len(mine),
            "accuracy_mean": round(sum(r["accuracy"] for r in mine) / max(1, len(mine)), 3),
            "right_number_of_voices": sum(1 for r in mine if r["voices_found"] == voices),
            "cpu_per_second_of_audio": round(
                sum(r["cpu_per_second_of_audio"] for r in mine) / max(1, len(mine)), 4
            ),
        }
    return {
        "segmentation": args.segmentation.name,
        "embedding": args.embedding.name,
        "threshold": args.threshold,
        "load_seconds": round(load, 2),
        "by_voices": by_voices,
        "conversations": rows,
        "peak_memory_mb": peak_mb(),
        "limits": SPEAKER_LIMITS,
    }


# --------------------------------------------------------------------------- #
# D-30: speech output
# --------------------------------------------------------------------------- #

TTS_LIMITS = (
    "Intelligibility is measured by a speech recogniser (multilingual Whisper small) "
    "transcribing what each voice said, so it rewards clear, standard speech and says "
    "nothing about how pleasant a voice is; a person listening is the real test."
)

#: One sentence per language QUILL's Kokoro voices speak (KOKORO_VOICES).
TTS_SENTENCES = {
    "en-us": "The quick brown fox jumps over the lazy dog near the river bank.",
    "en-gb": "Please remember to bring your umbrella, because it may rain this afternoon.",
    "es": "Mañana iremos al mercado para comprar pan, queso y fruta fresca.",
    "fr-fr": "Nous partirons demain matin pour visiter le musée de la ville.",
    "it": "Domani andremo al mercato per comprare pane e formaggio fresco.",
    "pt-br": "Amanhã vamos ao mercado para comprar pão, queijo e frutas frescas.",
    "hi": "कल हम ताज़ा फल और सब्ज़ियाँ खरीदने के लिए बाज़ार जाएंगे।",
}
_WHISPER_LANGUAGE = {
    "en-us": "en",
    "en-gb": "en",
    "es": "es",
    "fr-fr": "fr",
    "it": "it",
    "pt-br": "pt",
    "hi": "hi",
}


def model_speakers(model: Path) -> list[str]:
    """A sherpa-onnx Kokoro model's voices in speaker-id order, from the
    ``speaker_names`` its exporter writes into the model's metadata."""
    import onnxruntime

    session = onnxruntime.InferenceSession(str(model), providers=["CPUExecutionProvider"])
    names = session.get_modelmeta().custom_metadata_map.get("speaker_names", "")
    return [name.strip() for name in names.split(",") if name.strip()]


def voice_language(voice: str) -> str:
    from quill.core.read_aloud import kokoro_lang_for_voice

    return str(kokoro_lang_for_voice(voice))


def run_tts(args: argparse.Namespace) -> dict[str, Any]:  # pragma: no cover - runs models
    import numpy as np
    from fetch_bench_audio import resample

    from quill.core.read_aloud import KOKORO_VOICES

    shipped = [voice for voice, _label in KOKORO_VOICES]
    report: dict[str, Any] = {"engine": args.engine, "limits": TTS_LIMITS}
    started = time.perf_counter()
    if args.engine == "sherpa":
        import sherpa_onnx

        from quill.core import sherpa_kokoro

        # QUILL's own engine (quill/core/sherpa_kokoro.py): one engine, the
        # language passed per call, French named "fr".
        model = sorted(args.model_dir.glob("model*.onnx"))[0]
        speakers = model_speakers(model)
        engine = sherpa_kokoro.build(sherpa_onnx, args.model_dir, speakers, threads=1)

        def speak(text: str, voice: str) -> tuple[Any, int]:
            samples, rate = engine.speak(text, voice)
            return np.asarray(samples, dtype=np.float32), rate

        report["model_speakers"] = len(speakers)
        report["voices_available"] = [v for v in shipped if v in speakers]
    else:
        from kokoro_onnx import Kokoro

        kokoro = Kokoro(
            str(args.model_dir / "kokoro-v1.0.int8.onnx"), str(args.model_dir / "voices-v1.0.bin")
        )

        def speak(text: str, voice: str) -> tuple[Any, int]:
            samples, rate = kokoro.create(text, voice=voice, speed=1.0, lang=voice_language(voice))
            return np.asarray(samples, dtype=np.float32), int(rate)

        report["voices_available"] = shipped
    report["load_seconds"] = round(time.perf_counter() - started, 2)
    report["voices_shipped"] = len(shipped)
    report["voices_missing"] = [v for v in shipped if v not in report["voices_available"]]
    # Every language's first shipped voice says its sentence; memory is read
    # before the recogniser loads, so it is the speech engine's own.
    import dictbench

    rows = []
    spoken: dict[str, Any] = {}
    compute = audio_seconds = 0.0
    for lang, sentence in TTS_SENTENCES.items():
        voice = next((v for v in shipped if voice_language(v) == lang), None)
        if voice is None or voice not in report["voices_available"]:
            rows.append({"language": lang, "voice": voice, "spoken": False})
            continue
        try:
            began = time.perf_counter()
            samples, rate = speak(sentence, voice)
            took = time.perf_counter() - began
        except Exception as error:  # noqa: BLE001 - a language that fails is the finding
            rows.append({"language": lang, "voice": voice, "spoken": False, "error": str(error)})
            continue
        if not rate or len(samples) == 0:
            rows.append({"language": lang, "voice": voice, "spoken": False, "error": "no audio"})
            continue
        compute += took
        audio_seconds += len(samples) / rate
        spoken[lang] = resample(samples, rate, RATE)
        rows.append({
            "language": lang,
            "voice": voice,
            "spoken": True,
            "seconds": round(len(samples) / rate, 2),
        })
    report["peak_memory_mb_speech_only"] = peak_mb()
    report["seconds_of_computing_per_second_of_speech"] = round(
        compute / max(audio_seconds, 1e-9), 3
    )
    # Intelligibility: multilingual Whisper, pinned to each language and told
    # to transcribe (the app's loader maps unknown languages to English).
    import sherpa_onnx

    from quill.core.windows_dictation import model_store
    from quill.core.windows_dictation.model_catalog import downloadable

    asr = downloadable(args.asr)
    folder = model_store.model_folder(asr) if asr is not None else None
    for row in rows:
        if not row.get("spoken") or folder is None:
            continue
        recogniser = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(next(folder.glob("*encoder*.onnx"))),
            decoder=str(next(folder.glob("*decoder*.onnx"))),
            tokens=str(next(folder.glob("*tokens.txt"))),
            language=_WHISPER_LANGUAGE[row["language"]],
            task="transcribe",
            num_threads=2,
            provider="cpu",
        )
        heard = dictbench.recognise(recogniser, spoken[row["language"]])
        result = dictbench.score(row["voice"], TTS_SENTENCES[row["language"]], heard)
        row["heard"] = heard
        row["word_error_rate"] = round(result.errors / max(1, result.words), 3)
    report["languages"] = rows
    return report


# --------------------------------------------------------------------------- #
# The command line
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - a person runs it
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    voc = commands.add_parser("vocab", help="bpe.model -> bpe.vocab")
    voc.add_argument("model", type=Path)
    voc.add_argument("--out", type=Path, required=True)
    kws = commands.add_parser("kws", help="D-27")
    kws.add_argument("--model", type=Path, required=True)
    kws.add_argument("--word", default="quill")
    kws.add_argument("--soak", type=Path, required=True)
    kws.add_argument("--minutes", type=float, default=60.0)
    kws.add_argument("--commands", type=Path)
    kws.add_argument("--mentions", type=Path)
    kws.add_argument("--boost", type=float, default=1.0)
    kws.add_argument("--threshold", type=float, default=0.25)
    hot = commands.add_parser("hotwords", help="D-28")
    hot.add_argument("--model", type=Path, required=True)
    hot.add_argument("--bpe-model", type=Path, required=True)
    hot.add_argument("--names-set", type=Path, required=True)
    hot.add_argument("--names", type=Path, required=True)
    hot.add_argument("--b1", type=Path)
    hot.add_argument("--b1-count", type=int, default=100)
    hot.add_argument("--b1-subset", help="a bench_subsets.json subset of the --b1 dataset")
    hot.add_argument("--score", type=float, default=1.5)
    pun = commands.add_parser("punct", help="D-29 punctuation")
    pun.add_argument("--model", type=Path, required=True)
    pun.add_argument("--set", type=Path, required=True)
    pun.add_argument("--kind", choices=("ct", "cased"), default="ct", help="ct: CT-Transformer")
    spk = commands.add_parser("speakers", help="D-29 speaker labels")
    spk.add_argument("--segmentation", type=Path, required=True)
    spk.add_argument("--embedding", type=Path, required=True)
    spk.add_argument("--set", type=Path, required=True)
    spk.add_argument("--voices", type=int, nargs="+", default=[2, 3])
    spk.add_argument("--count", type=int, default=8)
    spk.add_argument("--turns", type=int, default=12)
    spk.add_argument("--threshold", type=float, default=0.5)
    tts = commands.add_parser("tts", help="D-30")
    tts.add_argument("--engine", choices=("sherpa", "kokoro-onnx"), required=True)
    tts.add_argument("--model-dir", type=Path, required=True)
    tts.add_argument("--asr", default="whisper_small")
    for sub in (kws, hot, pun, spk, tts):
        sub.add_argument("--json", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "vocab":
        write_bpe_vocab(sentencepiece_vocab(args.model.read_bytes()), args.out)
        print(f"Wrote {args.out}.")
        return 0
    args.out_dir = args.json.parent
    args.out_dir.mkdir(parents=True, exist_ok=True)
    run = {
        "kws": run_kws,
        "hotwords": run_hotwords,
        "punct": run_punct,
        "speakers": run_speakers,
        "tts": run_tts,
    }[args.command]
    report = run(args)
    report["date"] = time.strftime("%Y-%m-%d")
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    brief = {k: v for k, v in report.items() if k not in {"files", "examples", "conversations"}}
    print(json.dumps(brief, ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
