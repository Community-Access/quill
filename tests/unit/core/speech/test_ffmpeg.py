from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from quill.core.speech import ffmpeg


def test_resolve_export_format_named_filter_normalizes_suffix() -> None:
    # User left the typed name extensionless and picked the MP3 filter (index 1):
    # choose mp3 and signal the suffix should be normalized.
    exts = ["wav", "mp3", "m4a", "ogg", "opus", "flac"]
    fmt, normalize = ffmpeg.resolve_export_format("", 1, exts)
    assert (fmt, normalize) == ("mp3", True)


def test_resolve_export_format_typed_extension_wins_and_keeps_name() -> None:
    # "song.mp3" typed under the "All files" filter (trailing index) still makes
    # an MP3, and the user's name is preserved (no normalization).
    exts = ["wav", "mp3", "flac"]
    fmt, normalize = ffmpeg.resolve_export_format(".mp3", len(exts), exts)
    assert (fmt, normalize) == ("mp3", False)


def test_resolve_export_format_unknown_under_all_files_falls_back_to_wav() -> None:
    exts = ["wav", "mp3"]
    # Unknown extension under "All files" -> wav, normalize on.
    assert ffmpeg.resolve_export_format(".xyz", len(exts), exts) == ("wav", True)
    # Already .wav under "All files" -> wav, no normalization needed.
    assert ffmpeg.resolve_export_format(".wav", len(exts), exts) == ("wav", False)


def test_resolve_export_format_wav_filter_selected() -> None:
    # Selecting the WAV filter (index 0) with no typed extension stays wav.
    exts = ["wav", "mp3"]
    assert ffmpeg.resolve_export_format("", 0, exts) == ("wav", True)


def test_build_transcode_command_targets_16k_mono_wav() -> None:
    args = ffmpeg.build_transcode_command("ffmpeg", Path("in.mp3"), Path("out.wav"))
    assert args[0] == "ffmpeg"
    assert "-i" in args and "in.mp3" in args
    # 16 kHz mono PCM, no video, overwrite.
    assert args[args.index("-ar") + 1] == "16000"
    assert args[args.index("-ac") + 1] == "1"
    assert args[args.index("-acodec") + 1] == "pcm_s16le"
    assert "-vn" in args
    assert args[-1] == "out.wav"


def test_resolve_rejects_disallowed_basename(monkeypatch) -> None:
    # A which() hit whose basename is not on the allowlist must be rejected.
    monkeypatch.setattr(ffmpeg, "ffmpeg_search_dirs", lambda: [])
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: "/usr/bin/eviltool")
    assert ffmpeg._resolve_tool("ffmpeg", ffmpeg._ALLOWED_FFMPEG) is None


def test_resolve_accepts_path_ffmpeg(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ffmpeg, "ffmpeg_search_dirs", lambda: [])
    fake = tmp_path / "ffmpeg"
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: str(fake))
    assert ffmpeg._resolve_tool("ffmpeg", ffmpeg._ALLOWED_FFMPEG) == str(fake)


def test_resolve_prefers_managed_dir(monkeypatch, tmp_path) -> None:
    managed = tmp_path / "tools" / "ffmpeg"
    managed.mkdir(parents=True)
    exe = managed / ("ffmpeg.exe" if ffmpeg.os.name == "nt" else "ffmpeg")
    exe.write_text("")
    monkeypatch.setattr(ffmpeg, "ffmpeg_search_dirs", lambda: [managed])
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: "/should/not/be/used")
    assert ffmpeg._resolve_tool("ffmpeg", ffmpeg._ALLOWED_FFMPEG) == str(exe)


def test_transcode_raises_when_ffmpeg_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ffmpeg, "find_ffmpeg", lambda: None)
    src = tmp_path / "a.mp3"
    src.write_text("x")
    with pytest.raises(ffmpeg.TranscodeError) as exc:
        ffmpeg.transcode_to_wav(src, out_dir=tmp_path)
    assert "ffmpeg is not installed" in str(exc.value)


def test_transcode_surfaces_ffmpeg_failure(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ffmpeg, "find_ffmpeg", lambda: "ffmpeg")
    src = tmp_path / "a.mp3"
    src.write_text("x")

    def _fake_run(args, *, timeout_seconds, cwd=None):
        return subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr("quill.stability.safe_subprocess.run_subprocess_safely", _fake_run)
    with pytest.raises(ffmpeg.TranscodeError) as exc:
        ffmpeg.transcode_to_wav(src, out_dir=tmp_path)
    assert "could not convert" in str(exc.value).lower()


def test_transcode_success_returns_wav(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ffmpeg, "find_ffmpeg", lambda: "ffmpeg")
    src = tmp_path / "a.mp3"
    src.write_text("x")
    out_dir = tmp_path / "out"

    def _fake_run(args, *, timeout_seconds, cwd=None):
        # Simulate ffmpeg writing the output file (last argv element).
        Path(args[-1]).write_text("RIFF")
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("quill.stability.safe_subprocess.run_subprocess_safely", _fake_run)
    result = ffmpeg.transcode_to_wav(src, out_dir=out_dir)
    assert result.is_file()
    assert result.suffix == ".wav"
