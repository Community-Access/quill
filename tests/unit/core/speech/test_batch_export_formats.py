"""Headless tests for batch output format / skip-existing / .txt (§4.1).

A fake synthesizer (monkeypatched over ``_synthesize_one``) writes a tiny WAV, so
the discovery -> extract -> output-path -> skip/format wiring is exercised with no
TTS engine. The MP3 path is checked for its graceful WAV fallback when ffmpeg is
absent.
"""

from __future__ import annotations

import threading
import wave
from pathlib import Path

import pytest

from quill.core.speech import batch_export
from quill.core.speech.batch_export import (
    SUPPORTED_EXTENSIONS,
    BatchExportOptions,
    BatchFileResult,
    _output_path_for,
    discover_files,
    run_batch_export,
)


def _fake_synth(text: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00" * 2205)  # 50 ms


@pytest.fixture
def fake_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_export, "_synthesize_one", lambda text, out, opts: _fake_synth(text, out)
    )


def _run(opts: BatchExportOptions, files: list[Path]) -> list[BatchFileResult]:
    results = [BatchFileResult(source_path=f) for f in files]
    run_batch_export(opts, results, lambda d, t, r: None, threading.Event())
    return results


def test_txt_is_supported() -> None:
    assert ".txt" in SUPPORTED_EXTENSIONS


def test_output_path_uses_format() -> None:
    src = Path("/root/sub/a.docx")
    assert _output_path_for(src, Path("/root"), Path("/out"), "wav").name == "a.wav"
    assert _output_path_for(src, Path("/root"), Path("/out"), "mp3").name == "a.mp3"


def test_txt_file_converts(tmp_path: Path, fake_engine: None) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "note.txt").write_text("Hello there, this is plain text.", encoding="utf-8")
    files = discover_files(src, [".txt"], recursive=False)
    assert len(files) == 1
    results = _run(BatchExportOptions(source_folder=src, output_folder=tmp_path / "out"), files)
    assert results[0].status == "done"
    assert results[0].output_path is not None and results[0].output_path.suffix == ".wav"


def test_skip_existing_skips_already_present(tmp_path: Path, fake_engine: None) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("alpha", encoding="utf-8")
    out = tmp_path / "out"
    opts = BatchExportOptions(source_folder=src, output_folder=out, skip_existing=True)
    files = discover_files(src, [".txt"], recursive=False)

    first = _run(opts, files)
    assert first[0].status == "done"
    # second run: output now exists, so it is skipped
    second = _run(opts, files)
    assert second[0].status == "skipped"
    assert second[0].error == "Already exported"


def test_mp3_without_ffmpeg_falls_back_to_wav(
    tmp_path: Path, fake_engine: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.speech.ffmpeg as ffmpeg

    monkeypatch.setattr(ffmpeg, "find_ffmpeg", lambda: None)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("text to speak", encoding="utf-8")
    files = discover_files(src, [".txt"], recursive=False)
    results = _run(
        BatchExportOptions(source_folder=src, output_folder=tmp_path / "o", output_format="mp3"),
        files,
    )
    assert results[0].status == "done"
    assert results[0].output_path is not None
    assert results[0].output_path.suffix == ".wav"  # fell back
    assert "ffmpeg" in (results[0].error or "")


def test_empty_text_is_skipped(tmp_path: Path, fake_engine: None) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "blank.txt").write_text("   \n  ", encoding="utf-8")
    files = discover_files(src, [".txt"], recursive=False)
    results = _run(BatchExportOptions(source_folder=src, output_folder=tmp_path / "o"), files)
    assert results[0].status == "skipped"
    assert results[0].error == "No speakable text"
