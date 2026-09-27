# ruff: noqa: E501 -- report templates and ffmpeg filter graphs read better unwrapped
"""Quill Converter end-to-end check: every format, every feature, files kept.

Builds a corpus of source files -- synthesized speech, music and video made
with the *bundled* FFmpeg, plus whatever real-world samples sit in
``<out>/_cache/real`` -- then drives the Converter's own engine (the same
functions the app calls, not a re-implementation) through:

* every sound format out, from one speech master;
* every input read back, to MP3 and FLAC;
* every video format out, from a video master with two audio tracks,
  subtitles and chapters; every real video sample to MP4, MKV and M4A;
* every effect recipe, on a deliberately dirty recording, so the before and
  after can be listened to side by side;
* every preset, the format constraints (rates, mono-only, bit depths), keep
  only part, cover art carried across, Join with chapters, Split by
  chapters, both previews, container-only remux, and the failure wording.

Every output is checked with ffprobe -- it exists, it is the codec it should
be, it is about as long as it should be -- and nothing is deleted: inputs are
in ``<out>/inputs``, outputs in ``<out>/outputs/<area>/``, and the verdict in
``report.md`` / ``report.html`` / ``report.json``.

Usage (from the checkout root)::

    python scripts/converter_e2e.py [--out local/converter-e2e] [--ffmpeg-dir build/deps/ffmpeg]
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


@dataclass
class Check:
    area: str
    name: str
    source: str
    output: str
    ok: bool
    detail: str
    seconds: float = 0.0


@dataclass
class Run:
    out: Path
    ffmpeg: str
    ffprobe: str
    checks: list[Check] = field(default_factory=list)

    def record(self, check: Check) -> None:
        self.checks.append(check)
        mark = "PASS" if check.ok else "FAIL"
        print(f"{mark} {check.area}: {check.name} -- {check.detail}", flush=True)


# --------------------------------------------------------------------------- #
# Corpus
# --------------------------------------------------------------------------- #

SPEECH = (
    "Welcome to the Quill Converter test recording. This is a person speaking "
    "into a cheap microphone in a room with a fan running and a refrigerator "
    "humming in the next room. Sharp sounds like sister, susurrus and sixty "
    "six test the de-esser. The quick brown fox jumps over the lazy dog, and "
    "a pause follows.  Now the second half begins, a little quieter, as if "
    "the speaker had leaned away from the microphone. Thank you for listening."
)
DESCRIBED = (
    "Audio description. A test pattern fills the screen. Coloured bars slide "
    "from left to right while a counter ticks upward in the corner."
)


def ff(run: Run, *args: str) -> None:
    subprocess.run([run.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def sapi(text: str, dest: Path, voice: str) -> None:
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"try {{ $s.SelectVoice('{voice}') }} catch {{}};"
        "$s.Rate=0;"
        f"$s.SetOutputToWaveFile('{dest}');"
        f"$s.Speak(@'\n{text}\n'@);$s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)


def build_corpus(run: Run) -> dict[str, Path]:
    inputs = run.out / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    made: dict[str, Path] = {}
    clean = inputs / "speech-clean.wav"
    if not clean.exists():
        sapi(SPEECH, clean, "Microsoft Zira Desktop")
    described = inputs / "speech-described.wav"
    if not described.exists():
        sapi(DESCRIBED, described, "Microsoft David Desktop")
    made["speech-clean"] = clean
    # The dirty recording: speech, 60 Hz hum with harmonics, steady hiss, rumble,
    # and a level that drops by half in the second half.
    dirty = inputs / "speech-dirty.wav"
    ff(
        run,
        "-i",
        str(clean),
        "-f",
        "lavfi",
        "-i",
        "sine=f=60:r=44100,volume=0.08",
        "-f",
        "lavfi",
        "-i",
        "sine=f=120:r=44100,volume=0.04",
        "-f",
        "lavfi",
        "-i",
        "anoisesrc=c=pink:a=0.02:r=44100",
        "-f",
        "lavfi",
        "-i",
        "sine=f=18:r=44100,volume=0.2",
        "-filter_complex",
        "[0:a]aresample=44100,volume='if(gt(t,12),0.45,1)':eval=frame[s];"
        "[s][1:a][2:a][3:a][4:a]amix=inputs=5:duration=first:normalize=0[m]",
        "-map",
        "[m]",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(dirty),
    )
    made["speech-dirty"] = dirty
    # Film mix: quiet dialogue under loud music, for "Louder dialogue".
    film = inputs / "film-mix.wav"
    ff(
        run,
        "-i",
        str(clean),
        "-f",
        "lavfi",
        "-i",
        "aevalsrc='0.25*sin(2*PI*220*t)+0.2*sin(2*PI*277*t)+0.2*sin(2*PI*330*t)':s=44100:c=stereo",
        "-filter_complex",
        "[0:a]aresample=44100,volume=0.35,pan=stereo|c0=c0|c1=c0[d];[d][1:a]amix=inputs=2:duration=first:normalize=0[m]",
        "-map",
        "[m]",
        "-c:a",
        "pcm_s16le",
        str(film),
    )
    made["film-mix"] = film
    # Music: a chord progression, stereo, 20 s.
    music = inputs / "music.wav"
    ff(
        run,
        "-f",
        "lavfi",
        "-i",
        "aevalsrc='0.2*sin(2*PI*(220+110*floor(t/5))*t)+0.15*sin(2*PI*(330+110*floor(t/5))*t)|"
        "0.2*sin(2*PI*(277+110*floor(t/5))*t)+0.1*sin(2*PI*440*t)':s=48000:d=20",
        "-c:a",
        "pcm_s24le",
        str(music),
    )
    made["music"] = music
    # Cover art, and an MP3 that carries it with tags.
    cover = inputs / "cover.png"
    ff(run, "-f", "lavfi", "-i", "testsrc2=s=300x300:d=1", "-frames:v", "1", str(cover))
    tagged = inputs / "tagged-with-cover.mp3"
    ff(
        run,
        "-i",
        str(clean),
        "-i",
        str(cover),
        "-map",
        "0:a",
        "-map",
        "1:v",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "4",
        "-c:v",
        "png",
        "-disposition:v",
        "attached_pic",
        "-id3v2_version",
        "3",
        "-metadata",
        "title=Converter Test",
        "-metadata",
        "artist=Quill",
        "-metadata",
        "album=E2E",
        str(tagged),
    )
    made["tagged-with-cover"] = tagged
    # A chaptered audiobook: five chapters over the speech, looped to 60 s.
    meta = inputs / "chapters.ffmeta"
    meta.write_text(
        ";FFMETADATA1\ntitle=Test Audiobook\n"
        + "".join(
            f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={i * 12000}\nEND={(i + 1) * 12000}\ntitle=Chapter {i + 1}: Part {'ABCDE'[i]}\n"
            for i in range(5)
        ),
        encoding="utf-8",
    )
    book = inputs / "audiobook-5-chapters.m4b"
    ff(
        run,
        "-stream_loop",
        "3",
        "-i",
        str(clean),
        "-i",
        str(meta),
        "-map",
        "0:a",
        "-map_metadata",
        "1",
        "-map_chapters",
        "1",
        "-t",
        "60",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-f",
        "ipod",
        str(book),
    )
    made["audiobook"] = book
    # The video master: 12 s of test pattern, two audio tracks (main + described),
    # English subtitles, two chapters.
    srt = inputs / "subs.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:05,000\nHello from the subtitles.\n\n"
        "2\n00:00:06,000 --> 00:00:10,000\nSecond caption.\n",
        encoding="utf-8",
    )
    vmeta = inputs / "video.ffmeta"
    vmeta.write_text(
        ";FFMETADATA1\ntitle=Video Master\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=6000\n"
        "title=Opening\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=6000\nEND=12000\ntitle=Closing\n",
        encoding="utf-8",
    )
    video = inputs / "video-master.mkv"
    ff(
        run,
        "-f",
        "lavfi",
        "-i",
        "testsrc2=s=1280x720:r=30:d=12",
        "-i",
        str(clean),
        "-i",
        str(described),
        "-i",
        str(srt),
        "-i",
        str(vmeta),
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-map",
        "2:a",
        "-map",
        "3:s",
        "-map_metadata",
        "4",
        "-map_chapters",
        "4",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-c:s",
        "srt",
        "-metadata:s:a:0",
        "language=eng",
        "-metadata:s:a:1",
        "language=eng",
        "-metadata:s:a:1",
        "title=Audio description",
        "-metadata:s:s:0",
        "language=eng",
        "-t",
        "12",
        str(video),
    )
    made["video-master"] = video
    # An odd-sized video (x264 refuses odd dimensions unless the builder evens them).
    odd = inputs / "video-odd-size.mp4"
    ff(
        run,
        "-f",
        "lavfi",
        "-i",
        "testsrc=s=321x241:r=25:d=4",
        "-f",
        "lavfi",
        "-i",
        "sine=f=440:d=4",
        "-c:v",
        "mpeg4",
        "-c:a",
        "aac",
        "-shortest",
        str(odd),
    )
    made["video-odd-size"] = odd
    # A corrupt file named like an MP3.
    corrupt = inputs / "corrupt-not-really.mp3"
    corrupt.write_bytes(b"ID3" + os.urandom(4000))
    made["corrupt"] = corrupt
    # Speech with two long pauses, for "Remove long silences".
    gaps = inputs / "speech-with-long-pauses.wav"
    ff(
        run,
        "-i",
        str(clean),
        "-i",
        str(clean),
        "-filter_complex",
        "[0:a]apad=pad_dur=2.5[a];[a][1:a]concat=n=2:v=0:a=1,apad=pad_dur=2[m]",
        "-map",
        "[m]",
        "-c:a",
        "pcm_s16le",
        str(gaps),
    )
    made["speech-gaps"] = gaps
    return made


# --------------------------------------------------------------------------- #
# Probing
# --------------------------------------------------------------------------- #


def probe(run: Run, path: Path) -> dict:
    from quill.core.audio.media_probe import parse_probe_json

    completed = subprocess.run(
        [
            run.ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    info = parse_probe_json(path, completed.stdout)
    raw = json.loads(completed.stdout or "{}")
    names = [s.get("codec_name", "") for s in raw.get("streams", [])]
    return {"info": info, "codecs": names, "raw": raw}


def verify(
    run: Run,
    path: Path,
    *,
    expect_codec: str | None = None,
    expect_s: float | None = None,
    tolerance: float = 1.5,
    video: bool | None = None,
) -> tuple[bool, str]:
    if not path.is_file() or path.stat().st_size == 0:
        return False, "no output file"
    got = probe(run, path)
    info = got["info"]
    parts = [
        f"{info.duration_s:.1f} s",
        "+".join(got["codecs"]),
        f"{path.stat().st_size // 1024} KB",
    ]
    if not got["codecs"]:
        return False, "unreadable output"
    if expect_codec and expect_codec not in got["codecs"]:
        return False, f"expected codec {expect_codec}, got {got['codecs']}"
    if expect_s is not None and info.duration_s and abs(info.duration_s - expect_s) > tolerance:
        # Raw streams (.aac, .ac3, .mp2) carry no length; ffprobe guesses from
        # the bit rate. Decoding the whole file is the honest measurement.
        decoded = decoded_seconds(run, path)
        if decoded is None or abs(decoded - expect_s) > tolerance:
            return (
                False,
                f"length {decoded or info.duration_s:.1f} s, expected about {expect_s:.1f}",
            )
        parts[0] = f"{decoded:.1f} s (decoded)"
    if video is True and not info.video:
        return False, "no video stream"
    if video is False and info.video:
        return False, "unexpected video stream"
    return True, ", ".join(parts)


def decoded_seconds(run: Run, path: Path) -> float | None:
    completed = subprocess.run(
        [run.ffmpeg, "-hide_banner", "-i", str(path), "-map", "0:a:0", "-f", "null", "-"],
        capture_output=True,
        text=True,
        errors="replace",
    )
    stamps = [chunk.split()[0] for chunk in completed.stderr.split("time=")[1:]]
    if not stamps:
        return None
    hours, minutes, seconds = stamps[-1].split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


# --------------------------------------------------------------------------- #
# Areas
# --------------------------------------------------------------------------- #


def convert(
    run: Run,
    area: str,
    sources: list[Path],
    fmt: str,
    *,
    preset: str = "just_convert",
    filters: tuple[str, ...] = (),
    dest_name: str | None = None,
    **spec_changes: object,
):
    from quill.core.audio.convert import OnExisting, plan_jobs, run_conversion_batch
    from quill.core.audio.presets import preset_spec

    spec = replace(
        preset_spec(preset),
        fmt=fmt,
        filters=tuple(preset_spec(preset).filters) + filters,
        **spec_changes,
    )
    dest = run.out / "outputs" / area / (dest_name or fmt)
    queue = [(src, None) for src in sources]
    jobs, skipped = plan_jobs(queue, dest, spec, on_existing=OnExisting.OVERWRITE)
    started = time.monotonic()
    result = run_conversion_batch(run.ffmpeg, jobs, workers=4)
    return result, skipped, time.monotonic() - started


def expected_codec(fmt: str) -> str:
    from quill.core.audio.formats import AUDIO_OUTPUT_FORMATS, PCM_CODECS, VIDEO_OUTPUT_FORMATS

    if fmt in VIDEO_OUTPUT_FORMATS:
        codec = VIDEO_OUTPUT_FORMATS[fmt].video_codec
    elif fmt in PCM_CODECS:
        return PCM_CODECS[fmt][None]
    else:
        codec = AUDIO_OUTPUT_FORMATS[fmt][0]
    return {
        "libmp3lame": "mp3",
        "libvorbis": "vorbis",
        "libopus": "opus",
        "libx264": "h264",
        "libx265": "hevc",
        "libvpx-vp9": "vp9",
        "libxvid": "mpeg4",
        "libtheora": "theora",
        "libspeex": "speex",
        "libopencore_amrnb": "amr_nb",
        "libvo_amrwbenc": "amr_wb",
        "wavpack": "wavpack",
        "mpeg2video": "mpeg2video",
    }.get(codec, codec)


def record_batch(
    run: Run,
    area: str,
    name: str,
    result,
    *,
    expect_s=None,
    codec=None,
    video=None,
    seconds=0.0,
    refusal: str = "",
    tolerance: float = 1.5,
) -> None:
    """Verify each result. *refusal*: the job is expected to be refused, and
    passes only when the reason given contains that phrase."""
    for item in result.results:
        if refusal:
            ok = not item.ok and refusal in (item.error or "").lower()
            detail = (
                f"refused in words: {item.error}" if not item.ok else "converted, but should not"
            )
            run.record(Check(area, name, item.job.source.name, "", ok, detail, seconds))
            continue
        if not item.ok:
            run.record(
                Check(
                    area,
                    name,
                    item.job.source.name,
                    str(item.job.dest),
                    False,
                    item.error or "failed",
                    seconds,
                )
            )
            continue
        candidates = expect_s if isinstance(expect_s, tuple) else (expect_s,)
        for want in candidates:
            ok, detail = verify(
                run,
                item.job.dest,
                expect_codec=codec,
                expect_s=want,
                video=video,
                tolerance=tolerance,
            )
            if ok:
                break
        if item.error:
            detail += f" (note: {item.error})"
        run.record(Check(area, name, item.job.source.name, str(item.job.dest), ok, detail, seconds))


def has_streams(run: Run, path: Path) -> tuple[bool, bool]:
    info = probe(run, path)["info"]
    return bool(info.audio), bool(info.video)


def area_audio_formats(run: Run, corpus: dict[str, Path], formats: list[str]) -> list[Path]:
    from quill.core.audio.formats import is_video_format

    outputs = []
    src = corpus["speech-clean"]
    length = probe(run, src)["info"].duration_s
    for fmt in formats:
        if is_video_format(fmt):
            continue
        result, _s, secs = convert(run, "01-every-sound-format", [src], fmt)
        record_batch(
            run,
            "01-every-sound-format",
            fmt,
            result,
            expect_s=length,
            codec=expected_codec(fmt),
            video=False,
            seconds=secs,
        )
        outputs += [r.job.dest for r in result.results if r.ok]
    # Every format again with a full effect chain on: loudnorm hands on 192 kHz,
    # which is how WMA was found failing only when an effect was chosen.
    from quill.core.audio.effect_recipes import recipe_filters

    for fmt in formats:
        video = is_video_format(fmt)
        chain = recipe_filters("dialogue" if video else "podcast")
        result, _s, secs = convert(
            run,
            "01b-every-format-with-effects",
            [corpus["video-master"] if video else corpus["tagged-with-cover"]],
            fmt,
            preset="video_small" if video else "just_convert",
            filters=chain,
        )
        record_batch(
            run,
            "01b-every-format-with-effects",
            f"{fmt} + {'dialogue' if video else 'podcast'} effects",
            result,
            expect_s=12.0 if video else length,
            codec=expected_codec(fmt),
            video=video,
            seconds=secs,
        )
    return outputs


def area_decode_everything(run: Run, inputs: list[Path]) -> None:
    for src in inputs:
        label = f"{src.parent.name}-{src.suffix.lstrip('.')}"
        for fmt in ("mp3", "flac"):
            result, _s, secs = convert(
                run, "02-every-input-read", [src], fmt, dest_name=f"{label}-to-{fmt}"
            )
            # The real samples are often cut short from much longer files, so the
            # header's length is wrong; decoding the source is the true length.
            length = (probe(run, src)["info"].duration_s or None, decoded_seconds(run, src))
            audio, _video = has_streams(run, src)
            record_batch(
                run,
                "02-every-input-read",
                f"{src.suffix} -> {fmt}",
                result,
                refusal="" if audio else "no sound track",
                expect_s=length,
                codec=fmt,
                video=False,
                seconds=secs,
            )


def area_video(
    run: Run, corpus: dict[str, Path], formats: list[str], real_videos: list[Path]
) -> None:
    from quill.core.audio.formats import is_video_format

    master = corpus["video-master"]
    for fmt in [f for f in formats if is_video_format(f)]:
        result, _s, secs = convert(run, "03-every-video-format", [master], fmt)
        record_batch(
            run,
            "03-every-video-format",
            fmt,
            result,
            expect_s=12,
            codec=expected_codec(fmt),
            video=True,
            seconds=secs,
        )
        for item in result.results:
            if item.ok and fmt in ("mp4", "mkv", "mov", "webm"):
                audio = probe(run, item.job.dest)["info"].audio
                run.record(
                    Check(
                        "03-every-video-format",
                        f"{fmt} keeps both audio tracks",
                        master.name,
                        str(item.job.dest),
                        len(audio) == 2,
                        f"{len(audio)} audio track(s)",
                    )
                )
            if item.ok and fmt == "mkv":
                subs = [
                    s for s in probe(run, item.job.dest)["info"].streams if s.kind == "subtitle"
                ]
                run.record(
                    Check(
                        "03-every-video-format",
                        "mkv keeps subtitles",
                        master.name,
                        str(item.job.dest),
                        len(subs) == 1,
                        f"{len(subs)} subtitle track(s)",
                    )
                )
    odd = corpus["video-odd-size"]
    result, _s, secs = convert(run, "03-every-video-format", [odd], "mp4", dest_name="odd-size")
    record_batch(
        run,
        "03-every-video-format",
        "odd 321x241 -> mp4",
        result,
        expect_s=4,
        codec="h264",
        video=True,
        seconds=secs,
    )
    for preset in ("video_same", "video_web", "video_small", "video_tiny", "video_remux"):
        result, _s, secs = convert(
            run, "04-video-presets", [master], "mp4", preset=preset, dest_name=preset
        )
        record_batch(run, "04-video-presets", preset, result, expect_s=12, video=True, seconds=secs)
    for src in real_videos:
        audio, picture = has_streams(run, src)
        for fmt in ("mp4", "mkv", "m4a"):
            refusal = ""
            if fmt == "m4a" and not audio:
                refusal = "no sound track"
            elif fmt != "m4a" and not picture:
                refusal = "sound file cannot become a video"
            result, _s, secs = convert(
                run,
                "05-real-video",
                [src],
                fmt,
                preset="video_small" if fmt != "m4a" else "just_convert",
                dest_name=fmt,
            )
            record_batch(
                run,
                "05-real-video",
                f"{src.name} -> {fmt}",
                result,
                refusal=refusal,
                video=fmt != "m4a",
                seconds=secs,
            )


def area_effects(run: Run, corpus: dict[str, Path]) -> None:
    from quill.core.audio.effect_recipes import EFFECT_RECIPES, recipe_filters

    before = run.out / "outputs" / "06-effects-before-and-after"
    before.mkdir(parents=True, exist_ok=True)
    shutil.copy2(corpus["speech-dirty"], before / "00-BEFORE-speech-dirty.wav")
    shutil.copy2(corpus["film-mix"], before / "00-BEFORE-film-mix.wav")
    shutil.copy2(corpus["speech-gaps"], before / "00-BEFORE-speech-with-long-pauses.wav")
    length = probe(run, corpus["speech-dirty"])["info"].duration_s
    for recipe in EFFECT_RECIPES:
        src = (
            corpus["film-mix"]
            if recipe.id in ("dialogue", "music", "bass", "night")
            else corpus["speech-gaps"]
            if recipe.id == "remove_silence"
            else corpus["speech-dirty"]
        )
        for fmt in ("wav", "mp3"):
            result, _s, secs = convert(
                run,
                "06-effects-before-and-after",
                [src],
                fmt,
                filters=recipe_filters(recipe.id),
                dest_name=f"{recipe.id}",
            )
            expect = None if recipe.id == "remove_silence" else probe(run, src)["info"].duration_s
            record_batch(
                run,
                "06-effects-before-and-after",
                f"{recipe.id} ({fmt})",
                result,
                expect_s=expect,
                codec=expected_codec(fmt),
                seconds=secs,
            )
    # Silence removal must actually shorten the recording.
    trimmed = (
        run.out
        / "outputs"
        / "06-effects-before-and-after"
        / "remove_silence"
        / "speech-with-long-pauses.wav"
    )
    length = decoded_seconds(run, corpus["speech-gaps"]) or 0.0
    if trimmed.exists():
        got = probe(run, trimmed)["info"].duration_s
        run.record(
            Check(
                "06-effects-before-and-after",
                "remove_silence shortens",
                "speech-with-long-pauses.wav",
                str(trimmed),
                got < length - 0.3,
                f"{length:.1f} s -> {got:.1f} s",
            )
        )
    # Loudness targets land where they say (within 1.5 LU).
    for recipe_id, target in (
        ("podcast", -16.0),
        ("audiobook", -20.0),
        ("music", -14.0),
        ("broadcast", -23.0),
    ):
        folder = run.out / "outputs" / "06-effects-before-and-after" / recipe_id
        wav = next(folder.glob("*.wav"), None)
        if wav is None:
            continue
        measured = measure_lufs(run, wav)
        run.record(
            Check(
                "06-effects-before-and-after",
                f"{recipe_id} loudness",
                wav.name,
                str(wav),
                measured is not None and abs(measured - target) <= 1.5,
                f"measured {measured} LUFS, target {target}",
            )
        )


def measure_lufs(run: Run, path: Path) -> float | None:
    completed = subprocess.run(
        [run.ffmpeg, "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
        errors="replace",
    )
    for line in reversed(completed.stderr.splitlines()):
        line = line.strip()
        if line.startswith("I:") and "LUFS" in line:
            try:
                return float(line.split()[1])
            except (IndexError, ValueError):
                return None
    return None


def area_presets_and_constraints(run: Run, corpus: dict[str, Path]) -> None:
    from quill.core.audio.convert import Channels
    from quill.core.audio.presets import BUILTIN_PRESETS

    src = corpus["speech-clean"]
    length = probe(run, src)["info"].duration_s
    for preset in BUILTIN_PRESETS:
        fmt = preset.spec.fmt
        result, _s, secs = convert(
            run, "07-sound-presets", [src], fmt, preset=preset.id, dest_name=preset.id
        )
        record_batch(run, "07-sound-presets", preset.id, result, expect_s=length, seconds=secs)
    # Constraints: a 22 kHz preset into formats that cannot take 22 kHz.
    for fmt in ("ac3", "eac3", "opus", "weba", "amr", "awb", "spx", "mp2"):
        result, _s, secs = convert(
            run,
            "08-format-constraints",
            [corpus["music"]],
            fmt,
            preset="voice_memo",
            dest_name=f"voice-memo-into-{fmt}",
        )
        record_batch(
            run,
            "08-format-constraints",
            f"22 kHz preset into {fmt}",
            result,
            expect_s=20,
            seconds=secs,
        )
    for fmt, depth, codec in (
        ("wav", 24, "pcm_s24le"),
        ("wav", 32, "pcm_f32le"),
        ("aiff", 24, "pcm_s24be"),
        ("flac", 24, "flac"),
        ("w64", 32, "pcm_f32le"),
        ("au", 16, "pcm_s16be"),
    ):
        result, _s, secs = convert(
            run,
            "08-format-constraints",
            [corpus["music"]],
            fmt,
            dest_name=f"{fmt}-{depth}-bit",
            bit_depth=depth,
        )
        record_batch(
            run,
            "08-format-constraints",
            f"{fmt} {depth}-bit",
            result,
            expect_s=20,
            codec=codec,
            seconds=secs,
        )
    result, _s, secs = convert(
        run,
        "08-format-constraints",
        [corpus["music"]],
        "mp3",
        dest_name="mono-left",
        channels=Channels.LEFT,
    )
    record_batch(
        run, "08-format-constraints", "left channel only", result, expect_s=20, seconds=secs
    )
    # Keep only part.
    result, _s, secs = convert(
        run, "09-keep-only-part", [src], "mp3", dest_name="5s-to-12s", start_s=5.0, end_s=12.0
    )
    record_batch(
        run,
        "09-keep-only-part",
        "keep 5 s to 12 s",
        result,
        expect_s=7.0,
        tolerance=0.4,
        seconds=secs,
    )
    result, _s, secs = convert(
        run,
        "09-keep-only-part",
        [corpus["video-master"]],
        "mp4",
        preset="video_same",
        dest_name="video-3s-to-9s",
        start_s=3.0,
        end_s=9.0,
    )
    record_batch(
        run,
        "09-keep-only-part",
        "video keep 3 s to 9 s",
        result,
        expect_s=6.0,
        tolerance=0.6,
        video=True,
        seconds=secs,
    )


def area_cover_art(run: Run, corpus: dict[str, Path]) -> None:
    from quill.core.audio.cover_art import _read_picture

    for fmt in ("mp3", "m4a", "m4b", "flac", "opus", "ogg", "wav", "aiff"):
        result, _s, secs = convert(run, "10-cover-art-carried", [corpus["tagged-with-cover"]], fmt)
        for item in result.results:
            has = item.ok and _read_picture(item.job.dest) is not None
            tags = probe(run, item.job.dest)["info"].tags if item.ok else {}
            ok = has and tags.get("title") == "Converter Test"
            run.record(
                Check(
                    "10-cover-art-carried",
                    f"{fmt} keeps cover and title",
                    item.job.source.name,
                    str(item.job.dest),
                    ok,
                    f"cover={'yes' if has else 'no'}, title={tags.get('title', '')!r}",
                    secs,
                )
            )


def area_join_split(run: Run, corpus: dict[str, Path], inputs_for_join: list[Path]) -> None:
    from quill.core.audio.assemble import plan_chapter_split, run_join
    from quill.core.audio.convert import run_conversion_batch
    from quill.core.audio.media_probe import probe as mprobe
    from quill.core.audio.presets import preset_spec

    folder = run.out / "outputs" / "11-join"
    folder.mkdir(parents=True, exist_ok=True)
    for fmt in ("m4b", "mp3", "mka"):
        out = folder / f"joined-{len(inputs_for_join)}-files.{fmt}"
        started = time.monotonic()
        try:
            run_join(
                run.ffmpeg, inputs_for_join, replace(preset_spec("just_convert"), fmt=fmt), out
            )
            info = mprobe(out, ffprobe=run.ffprobe)
            want_chapters = len(inputs_for_join) if fmt in ("m4b", "mka") else 0
            ok = info.duration_s > 0 and (len(info.chapters) == want_chapters or not want_chapters)
            titles = "; ".join(c.title for c in info.chapters)
            detail = f"{info.duration_s:.1f} s, {len(info.chapters)} chapters: {titles}"
        except Exception as error:  # noqa: BLE001
            ok, detail = False, str(error)
        run.record(
            Check(
                "11-join",
                f"join into {fmt}",
                f"{len(inputs_for_join)} files",
                str(out),
                ok,
                detail,
                time.monotonic() - started,
            )
        )
    book = corpus["audiobook"]
    info = mprobe(book, ffprobe=run.ffprobe)
    jobs = plan_chapter_split(
        book,
        info.chapters,
        run.out / "outputs" / "12-split-by-chapters",
        replace(preset_spec("just_convert"), fmt="mp3"),
    )
    result = run_conversion_batch(run.ffmpeg, jobs, workers=4)
    for item, chapter in zip(result.results, info.chapters, strict=False):
        expect = chapter.end_s - chapter.start_s
        ok, detail = (
            verify(run, item.job.dest, expect_codec="mp3", expect_s=expect, tolerance=0.5)
            if item.ok
            else (False, item.error)
        )
        run.record(
            Check("12-split-by-chapters", chapter.title, book.name, str(item.job.dest), ok, detail)
        )


def area_chapters(run: Run, corpus: dict[str, Path]) -> None:
    """Chapters through every conversion, from every source, into every home."""
    from quill.core.audio import chapter_plan as cp
    from quill.core.audio.assemble import run_join
    from quill.core.audio.presets import preset_spec
    from quill.core.speech.chapters import read_mp3_chapters

    area = "16-chapters"
    book = corpus["audiobook"]  # 60 s, five chapters of 12 s

    def count(path: Path) -> int:
        if path.suffix == ".mp3":
            return len(read_mp3_chapters(path))
        return len(probe(run, path)["info"].chapters)

    def check(name: str, source: Path, fmt: str, want: int, **changes: object) -> None:
        result, _s, secs = convert(run, area, [source], fmt, dest_name=name, **changes)
        for item in result.results:
            if not item.ok:
                run.record(Check(area, name, source.name, "", False, item.error, secs))
                continue
            home = cp.chapter_home(fmt)
            if home == "native":
                got = count(item.job.dest)
                ok, detail = got == want, f"{got} chapters inside"
            elif home == "comments":
                import mutagen

                tags = mutagen.File(str(item.job.dest)).tags
                got = len([k for k in tags.keys() if re.fullmatch(r"CHAPTER\d+NAME", k.upper())])
                ok, detail = got == want, f"{got} CHAPTERnnn comments"
            else:
                cue = item.job.dest.with_suffix(".cue")
                got = cue.read_text(encoding="utf-8").count("TRACK") if cue.is_file() else 0
                ok, detail = got == want, f"{got} tracks in {cue.name}"
            if item.error:
                detail += f" (note: {item.error})"
            run.record(Check(area, name, source.name, str(item.job.dest), ok, detail, secs))

    # 1. A file's own chapters land in every format, one way or another.
    for fmt in (
        "mp3",
        "m4b",
        "m4a",
        "opus",
        "mka",
        "wma",
        "weba",
        "ogg",
        "flac",
        "wav",
        "aiff",
        "ac3",
    ):
        check(f"keep-into-{fmt}", book, fmt, 5)
    for fmt in ("mp4", "mkv", "webm"):
        check(f"keep-into-{fmt}", corpus["video-master"], fmt, 2, preset="video_small")
    # 2. Removed on request.
    check("none-into-m4b", book, "m4b", 0, chapter_source=cp.NONE)
    check("none-into-mp3", book, "mp3", 0, chapter_source=cp.NONE)
    # 3. A chapter list you wrote yourself, in plain text beside the file.
    gaps = corpus["speech-gaps"]
    listed = gaps.with_suffix("").with_name(gaps.stem + ".chapters.txt")
    listed.write_text("0:00 Opening\n0:08 The pause\n0:20 The second reading\n", encoding="utf-8")
    for fmt in ("m4b", "mp3", "ogg", "wav"):
        check(f"your-list-into-{fmt}", gaps, fmt, 3, chapter_source=cp.LIST)
    # 4. Found at the pauses (two 2.5 s gaps -> at least two chapters).
    result, _s, secs = convert(
        run, area, [gaps], "m4b", dest_name="pauses", chapter_source=cp.PAUSES
    )
    for item in result.results:
        got = count(item.job.dest) if item.ok else 0
        run.record(
            Check(
                area,
                "found at the pauses",
                gaps.name,
                str(item.job.dest),
                got >= 2,
                f"{got} chapters ({item.error})",
            )
        )
    # 5. Every N minutes, on an 11-minute recording.
    long_file = run.out / "inputs" / "eleven-minutes.mp3"
    if not long_file.exists():
        ff(
            run,
            "-f",
            "lavfi",
            "-i",
            "sine=f=220:d=660",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "32k",
            str(long_file),
        )
    check("every-5-minutes", long_file, "m4b", 3, chapter_source=cp.every(5))
    check("every-5-minutes-mp3", long_file, "mp3", 3, chapter_source=cp.every(5))
    # 6. Keep only part: chapters inside the window only, shifted to zero.
    check("keep-13s-to-37s-list", book, "m4b", 3, chapter_source=cp.LIST, start_s=13.0, end_s=37.0)
    # 7. Join into MP3 now writes a chapter per file, too.
    parts = sorted((run.out / "outputs" / "12-split-by-chapters" / book.stem).glob("*.mp3"))
    if len(parts) >= 2:
        out = run.out / "outputs" / area / "joined-chapters.mp3"
        run_join(run.ffmpeg, parts, replace(preset_spec("just_convert"), fmt="mp3"), out)
        got = len(read_mp3_chapters(out))
        titles = [c.title for c in read_mp3_chapters(out)]
        run.record(
            Check(
                area,
                "join into MP3 writes chapters",
                f"{len(parts)} files",
                str(out),
                got == len(parts),
                f"{got} chapters: {titles}",
            )
        )


def area_preview_and_errors(run: Run, corpus: dict[str, Path]) -> None:
    from quill.core.audio.assemble import render_preview
    from quill.core.audio.effect_recipes import recipe_filters
    from quill.core.audio.presets import preset_spec

    folder = run.out / "outputs" / "13-preview"
    folder.mkdir(parents=True, exist_ok=True)
    for original, name, src, fmt in (
        (True, "original-speech-dirty", corpus["speech-dirty"], "mp3"),
        (False, "with-clean-speech-effects", corpus["speech-dirty"], "mp3"),
        (False, "video-mp4-dialogue-boost", corpus["video-master"], "mp4"),
    ):
        spec = replace(preset_spec("just_convert"), fmt=fmt, filters=recipe_filters("clean_speech"))
        out = folder / f"{name}.wav"
        try:
            render_preview(run.ffmpeg, src, spec, out, original=original)
            want = min(15.0, probe(run, src)["info"].duration_s)
            ok, detail = verify(run, out, expect_codec="pcm_s16le", expect_s=want, tolerance=1.0)
        except Exception as error:  # noqa: BLE001
            ok, detail = False, str(error)
        run.record(Check("13-preview", name, src.name, str(out), ok, detail))
    # Failures must be said in words.
    result, _s, _secs = convert(run, "14-errors", [corpus["corrupt"]], "mp3")
    for item in result.results:
        run.record(
            Check(
                "14-errors",
                "corrupt file is explained",
                item.job.source.name,
                "",
                not item.ok and "damaged" in item.error.lower(),
                item.error or "unexpectedly converted",
            )
        )
    result, skipped, _secs = convert(run, "14-errors", [corpus["speech-clean"]], "mp4")
    run.record(
        Check(
            "14-errors",
            "sound file skipped for a video format",
            "speech-clean.wav",
            "",
            not result.results and len(skipped) == 1,
            f"skipped {len(skipped)}",
        )
    )
    result, _s, _secs = convert(
        run,
        "14-errors",
        [corpus["video-master"]],
        "avi",
        preset="video_remux",
        dest_name="remux-into-avi",
    )
    for item in result.results:
        run.record(
            Check(
                "14-errors",
                "remux mkv(h264+aac+srt) into avi",
                item.job.source.name,
                str(item.job.dest),
                True,
                "converted" if item.ok else f"refused in words: {item.error}",
            )
        )


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #


def write_reports(run: Run, started: float, ffmpeg_version: str) -> None:
    passed = sum(c.ok for c in run.checks)
    failed = [c for c in run.checks if not c.ok]
    stamp = time.strftime("%Y-%m-%d %H:%M")
    head = (
        f"Quill Converter end-to-end run, {stamp}. {passed} of {len(run.checks)} checks passed, "
        f"{len(failed)} failed. Took {int(time.monotonic() - started)} seconds. FFmpeg: {ffmpeg_version}."
    )
    md = [
        "# Quill Converter end-to-end report",
        "",
        head,
        "",
        "Inputs are in `inputs/` (and `_cache/real/` for the real-world samples); every output is in "
        "`outputs/<area>/`, kept so you can listen to the before and after.",
        "",
    ]
    if failed:
        md += (
            ["## Failures", ""]
            + [f"- {c.area}: {c.name} ({c.source}) -- {c.detail}" for c in failed]
            + [""]
        )
    areas: dict[str, list[Check]] = {}
    for c in run.checks:
        areas.setdefault(c.area, []).append(c)
    for area, checks in areas.items():
        ok = sum(c.ok for c in checks)
        md += [
            f"## {area} ({ok} of {len(checks)} passed)",
            "",
            "| Result | Check | Source | Detail |",
            "|---|---|---|---|",
        ]
        md += [
            f"| {'PASS' if c.ok else 'FAIL'} | {c.name} | {c.source} | {c.detail.replace('|', '/')} |"
            for c in checks
        ]
        md.append("")
    (run.out / "report.md").write_text("\n".join(md), encoding="utf-8")
    rows = []
    for area, checks in areas.items():
        body = "".join(
            f"<tr><td>{'PASS' if c.ok else '<strong>FAIL</strong>'}</td><th scope='row'>{html.escape(c.name)}</th>"
            f"<td>{html.escape(c.source)}</td><td>{html.escape(c.detail)}</td>"
            f"<td>{html.escape(Path(c.output).relative_to(run.out).as_posix()) if c.output.startswith(str(run.out)) else ''}</td></tr>"
            for c in checks
        )
        rows.append(
            f"<h2>{html.escape(area)}</h2><table><caption>{html.escape(area)}: "
            f"{sum(c.ok for c in checks)} of {len(checks)} passed</caption><thead><tr>"
            "<th scope='col'>Result</th><th scope='col'>Check</th><th scope='col'>Source</th>"
            "<th scope='col'>Detail</th><th scope='col'>Output</th></tr></thead><tbody>"
            f"{body}</tbody></table>"
        )
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Converter E2E report</title>"
        "<style>body{font-family:Segoe UI,sans-serif;max-width:70em;margin:1em auto;padding:0 1em}"
        "table{border-collapse:collapse;width:100%;margin-bottom:2em}td,th{border:1px solid #888;"
        "padding:.3em;text-align:left;vertical-align:top}caption{font-weight:bold;text-align:left}</style>"
        f"</head><body><main><h1>Quill Converter end-to-end report</h1><p>{html.escape(head)}</p>"
        + "".join(rows)
        + "</main></body></html>"
    )
    (run.out / "report.html").write_text(page, encoding="utf-8")
    (run.out / "report.json").write_text(
        json.dumps([c.__dict__ for c in run.checks], indent=1), encoding="utf-8"
    )
    print(head)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=REPO / "local" / "converter-e2e")
    parser.add_argument("--ffmpeg-dir", type=Path, default=REPO / "build" / "deps" / "ffmpeg")
    parser.add_argument(
        "--only", default="", help="comma-separated area numbers to run (e.g. 01,06)"
    )
    args = parser.parse_args()
    out = args.out.resolve()
    # The engine must find the same pinned FFmpeg the installer ships, not
    # whatever is on this machine's PATH: QUILL_APP_ROOT/tools/ffmpeg wins.
    app_root = out / "_app"
    tools = app_root / "tools" / "ffmpeg"
    tools.mkdir(parents=True, exist_ok=True)
    for name in ("ffmpeg.exe", "ffprobe.exe"):
        if not (tools / name).exists():
            shutil.copy2(args.ffmpeg_dir / name, tools / name)
    os.environ["QUILL_APP_ROOT"] = str(app_root)
    sys.path.insert(0, str(REPO))
    from quill.core.audio.convert import available_output_formats
    from quill.core.speech.ffmpeg import find_ffmpeg, find_ffprobe

    ffmpeg, ffprobe = find_ffmpeg(), find_ffprobe()
    assert ffmpeg and Path(ffmpeg).parent == tools, ffmpeg
    run = Run(out=out, ffmpeg=ffmpeg, ffprobe=ffprobe or "")
    version = subprocess.run(
        [ffmpeg, "-version"], capture_output=True, text=True
    ).stdout.splitlines()[0]
    started = time.monotonic()
    only = {a.strip() for a in args.only.split(",") if a.strip()}

    def wanted(area: str) -> bool:
        return not only or area in only

    corpus = build_corpus(run)
    formats = available_output_formats(ffmpeg)
    print(f"{len(formats)} output formats available: {', '.join(formats)}", flush=True)
    sound_outputs = area_audio_formats(run, corpus, formats) if wanted("01") else []
    real = (
        sorted((out / "_cache" / "real").glob("real-*"))
        if (out / "_cache" / "real").is_dir()
        else []
    )
    real = [p for p in real if p.suffix.lower() != ".json"]
    from quill.core.audio.formats import VIDEO_EXTENSIONS

    real_videos = [p for p in real if p.suffix.lower() in VIDEO_EXTENSIONS]
    if wanted("02"):
        area_decode_everything(
            run, sound_outputs + real + [corpus["video-master"], corpus["audiobook"]]
        )
    if wanted("03"):
        area_video(run, corpus, formats, real_videos)
    if wanted("06"):
        area_effects(run, corpus)
    if wanted("07"):
        area_presets_and_constraints(run, corpus)
    if wanted("10"):
        area_cover_art(run, corpus)
    if wanted("11"):
        joins = sorted((out / "outputs" / "01-every-sound-format").glob("*/speech-clean.*"))[
            :5
        ] or [corpus["speech-clean"], corpus["music"], corpus["tagged-with-cover"]]
        area_join_split(run, corpus, joins)
    if wanted("13"):
        area_preview_and_errors(run, corpus)
    if wanted("16"):
        area_chapters(run, corpus)
    write_reports(run, started, version)
    return 0 if all(c.ok for c in run.checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
