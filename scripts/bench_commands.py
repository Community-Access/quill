"""The generated dictation-command script (dict.md section 8, B-1c).

Writes a script from QUILL's own command table, has it read by a synthetic
voice, and mixes the recordings with noise and with recorded screen-reader
speech, so the parser, the reader gate and the echo guard are exercised::

    python scripts/bench_commands.py script --language en --out D:/bench/b1c-en/script.tsv
    python scripts/bench_commands.py render D:/bench/b1c-en/script.tsv --voice sapi
    python scripts/bench_commands.py mix D:/bench/b1c-en --noise MUSAN/noise --levels 20 10 5
    python scripts/bench_commands.py mix D:/bench/b1c-en --reader D:/bench/reader --levels 10 0
    python scripts/dictbench.py D:/bench/b1c-en-mixed --parse --group-by group

**What it measures** (and dictbench says so): whether each command parses,
whether a command is ever *typed* as words (``commands_typed``), and how that
changes with noise and with the screen reader talking. **Not** accuracy:
synthetic speech is too clean and too regular, so its word errors are never
quoted as accuracy.

**The script** covers every whole-phrase command (its first spoken form),
the punctuation words inside sentences, "new paragraph", "scratch that", the
D-8 insert commands, commands after the D-1 command word ("QUILL scratch
that"), and the Spanish punctuation words. A command line's reference is
written ``!phrase`` (dictbench's convention); a sentence's reference is what
QUILL's own parser and composer write for it.

**Voices.** ``sapi`` (Windows' own voices, always present on Windows) writes
22 kHz audio that is resampled to 16 kHz; ``kokoro`` uses QUILL's Kokoro voice
when it is downloaded; ``piper`` takes ``--piper-exe`` and ``--piper-model``.
Nothing is played aloud, and nothing is recorded from a microphone.

**Reader speech** is a folder of WAVs a person recorded of NVDA and JAWS
reading ordinary text (process loopback or a file export), never generated
here. Noise is MUSAN's ``noise`` folder (``fetch_bench_audio.py musan``).
"""

from __future__ import annotations

import argparse
import sys
import wave
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

RATE = 16_000

#: Sentences with spoken punctuation, as said and as QUILL should write them.
_EN_SENTENCES = (
    "send the report today comma please period",
    "where did you put the keys question mark",
    "the meeting is at three o'clock period thanks for coming period",
    "we need eggs comma milk comma and bread period",
    "open quote hello close quote she said period",
)
_ES_SENTENCES = (
    "abre interrogación dónde está la biblioteca cierra interrogación",
    "necesitamos huevos coma leche y pan punto",
    "hola coma amigos punto hasta mañana punto",
)
#: Layout words said alone: marks, not commands, but never to be typed as words.
#: (A line break inside a reference would break transcripts.txt, so they are
#: scored as commands: ``!new paragraph``.)
_EN_LAYOUT = ("new paragraph", "new line")
#: The D-8 insert commands, with an argument (prefix commands).
_EN_PREFIXED = ("insert snippet sign off", "insert abbreviation addr", "paste clip three")
#: Said after the D-1 command word.
_AFTER_THE_WORD = ("scratch that", "new paragraph", "stop dictation")


@dataclass(frozen=True, slots=True)
class Line:
    name: str
    spoken: str
    reference: str
    kind: str  # command, layout, prefixed, after-word, sentence


def _written(spoken: str, language: str) -> str:
    """What QUILL writes for *spoken*: its parser, then its composer."""
    from quill.core.windows_dictation.composer import compose
    from quill.core.windows_dictation.parser import RecognizedPhrase, parse, words_from_text
    from quill.core.windows_dictation.vocabulary import vocabulary_for

    parsed = parse(RecognizedPhrase(words_from_text(spoken)), vocabulary=vocabulary_for(language))
    return compose(parsed.pieces)


def command_phrases(language: str = "en") -> list[str]:
    """The first spoken form of every whole-phrase command that parses back to
    itself -- the ones the table says and the parser agrees with."""
    from quill.core.windows_dictation.parser import RecognizedPhrase, parse, words_from_text
    from quill.core.windows_dictation.vocabulary import vocabulary_for

    if language.startswith("es"):
        from quill.core.windows_dictation.vocabulary_es import (
            SPANISH_COMMAND_HELP,
            SPANISH_SWITCH_HELP,
        )

        # The drafted Spanish commands count only when they are switched on;
        # the switch back to English always does.
        table = (*SPANISH_SWITCH_HELP, *SPANISH_COMMAND_HELP)
    else:
        from quill.core.windows_dictation.vocabulary import COMMAND_HELP as table
    vocabulary = vocabulary_for(language)
    found: list[str] = []
    for entry in table:
        phrase = entry.phrases[0]
        parsed = parse(RecognizedPhrase(words_from_text(phrase)), vocabulary=vocabulary)
        if parsed.command == entry.command and phrase not in found:
            found.append(phrase)
    return found


def script(language: str = "en", command_word: str = "quill") -> list[Line]:
    """Every line of the B-1c script for *language*."""
    lines: list[Line] = []

    def add(spoken: str, reference: str, kind: str) -> None:
        lines.append(Line(f"{language}-{len(lines) + 1:03d}.wav", spoken, reference, kind))

    for phrase in command_phrases(language):
        add(phrase, f"!{phrase}", "command")
    if language.startswith("es"):
        for sentence in _ES_SENTENCES:
            add(sentence, _written(sentence, "es"), "sentence")
        return lines
    for phrase in _EN_LAYOUT:
        add(phrase, f"!{phrase}", "layout")
    for phrase in _EN_PREFIXED:
        add(phrase, f"!{phrase}", "prefixed")
    for phrase in _AFTER_THE_WORD:
        add(f"{command_word} {phrase}", f"!{command_word} {phrase}", "after-word")
    for sentence in _EN_SENTENCES:
        add(sentence, _written(sentence, "en"), "sentence")
    return lines


def write_script(lines: Iterable[Line], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = ["name\tspoken\treference\tkind"]
    rows += [f"{line.name}\t{line.spoken}\t{line.reference}\t{line.kind}" for line in lines]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def read_script(path: Path) -> list[Line]:
    rows = path.read_text(encoding="utf-8").splitlines()[1:]
    return [Line(*row.split("\t")) for row in rows if row.strip()]


# --------------------------------------------------------------------------- #
# Audio
# --------------------------------------------------------------------------- #


def read_wav(path: Path) -> tuple[Any, int]:
    """Mono float samples and the rate, from a 16-bit PCM WAV."""
    import numpy as np

    with wave.open(str(path), "rb") as audio:
        rate, channels, width = audio.getframerate(), audio.getnchannels(), audio.getsampwidth()
        frames = audio.readframes(audio.getnframes())
    if width != 2:
        raise SystemExit(f"{path.name}: only 16-bit PCM WAV is read here.")
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, rate


def write_wav(path: Path, samples: Any, rate: int = RATE) -> None:
    import numpy as np

    clipped = np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes((clipped * 32767).astype("<i2").tobytes())


def mix(speech: Any, noise: Any, snr_db: float) -> Any:
    """*speech* with *noise* added at *snr_db* (speech power over noise power).
    The noise is looped or cut to the speech's length."""
    import numpy as np

    speech = np.asarray(speech, dtype=np.float32)
    noise = np.asarray(noise, dtype=np.float32)
    if noise.size == 0 or speech.size == 0:
        return speech
    repeats = int(np.ceil(speech.size / noise.size))
    bed = np.tile(noise, repeats)[: speech.size]
    speech_power = float(np.mean(speech**2)) or 1e-12
    noise_power = float(np.mean(bed**2)) or 1e-12
    scale = np.sqrt(speech_power / (noise_power * 10 ** (snr_db / 10)))
    return (speech + bed * scale).astype(np.float32)


def render(script_path: Path, voice: str, **options: Any) -> int:  # pragma: no cover - TTS
    """Read every line aloud *to a file* with *voice*, as 16 kHz mono WAV."""
    import tempfile

    from fetch_bench_audio import resample

    folder = script_path.parent
    lines = read_script(script_path)
    with tempfile.TemporaryDirectory() as scratch:
        for line in lines:
            raw = Path(scratch) / line.name
            if voice == "sapi":
                from quill.platform.windows import sapi5

                sapi5.synthesize_to_wav(line.spoken, raw)
            elif voice == "kokoro":
                from quill.core.read_aloud import synthesize_with_kokoro

                synthesize_with_kokoro(
                    line.spoken, raw, voice=options.get("kokoro_voice") or "af_heart"
                )
            elif voice == "piper":
                from quill.core.read_aloud import synthesize_with_piper

                synthesize_with_piper(
                    line.spoken,
                    raw,
                    executable_path=Path(options["piper_exe"]),
                    model_path=Path(options["piper_model"]),
                )
            else:
                raise SystemExit(f"Unknown voice: {voice}. Use sapi, kokoro or piper.")
            samples, rate = _read_any(raw)
            write_wav(folder / line.name, resample(samples, rate, RATE))
    transcripts = [f"{line.name}\t{line.reference}" for line in lines]
    (folder / "transcripts.txt").write_text("\n".join(transcripts) + "\n", encoding="utf-8")
    speakers = ["file\tspeaker\taccent\tgender\tlanguage\tgroup"]
    speakers += [f"{line.name}\t{voice}\t\t\t{line.name[:2]}\tclean {line.kind}" for line in lines]
    (folder / "speakers.tsv").write_text("\n".join(speakers) + "\n", encoding="utf-8")
    return len(lines)


def _read_any(path: Path) -> tuple[Any, int]:  # pragma: no cover - TTS output
    try:
        return read_wav(path)
    except (SystemExit, wave.Error):
        import soundfile as sf

        samples, rate = sf.read(str(path), dtype="float32", always_2d=True)
        return samples.mean(axis=1), rate


def mix_folder(
    folder: Path,
    out: Path,
    beds: Sequence[Path],
    levels: Sequence[float],
    label: str,
) -> int:
    """Every recording in *folder* mixed with each bed at each level.

    Writes WAVs, transcripts.txt and speakers.tsv (``group`` names the
    condition, so ``dictbench --group-by group`` reports each one apart).
    """
    from dictbench import read_transcripts

    transcripts = read_transcripts(folder)
    out.mkdir(parents=True, exist_ok=True)
    rows: list[str] = []
    speakers = ["file\tspeaker\taccent\tgender\tlanguage\tgroup"]
    for name, reference in transcripts.items():
        speech, _rate = read_wav(folder / name)
        for bed_index, bed_path in enumerate(beds):
            noise, _ = read_wav(bed_path)
            for level in levels:
                mixed_name = f"{Path(name).stem}-{label}{bed_index}-{level:g}db.wav"
                write_wav(out / mixed_name, mix(speech, noise, level))
                rows.append(f"{mixed_name}\t{reference}")
                speakers.append(f"{mixed_name}\t\t\t\t\t{label} {level:g} dB")
    (out / "transcripts.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (out / "speakers.tsv").write_text("\n".join(speakers) + "\n", encoding="utf-8")
    return len(rows)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - a person runs it
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    s = commands.add_parser("script", help="write the script from the command table")
    s.add_argument("--language", default="en")
    s.add_argument("--command-word", default="quill")
    s.add_argument("--out", type=Path, required=True)
    r = commands.add_parser("render", help="read the script to WAV files")
    r.add_argument("script", type=Path)
    r.add_argument("--voice", default="sapi")
    r.add_argument("--kokoro-voice")
    r.add_argument("--piper-exe")
    r.add_argument("--piper-model")
    m = commands.add_parser("mix", help="mix rendered recordings with noise or reader speech")
    m.add_argument("folder", type=Path)
    m.add_argument("--noise", type=Path, help="a folder of noise WAVs (MUSAN noise)")
    m.add_argument("--reader", type=Path, help="a folder of recorded screen-reader speech")
    m.add_argument("--levels", type=float, nargs="+", default=[20.0, 10.0, 5.0])
    m.add_argument("--beds", type=int, default=3, help="how many noise files to use")
    m.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.command == "script":
        lines = script(args.language, args.command_word)
        write_script(lines, args.out)
        print(f"{len(lines)} lines written to {args.out}.")
        return 0
    if args.command == "render":
        count = render(
            args.script,
            args.voice,
            kokoro_voice=args.kokoro_voice,
            piper_exe=args.piper_exe,
            piper_model=args.piper_model,
        )
        print(f"{count} recordings written beside {args.script}.")
        return 0
    source = args.noise or args.reader
    if source is None:
        raise SystemExit("Give --noise or --reader.")
    label = "noise" if args.noise else "reader"
    beds = sorted(source.rglob("*.wav"))[: args.beds]
    out = args.out or args.folder.with_name(f"{args.folder.name}-{label}")
    count = mix_folder(args.folder, out, beds, args.levels, label)
    print(f"{count} mixed recordings in {out}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
