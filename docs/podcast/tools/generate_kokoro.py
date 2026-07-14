#!/usr/bin/env python3
"""Generate QUILL podcast episodes with Kokoro voices (Liam + Jessica).

Reads two-host transcripts from ``docs/podcast/scripts/*.txt`` written in the
marker format::

    [LIAM]
    Welcome to The QUILL Cast...

    [JESSICA]
    Thanks, Liam...

    [PAUSE]

and synthesizes each turn with kokoro-onnx (LIAM -> ``am_liam``,
JESSICA -> ``af_jessica`` by default), inserting natural gaps between turns
and a longer beat at ``[PAUSE]`` markers. Output is WAV plus MP3 (via ffmpeg).

The pipeline is adapted from the git-going-with-github podcast generator, cut
down to what this series needs. Model files are looked up in this order:

1. ``--model-dir`` argument
2. ``QUILL_KOKORO_MODEL_DIR`` environment variable
3. ``docs/podcast/tools/models/`` next to this script

Both ``kokoro-v1.0.onnx`` and ``voices-v1.0.bin`` must be present (QUILL's own
Voice Picker download or the kokoro-models.zip asset provide them).

Usage::

    python docs/podcast/tools/generate_kokoro.py                # all episodes
    python docs/podcast/tools/generate_kokoro.py --slug ep01-meet-quill
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
PODCAST_ROOT = HERE.parent
SCRIPTS_DIR = PODCAST_ROOT / "scripts"
AUDIO_DIR = PODCAST_ROOT / "audio"

MALE_SPEAKER = "LIAM"
FEMALE_SPEAKER = "JESSICA"

DEFAULT_MALE_VOICE = "am_liam"
DEFAULT_FEMALE_VOICE = "af_jessica"
DEFAULT_SPEED = 1.06
PAUSE_SECONDS = 0.9
SAME_SPEAKER_GAP = 0.18
SPEAKER_CHANGE_GAP = 0.30
FINAL_TAIL = 0.4
MAX_SEGMENT_CHARS = 360

_MARKER = re.compile(r"^\[(LIAM|JESSICA|PAUSE)\]$")


def parse_script(text: str) -> list[dict]:
    """Split a transcript into speaker turns and pauses."""
    segments: list[dict] = []
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if current and buf:
            segments.append({"speaker": current, "text": " ".join(buf)})
        buf = []

    for line in text.splitlines():
        t = line.lstrip("﻿").strip()
        if not t:
            continue
        match = _MARKER.match(t)
        if match is None:
            buf.append(t)
            continue
        marker = match.group(1)
        flush()
        if marker == "PAUSE":
            segments.append({"speaker": "PAUSE", "text": ""})
            current = None
        else:
            current = marker
    flush()
    return segments


def safe_text(s: str) -> str:
    """Normalize typography so the TTS never reads mojibake or smart quotes."""
    s = unicodedata.normalize("NFKC", s)
    replacements = {
        " ": " ",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
    }
    for src, dst in replacements.items():
        s = s.replace(src, dst)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cf")


def split_text(text: str, max_chars: int) -> list[str]:
    """Sentence-first chunking so Kokoro never sees an over-long input."""
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        while len(sentence) > max_chars:
            head, _, sentence = sentence[:max_chars].rpartition(" ")
            chunks.append(head or sentence[:max_chars])
        candidate = f"{current} {sentence}".strip()
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]


def find_model_dir(cli_value: str | None) -> Path:
    candidates = []
    if cli_value:
        candidates.append(Path(cli_value))
    env_value = os.environ.get("QUILL_KOKORO_MODEL_DIR", "").strip()
    if env_value:
        candidates.append(Path(env_value))
    candidates.append(HERE / "models")
    for candidate in candidates:
        if (candidate / "kokoro-v1.0.onnx").is_file() and (candidate / "voices-v1.0.bin").is_file():
            return candidate
    raise SystemExit(
        "Kokoro model files not found. Provide --model-dir or set "
        "QUILL_KOKORO_MODEL_DIR to a folder containing kokoro-v1.0.onnx and "
        "voices-v1.0.bin."
    )


def convert_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("MP3 output requires ffmpeg on PATH.")
    subprocess.check_call([
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(mp3_path),
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slug", action="append", default=[], help="Only these episode slugs")
    parser.add_argument("--model-dir", default=None, help="Folder with the Kokoro model files")
    parser.add_argument("--male-voice", default=DEFAULT_MALE_VOICE)
    parser.add_argument("--female-voice", default=DEFAULT_FEMALE_VOICE)
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED)
    parser.add_argument("--force", action="store_true", help="Regenerate existing episodes")
    parser.add_argument("--wav-only", action="store_true", help="Skip the MP3 conversion")
    args = parser.parse_args()

    try:
        import numpy as np
        import soundfile as sf
        from kokoro_onnx import Kokoro
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency. Install with: pip install kokoro-onnx soundfile numpy"
        ) from exc

    model_dir = find_model_dir(args.model_dir)
    scripts = sorted(SCRIPTS_DIR.glob("ep*.txt"))
    wanted = {slug.strip() for slug in args.slug if slug.strip()}
    if wanted:
        scripts = [s for s in scripts if s.stem in wanted]
        missing = wanted - {s.stem for s in scripts}
        if missing:
            raise SystemExit("Unknown slug(s): " + ", ".join(sorted(missing)))
    if not scripts:
        raise SystemExit(f"No episode scripts found in {SCRIPTS_DIR}")

    kokoro = Kokoro(str(model_dir / "kokoro-v1.0.onnx"), str(model_dir / "voices-v1.0.bin"))
    voices = set(kokoro.get_voices())
    for voice in (args.male_voice, args.female_voice):
        if voice not in voices:
            raise SystemExit(f"Voice not available in this model: {voice}")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    durations: dict[str, float] = {}

    for index, script in enumerate(scripts, start=1):
        slug = script.stem
        out_wav = AUDIO_DIR / f"{slug}.wav"
        out_mp3 = AUDIO_DIR / f"{slug}.mp3"
        done = out_mp3.exists() if not args.wav_only else out_wav.exists()
        if done and not args.force:
            print(f"[{index}/{len(scripts)}] skip existing {slug}")
            continue
        print(f"[{index}/{len(scripts)}] generating {slug}")
        segments = parse_script(script.read_text(encoding="utf-8"))
        if not segments:
            raise SystemExit(f"No speaker turns parsed from {script}")

        parts: list[np.ndarray] = []
        sample_rate = 24000
        for turn, segment in enumerate(segments, start=1):
            speaker = segment["speaker"]
            if speaker == "PAUSE":
                parts.append(np.zeros(int(PAUSE_SECONDS * sample_rate), dtype=np.float32))
                continue
            voice = args.male_voice if speaker == MALE_SPEAKER else args.female_voice
            text = safe_text(segment["text"])
            for chunk in split_text(text, MAX_SEGMENT_CHARS):
                samples, sample_rate = kokoro.create(
                    chunk, voice=voice, speed=args.speed, lang="en-us"
                )
                parts.append(np.asarray(samples, dtype=np.float32))
            next_speaker = segments[turn]["speaker"] if turn < len(segments) else None
            if next_speaker and next_speaker != "PAUSE":
                gap = SAME_SPEAKER_GAP if next_speaker == speaker else SPEAKER_CHANGE_GAP
                parts.append(np.zeros(int(gap * sample_rate), dtype=np.float32))
            if turn % 10 == 0 or turn == len(segments):
                print(f"    {turn}/{len(segments)} turns", flush=True)

        parts.append(np.zeros(int(FINAL_TAIL * sample_rate), dtype=np.float32))
        audio = np.concatenate(parts)
        sf.write(out_wav, audio, sample_rate)
        durations[slug] = round(len(audio) / sample_rate, 1)
        if not args.wav_only:
            convert_to_mp3(out_wav, out_mp3)
        minutes = durations[slug] / 60
        print(f"    done: {minutes:.1f} minutes")

    if durations:
        report = AUDIO_DIR / "durations.json"
        existing = {}
        if report.exists():
            try:
                existing = json.loads(report.read_text(encoding="utf-8"))
            except ValueError:
                existing = {}
        existing.update(durations)
        report.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print("All requested episodes generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
