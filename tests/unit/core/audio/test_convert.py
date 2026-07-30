"""Tests for the universal audio converter core (#1255)."""

from __future__ import annotations

import os
from pathlib import Path

from quill.core.audio import convert as cv
from quill.core.audio.convert import (
    Channels,
    ConversionJob,
    ConversionSpec,
    OnExisting,
)

# --------------------------------------------------------------------------- #
# Command building
# --------------------------------------------------------------------------- #


def _job(source: str, dest: str, spec: ConversionSpec) -> ConversionJob:
    return ConversionJob(source=Path(source), dest=Path(dest), spec=spec)


def test_build_command_mp3_vbr_default() -> None:
    cmd = cv.build_convert_command("ffmpeg", _job("in.wav", "out.mp3", ConversionSpec(fmt="mp3")))
    assert cmd[0] == "ffmpeg"
    assert "-i" in cmd and "in.wav" in cmd
    assert "-c:a" in cmd and "libmp3lame" in cmd
    assert "-q:a" in cmd  # VBR by default
    assert "-b:a" not in cmd
    assert cmd[-1] == "out.mp3"


def test_build_command_mp3_cbr_bitrate_wins_over_vbr() -> None:
    cmd = cv.build_convert_command(
        "ffmpeg", _job("in.flac", "out.mp3", ConversionSpec(fmt="mp3", bitrate_kbps=320))
    )
    assert "-b:a" in cmd and "320k" in cmd
    assert "-q:a" not in cmd


def test_build_command_wav_bit_depth_selects_pcm_codec() -> None:
    cmd = cv.build_convert_command(
        "ffmpeg", _job("in.mp3", "out.wav", ConversionSpec(fmt="wav", bit_depth=24))
    )
    assert "pcm_s24le" in cmd
    # A bitrate is meaningless for PCM WAV and must not be emitted.
    assert "-b:a" not in cmd


def test_build_command_flac_bit_depth_uses_sample_fmt() -> None:
    cmd = cv.build_convert_command(
        "ffmpeg", _job("in.wav", "out.flac", ConversionSpec(fmt="flac", bit_depth=24))
    )
    assert "-sample_fmt" in cmd and "s32" in cmd


def test_build_command_mono_downmix_and_sample_rate() -> None:
    cmd = cv.build_convert_command(
        "ffmpeg",
        _job(
            "in.wav",
            "out.mp3",
            ConversionSpec(fmt="mp3", channels=Channels.MONO, sample_rate=22050),
        ),
    )
    joined = " ".join(cmd)
    assert "-af" in cmd and "pan=mono" in joined
    assert "-ar" in cmd and "22050" in cmd


def test_build_command_stereo_uses_ac_two() -> None:
    cmd = cv.build_convert_command(
        "ffmpeg", _job("in.wav", "out.mp3", ConversionSpec(fmt="mp3", channels=Channels.STEREO))
    )
    assert "-ac" in cmd and "2" in cmd


def test_build_command_copy_remux_skips_codec_options() -> None:
    cmd = cv.build_convert_command(
        "ffmpeg",
        _job("in.wav", "out.m4a", ConversionSpec(fmt="m4a", copy_audio=True, bitrate_kbps=256)),
    )
    assert "copy" in cmd
    assert "-b:a" not in cmd and "-af" not in cmd


def test_build_command_extract_from_video_maps_audio() -> None:
    spec = ConversionSpec(fmt="mp3", extract_from_video=True)
    cmd = cv.build_convert_command("ffmpeg", _job("clip.mp4", "out.mp3", spec))
    assert "-map" in cmd and "0:a:0?" in cmd
    assert "-vn" not in cmd


def test_build_command_out_path_override_for_temp_write() -> None:
    cmd = cv.build_convert_command(
        "ffmpeg", _job("in.wav", "final.mp3", ConversionSpec(fmt="mp3")), out_path=Path("tmp.part")
    )
    assert cmd[-1] == "tmp.part"


def test_output_extension_maps_formats() -> None:
    assert ConversionSpec(fmt="mp3").output_extension() == ".mp3"
    assert ConversionSpec(fmt="alac").output_extension() == ".m4a"
    assert ConversionSpec(fmt="m4b").output_extension() == ".m4b"


# --------------------------------------------------------------------------- #
# Capability probe
# --------------------------------------------------------------------------- #

_ENCODERS_SAMPLE = """Encoders:
 V..... = Video
 A..... = Audio
 ------
 A..... libmp3lame           MP3 (MPEG audio layer 3)
 A..... aac                  AAC (Advanced Audio Coding)
 A..... libopus              libopus Opus
 A..... flac                 FLAC (Free Lossless Audio Codec)
 A..... pcm_s16le            PCM signed 16-bit little-endian
 V..... libx264              H.264
"""


def test_parse_encoder_names_extracts_audio_encoders() -> None:
    names = cv.parse_encoder_names(_ENCODERS_SAMPLE)
    assert "libmp3lame" in names
    assert "aac" in names
    assert "libopus" in names
    assert "flac" in names
    assert "libx264" in names  # parsed too; format filtering is separate


def test_available_output_formats_hides_missing_encoders(monkeypatch) -> None:
    monkeypatch.setattr(
        cv, "_default_probe_runner", lambda cmd: type("R", (), {"stdout": _ENCODERS_SAMPLE})()
    )
    cv.clear_probe_cache()
    formats = cv.available_output_formats("ffmpeg")
    assert "mp3" in formats and "opus" in formats and "flac" in formats
    assert "wav" in formats  # always available
    # No libvorbis in the sample -> ogg hidden; no wmav2 -> wma hidden.
    assert "ogg" not in formats
    assert "wma" not in formats


def test_available_output_formats_without_ffmpeg_offers_only_wav() -> None:
    assert cv.available_output_formats(None) == ["wav"]


# --------------------------------------------------------------------------- #
# Planning
# --------------------------------------------------------------------------- #


def _make(root: Path, rel: str, data: bytes = b"x") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def test_plan_jobs_single_file_to_named_output(tmp_path: Path) -> None:
    src = _make(tmp_path, "song.flac")
    jobs, skipped = cv.plan_jobs([(src, None)], tmp_path / "out", ConversionSpec(fmt="mp3"))
    assert not skipped
    assert len(jobs) == 1
    assert jobs[0].dest.name == "song.mp3"


def test_plan_jobs_folder_recurse_mirrors_tree(tmp_path: Path) -> None:
    root = tmp_path / "src"
    _make(root, "a.wav")
    _make(root, "sub/b.wav")
    dest = tmp_path / "out"
    jobs, _ = cv.plan_jobs([(root, root)], dest, ConversionSpec(fmt="mp3"), recurse=True)
    outs = {j.dest.relative_to(dest).as_posix() for j in jobs}
    assert outs == {"a.mp3", "sub/b.mp3"}


def test_plan_jobs_folder_flatten(tmp_path: Path) -> None:
    root = tmp_path / "src"
    _make(root, "a.wav")
    _make(root, "sub/b.wav")
    dest = tmp_path / "out"
    jobs, _ = cv.plan_jobs(
        [(root, root)], dest, ConversionSpec(fmt="mp3"), recurse=True, flatten=True
    )
    outs = {j.dest.parent for j in jobs}
    assert outs == {dest}  # everything flattened into one folder


def test_plan_jobs_non_recursive_skips_subfolders(tmp_path: Path) -> None:
    root = tmp_path / "src"
    _make(root, "a.wav")
    _make(root, "sub/b.wav")
    jobs, _ = cv.plan_jobs(
        [(root, root)], tmp_path / "out", ConversionSpec(fmt="mp3"), recurse=False
    )
    names = {j.source.name for j in jobs}
    assert names == {"a.wav"}


def test_plan_jobs_mixed_files_and_folder(tmp_path: Path) -> None:
    root = tmp_path / "src"
    _make(root, "in_folder.wav")
    loose = _make(tmp_path, "loose.flac")
    jobs, _ = cv.plan_jobs(
        [(root, root), (loose, None)], tmp_path / "out", ConversionSpec(fmt="mp3"), recurse=True
    )
    assert {j.source.name for j in jobs} == {"in_folder.wav", "loose.flac"}


def test_plan_jobs_dedups_overlapping_entries(tmp_path: Path) -> None:
    root = tmp_path / "src"
    f = _make(root, "dup.wav")
    # The same file added directly AND via its folder must plan once.
    jobs, _ = cv.plan_jobs(
        [(root, root), (f, None)], tmp_path / "out", ConversionSpec(fmt="mp3"), recurse=True
    )
    assert len(jobs) == 1


def test_plan_jobs_filename_template(tmp_path: Path) -> None:
    root = tmp_path / "src"
    _make(root, "a.wav")
    _make(root, "b.wav")
    jobs, _ = cv.plan_jobs(
        [(root, root)],
        tmp_path / "out",
        ConversionSpec(fmt="mp3"),
        recurse=True,
        filename_template="{index0}-{stem}",
    )
    names = sorted(j.dest.name for j in jobs)
    assert names == ["0-a.mp3", "1-b.mp3"]


def test_plan_jobs_conflict_rename_auto_numbers(tmp_path: Path) -> None:
    src = _make(tmp_path, "song.wav")
    dest = tmp_path / "out"
    dest.mkdir()
    (dest / "song.mp3").write_bytes(b"existing")  # collision on disk
    jobs, skipped = cv.plan_jobs(
        [(src, None)], dest, ConversionSpec(fmt="mp3"), on_existing=OnExisting.RENAME
    )
    assert not skipped
    assert jobs[0].dest.name == "song (1).mp3"


def test_plan_jobs_conflict_skip(tmp_path: Path) -> None:
    src = _make(tmp_path, "song.wav")
    dest = tmp_path / "out"
    dest.mkdir()
    (dest / "song.mp3").write_bytes(b"existing")
    jobs, skipped = cv.plan_jobs(
        [(src, None)], dest, ConversionSpec(fmt="mp3"), on_existing=OnExisting.SKIP
    )
    assert not jobs and skipped == [src]


def test_plan_jobs_video_marks_extract(tmp_path: Path) -> None:
    src = _make(tmp_path, "clip.mp4")
    jobs, _ = cv.plan_jobs([(src, None)], tmp_path / "out", ConversionSpec(fmt="mp3"))
    assert jobs and jobs[0].spec.extract_from_video is True


def test_plan_jobs_extension_filter(tmp_path: Path) -> None:
    root = tmp_path / "src"
    _make(root, "keep.wav")
    _make(root, "drop.txt")
    jobs, _ = cv.plan_jobs(
        [(root, root)], tmp_path / "out", ConversionSpec(fmt="mp3"), recurse=True
    )
    assert {j.source.name for j in jobs} == {"keep.wav"}


def test_default_destination_is_converted_sibling(tmp_path: Path) -> None:
    assert cv.default_destination(tmp_path).name == "Converted"


# --------------------------------------------------------------------------- #
# Batch runner (fake worker: progress + cancel + isolation)
# --------------------------------------------------------------------------- #


def _spec() -> ConversionSpec:
    return ConversionSpec(fmt="mp3")


def test_run_batch_reports_progress_and_converts_all() -> None:
    jobs = [ConversionJob(Path(f"{i}.wav"), Path(f"{i}.mp3"), _spec()) for i in range(5)]
    seen: list[tuple[int, int]] = []

    def fake_runner(ffmpeg: str, job: ConversionJob) -> cv.JobResult:
        return cv.JobResult(job=job, ok=True)

    result = cv.run_conversion_batch(
        "ffmpeg",
        jobs,
        workers=2,
        on_progress=lambda done, total, job: seen.append((done, total)),
        single_runner=fake_runner,
    )
    assert result.converted == 5
    assert not result.failed
    assert seen[-1] == (5, 5)  # progress reaches total


def test_run_batch_isolates_a_failing_job() -> None:
    jobs = [ConversionJob(Path(f"{i}.wav"), Path(f"{i}.mp3"), _spec()) for i in range(3)]

    def fake_runner(ffmpeg: str, job: ConversionJob) -> cv.JobResult:
        if job.source.name == "1.wav":
            raise RuntimeError("unreadable")
        return cv.JobResult(job=job, ok=True)

    result = cv.run_conversion_batch("ffmpeg", jobs, workers=1, single_runner=fake_runner)
    assert result.converted == 2
    assert len(result.failed) == 1
    assert "unreadable" in result.failed[0].error


def test_run_batch_cancel_skips_remaining() -> None:
    token = cv.CancelToken()
    token.cancel()  # cancelled before dispatch -> everything skipped
    jobs = [ConversionJob(Path(f"{i}.wav"), Path(f"{i}.mp3"), _spec()) for i in range(4)]
    result = cv.run_conversion_batch(
        "ffmpeg",
        jobs,
        workers=2,
        cancel=token,
        single_runner=lambda f, j: cv.JobResult(job=j, ok=True),
    )
    assert result.cancelled is True
    assert result.converted == 0
    assert result.skipped == 4


def test_batch_summary_names_failures() -> None:
    jobs = [
        ConversionJob(Path("good.wav"), Path("g.mp3"), _spec()),
        ConversionJob(Path("bad.m4a"), Path("b.mp3"), _spec()),
    ]
    result = cv.run_conversion_batch(
        "ffmpeg",
        jobs,
        workers=1,
        single_runner=lambda f, j: cv.JobResult(
            job=j,
            ok=j.source.name == "good.wav",
            error="" if j.source.name == "good.wav" else "unreadable",
        ),
    )
    summary = result.summary(total=2)
    assert "Converted 1 of 2" in summary
    assert "bad.m4a" in summary


def test_default_worker_count_is_positive() -> None:
    assert cv.default_worker_count() >= 1
    assert cv.default_worker_count() <= (os.cpu_count() or 2)


def test_empty_batch_is_a_noop() -> None:
    result = cv.run_conversion_batch("ffmpeg", [], single_runner=lambda f, j: cv.JobResult(j, True))
    assert result.results == [] and result.converted == 0
