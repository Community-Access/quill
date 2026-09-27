"""The 1.0.0 format catalogue and the video half of the command builder."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from quill.core.audio import convert as cv
from quill.core.audio import formats as fm
from quill.core.audio.convert import Channels, ConversionJob, ConversionSpec, build_convert_command


def _cmd(fmt: str, src: str = "in.wav", **changes: object) -> list[str]:
    spec = replace(ConversionSpec(fmt=fmt), **changes)
    return build_convert_command(
        "ffmpeg", ConversionJob(Path(src), Path("out" + spec.output_extension()), spec)
    )


def _after(cmd: list[str], flag: str) -> list[str]:
    return [cmd[i + 1] for i, item in enumerate(cmd[:-1]) if item == flag]


def test_every_ordered_format_has_a_label_a_profile_and_an_extension() -> None:
    assert len(fm.OUTPUT_ORDER) == len(set(fm.OUTPUT_ORDER)) == 34
    for fmt in fm.OUTPUT_ORDER:
        assert fmt in fm.FORMAT_LABELS, fmt
        assert fmt in fm.AUDIO_OUTPUT_FORMATS or fmt in fm.VIDEO_OUTPUT_FORMATS, fmt
        assert fm.output_extension(fmt).startswith("."), fmt


def test_every_audio_output_builds_a_command_ending_in_its_extension() -> None:
    for fmt in fm.OUTPUT_ORDER:
        cmd = _cmd(fmt, "in.mp4" if fm.is_video_format(fmt) else "in.wav")
        assert cmd[-1].endswith(fm.output_extension(fmt)), fmt
        assert "-c:a" in cmd or "-c" in cmd, fmt


def test_input_sets_do_not_overlap_and_cover_the_common_cases() -> None:
    assert not fm.AUDIO_EXTENSIONS & fm.VIDEO_EXTENSIONS
    for ext in (".mp3", ".ape", ".dts", ".amr", ".mpc", ".mod", ".dsf"):
        assert ext in fm.AUDIO_EXTENSIONS, ext
    for ext in (".mts", ".m2ts", ".vob", ".mpg", ".rmvb", ".mxf", ".wtv", ".3gp"):
        assert ext in fm.VIDEO_EXTENSIONS, ext
    wildcard = fm.open_wildcard()
    assert "*.m2ts" in wildcard and "*.ape" in wildcard and wildcard.endswith("*.*")


def test_aiff_and_au_are_big_endian_and_wav_32_is_float() -> None:
    assert _after(_cmd("aiff"), "-c:a") == ["pcm_s16be"]
    assert _after(_cmd("aiff", bit_depth=24), "-c:a") == ["pcm_s24be"]
    assert _after(_cmd("au"), "-c:a") == ["pcm_s16be"]
    assert _after(_cmd("wav", bit_depth=32), "-c:a") == ["pcm_f32le"]
    assert _after(_cmd("wav", bit_depth=24), "-c:a") == ["pcm_s24le"]


def test_a_rate_the_format_cannot_take_moves_to_the_nearest_it_can() -> None:
    assert _after(_cmd("ac3", sample_rate=22050), "-ar") == ["32000"]
    assert _after(_cmd("opus", sample_rate=44100), "-ar") == ["48000"]
    assert _after(_cmd("mp3", sample_rate=22050), "-ar") == ["22050"]
    # MP2 always gets an MPEG-1 rate: at 22 kHz its encoder refuses 192k.
    assert _after(_cmd("mp2"), "-ar") == ["48000"]


def test_amr_is_forced_mono_8k_and_keeps_its_own_bit_rate() -> None:
    cmd = _cmd("amr", bitrate_kbps=320, channels=Channels.STEREO)
    assert _after(cmd, "-ar") == ["8000"]
    assert _after(cmd, "-ac") == ["1"]
    assert _after(cmd, "-b:a") == ["12.2k"]


def test_lossless_formats_ignore_a_preset_bit_rate() -> None:
    for fmt in ("flac", "wv", "tta", "alac", "mka", "wav"):
        assert "-b:a" not in _cmd(fmt, bitrate_kbps=320), fmt


def test_video_command_maps_picture_all_audio_and_subtitles_for_mkv() -> None:
    cmd = _cmd("mkv", "in.mp4")
    maps = _after(cmd, "-map")
    assert maps[:2] == ["0:V:0", "0:a?"] and "0:s?" in maps
    assert _after(cmd, "-c:v") == ["libx264"]
    assert _after(cmd, "-crf") == ["18"]
    assert _after(cmd, "-vf")[0].startswith("scale=")  # always even dimensions


def test_video_presets_set_quality_height_and_remux() -> None:
    from quill.core.audio.presets import preset_spec

    web = build_convert_command(
        "ffmpeg",
        ConversionJob(
            Path("a.mkv"), Path("a.mp4"), replace(preset_spec("video_small"), fmt="webm")
        ),
    )
    assert _after(web, "-crf") == ["40"] and _after(web, "-b:v") == ["0"]
    assert "min(720,ih)" in _after(web, "-vf")[0]
    remux = _cmd("mp4", "a.mkv", copy_video=True)
    assert _after(remux, "-c") == ["copy"] and "-c:v" not in remux and "-af" not in remux


def test_avi_keeps_only_the_first_audio_track() -> None:
    assert "0:a:0?" in _after(_cmd("avi", "in.mkv"), "-map")


def test_keep_only_part_seeks_on_the_input_side() -> None:
    cmd = _cmd("mp3", start_s=5, end_s=12)
    assert cmd.index("-ss") < cmd.index("-i")
    assert _after(cmd, "-ss") == ["5"] and _after(cmd, "-t") == ["7"]
    assert "-ss" not in _cmd("mp3")


def test_plan_jobs_skips_sound_files_for_a_video_format(tmp_path: Path) -> None:
    song = tmp_path / "song.mp3"
    clip = tmp_path / "clip.mkv"
    song.write_bytes(b"x")
    clip.write_bytes(b"x")
    jobs, skipped = cv.plan_jobs(
        [(song, None), (clip, None)], tmp_path / "out", ConversionSpec(fmt="mp4")
    )
    assert [job.source for job in jobs] == [clip] and skipped == [song]


def test_available_formats_needs_both_encoders_for_video(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cv, "_probe_encoders", lambda *_a, **_k: frozenset({"libx264", "libmp3lame"})
    )
    formats = cv.available_output_formats("ffmpeg")
    assert "mp3" in formats and "wav" in formats and "aiff" in formats
    assert "mp4" not in formats  # libx264 alone is not enough: AAC is missing
    assert "avi" not in formats


def test_friendly_errors_quote_the_cause_not_the_consequence() -> None:
    from quill.core.audio.ffmpeg_errors import explain_failure

    text = explain_failure(
        "[mp2 @ 0x1] bitrate 192 is not allowed in mp2\n"
        "[aost#0:0/mp2 @ 0x2] Error while opening encoder - maybe incorrect parameters\n"
        "Nothing was written into output file"
    )
    assert text.startswith("The chosen format could not accept")
    assert "FFmpeg said: bitrate 192 is not allowed in mp2" in text
    assert "damaged" in explain_failure("x.mp3: Invalid data found when processing input")
    assert explain_failure("") == "FFmpeg stopped without saying why."


def test_runner_retries_without_captions_and_with_a_named_channel_count() -> None:
    from quill.core.audio.convert_runner import _retry_spec

    video = ConversionJob(Path("a.ts"), Path("a.mkv"), ConversionSpec(fmt="mkv"))
    retry = _retry_spec(
        video, "[out#0/matroska] Could not write header (incorrect codec parameters ?)"
    )
    assert retry is not None and retry[0].spec.keep_subtitles is False and "Subtitles" in retry[1]
    # Already without captions: nothing left to try.
    assert _retry_spec(retry[0], "Could not write header") is None
    audio = ConversionJob(Path("a.f4v"), Path("a.m4a"), ConversionSpec(fmt="m4a"))
    retry = _retry_spec(audio, '[aac] Unsupported channel layout "1 channels"')
    assert retry is not None and retry[0].spec.force_channels == 1
    assert "-ac" in build_convert_command("ffmpeg", retry[0])
    assert _retry_spec(audio, "Invalid data found when processing input") is None


def test_loudness_normalization_never_hands_on_192_khz() -> None:
    podcast = ("loudnorm=I=-16.0:TP=-1.5:LRA=11.0",)
    assert _after(_cmd("wma", filters=podcast), "-ar") == ["48000"]
    assert _after(_cmd("flac", filters=podcast), "-ar") == ["48000"]
    assert _after(_cmd("wma", filters=podcast, sample_rate=22050), "-ar") == ["22050"]
    assert _after(_cmd("amr", filters=podcast), "-ar") == ["8000"]
    assert "-ar" not in _cmd("wma")
