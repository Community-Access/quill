"""Tests for the headless audio-converter CLI (#1255 CLI)."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from quill.core.audio import convert_cli as cli
from quill.core.audio.convert import Channels, JobResult, OnExisting


def _emit() -> tuple[list[str], cli.Emit]:
    lines: list[str] = []
    return lines, lines.append


def test_safe_print_survives_strict_console(monkeypatch: pytest.MonkeyPatch) -> None:
    class StrictConsole(io.TextIOBase):
        encoding = "cp1252"

        def write(self, s: str) -> int:
            s.encode("cp1252")  # a real cp1252 console raises here on an em-dash
            return len(s)

    monkeypatch.setattr(sys, "stdout", StrictConsole())
    cli._safe_print("audiobook — ACX target")  # must not raise (falls back to replace)


# --------------------------------------------------------------------------- #
# resolve_queue (pure)
# --------------------------------------------------------------------------- #


def test_resolve_queue_files_folders_and_globs(tmp_path: Path) -> None:
    (tmp_path / "a.wav").write_bytes(b"")
    (tmp_path / "b.mp3").write_bytes(b"")
    sub = tmp_path / "sub"
    sub.mkdir()
    queue, unmatched = cli.resolve_queue([
        str(tmp_path / "a.wav"),
        str(sub),
        str(tmp_path / "*.mp3"),
    ])
    kinds = {p.name: root for p, root in queue}
    assert kinds["a.wav"] is None  # a file has no mirror root
    assert kinds["sub"] == sub  # a folder mirrors from itself
    assert kinds["b.mp3"] is None  # matched by glob, still a file
    assert unmatched == []


def test_resolve_queue_reports_unmatched(tmp_path: Path) -> None:
    queue, unmatched = cli.resolve_queue([str(tmp_path / "nope-*.flac")])
    assert queue == []
    assert unmatched == [str(tmp_path / "nope-*.flac")]


# --------------------------------------------------------------------------- #
# resolve_spec (pure)
# --------------------------------------------------------------------------- #


def test_resolve_spec_preset_plus_overrides() -> None:
    ns = cli.build_parser().parse_args([
        "--preset",
        "mp3_320",
        "--to",
        "flac",
        "--sample-rate",
        "48000",
    ])
    spec = cli.resolve_spec(ns)
    assert spec.fmt == "flac"  # --to overrides the preset format
    assert spec.bitrate_kbps == 320  # inherited from mp3_320
    assert spec.sample_rate == 48000  # explicit override


def test_resolve_spec_dsp_flags_compose_filters() -> None:
    ns = cli.build_parser().parse_args([
        "--to",
        "mp3",
        "--high-pass",
        "--loudness",
        "podcast",
        "--fade-out",
        "3",
    ])
    spec = cli.resolve_spec(ns)
    joined = ",".join(spec.filters)
    assert "highpass" in joined
    assert "loudnorm" in joined
    assert spec.filters.count("areverse") == 2  # fade-out


def test_resolve_spec_channels_override() -> None:
    ns = cli.build_parser().parse_args(["--to", "mp3", "--channels", "mono"])
    assert cli.resolve_spec(ns).channels is Channels.MONO


# --------------------------------------------------------------------------- #
# run_cli (injected emit / ffmpeg / runner)
# --------------------------------------------------------------------------- #


def test_run_cli_list_presets_needs_no_ffmpeg() -> None:
    lines, emit = _emit()
    code = cli.run_cli(["--list-presets"], emit=emit, ffmpeg_finder=lambda: None)
    assert code == 0
    assert any("mp3_320" in line for line in lines)


def test_run_cli_no_ffmpeg_is_setup_error(tmp_path: Path) -> None:
    (tmp_path / "a.wav").write_bytes(b"")
    lines, emit = _emit()
    code = cli.run_cli(
        [str(tmp_path / "a.wav"), "--to", "mp3"], emit=emit, ffmpeg_finder=lambda: None
    )
    assert code == 2
    assert any("FFmpeg" in line for line in lines)


def test_run_cli_no_inputs_is_setup_error() -> None:
    lines, emit = _emit()
    code = cli.run_cli(["--to", "mp3"], emit=emit, ffmpeg_finder=lambda: "ffmpeg")
    assert code == 2
    assert any("Nothing to convert" in line for line in lines)


def test_run_cli_dry_run_plans_without_running(tmp_path: Path) -> None:
    src = tmp_path / "a.wav"
    src.write_bytes(b"")
    lines, emit = _emit()
    code = cli.run_cli(
        [str(src), "--to", "mp3", "--out", str(tmp_path / "out"), "--dry-run"],
        emit=emit,
        ffmpeg_finder=lambda: "ffmpeg",
    )
    assert code == 0
    assert any("Would convert 1 file" in line for line in lines)
    assert any("a.wav" in line and "->" in line for line in lines)


def test_run_cli_runs_batch_with_injected_runner(tmp_path: Path) -> None:
    src = tmp_path / "a.wav"
    src.write_bytes(b"")
    lines, emit = _emit()

    def fake_runner(ffmpeg: str, job: object) -> JobResult:
        return JobResult(job=job, ok=True)  # type: ignore[arg-type]

    code = cli.run_cli(
        [str(src), "--to", "mp3", "--out", str(tmp_path / "out")],
        emit=emit,
        ffmpeg_finder=lambda: "ffmpeg",
        single_runner=fake_runner,
    )
    assert code == 0
    assert any("Converted 1 of 1" in line for line in lines)


def test_run_cli_reports_failure_exit_code(tmp_path: Path) -> None:
    src = tmp_path / "a.wav"
    src.write_bytes(b"")
    lines, emit = _emit()

    def failing_runner(ffmpeg: str, job: object) -> JobResult:
        return JobResult(job=job, ok=False, error="boom")  # type: ignore[arg-type]

    code = cli.run_cli(
        [str(src), "--to", "mp3", "--out", str(tmp_path / "out")],
        emit=emit,
        ffmpeg_finder=lambda: "ffmpeg",
        single_runner=failing_runner,
    )
    assert code == 1
    assert any("failed" in line for line in lines)


def test_on_existing_default_is_rename() -> None:
    ns = cli.build_parser().parse_args(["--to", "mp3"])
    assert OnExisting(ns.on_existing) is OnExisting.RENAME
