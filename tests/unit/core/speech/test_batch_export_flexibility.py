"""Headless tests for the batch-export flexibility knobs.

Covers discovery filters, output naming (flatten/template), the existing-file
policy, retry / stop-on-error, parallel worker clamping, the run manifest, and
the ffmpeg encode-command builders. A fake synthesizer (monkeypatched over
``_synthesize_one``) writes a tiny WAV so no real TTS engine is needed.
"""

from __future__ import annotations

import json
import threading
import wave
from pathlib import Path

import pytest

from quill.core.speech import batch_export
from quill.core.speech.batch_export import (
    BatchExportOptions,
    BatchFileResult,
    _effective_workers,
    _file_metadata,
    _output_path_for,
    _unique_path,
    discover_files,
    run_batch_export,
)
from quill.core.speech.ffmpeg import (
    AudioMetadata,
    build_encode_command,
    build_wav_conform_command,
)


def _fake_synth(text: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00" * 2205)


@pytest.fixture
def fake_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_export, "_synthesize_one", lambda text, out, opts: _fake_synth(text, out)
    )


def _run(opts: BatchExportOptions, files: list[Path]) -> list[BatchFileResult]:
    results = [BatchFileResult(source_path=f) for f in files]
    run_batch_export(opts, results, lambda d, t, r: None, threading.Event())
    return results


# --------------------------------------------------------------- discovery


def _seed(src: Path, names: list[str]) -> None:
    src.mkdir(parents=True, exist_ok=True)
    for name in names:
        p = src / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("hello there", encoding="utf-8")


def test_include_glob_keeps_only_matches(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _seed(src, ["keep-a.txt", "skip-b.txt", "keep-c.txt"])
    found = discover_files(src, [".txt"], recursive=False, include_glob="keep-*")
    assert {p.name for p in found} == {"keep-a.txt", "keep-c.txt"}


def test_exclude_glob_wins_over_include(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _seed(src, ["draft.txt", "final.txt"])
    found = discover_files(src, [".txt"], recursive=False, exclude_glob="draft*")
    assert {p.name for p in found} == {"final.txt"}


def test_exclude_glob_matches_relative_path(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _seed(src, ["a.txt", "drafts/b.txt"])
    found = discover_files(src, [".txt"], recursive=True, exclude_glob="drafts/*")
    assert {p.name for p in found} == {"a.txt"}


def test_max_file_bytes_drops_large(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "small.txt").write_text("hi", encoding="utf-8")
    (src / "big.txt").write_text("x" * 5000, encoding="utf-8")
    found = discover_files(src, [".txt"], recursive=False, max_file_bytes=1000)
    assert {p.name for p in found} == {"small.txt"}


# --------------------------------------------------------------- naming


def test_flatten_collapses_tree() -> None:
    src = Path("/root/sub/deep/a.docx")
    out = _output_path_for(src, Path("/root"), Path("/out"), "wav", flatten=True)
    assert out == Path("/out/a.wav")


def test_filename_template_indexes() -> None:
    src = Path("/root/a.docx")
    out = _output_path_for(
        src, Path("/root"), Path("/out"), "mp3", filename_template="{index:03d} - {stem}", index=7
    )
    assert out.name == "007 - a.mp3"


def test_filename_template_bad_field_falls_back() -> None:
    src = Path("/root/a.docx")
    out = _output_path_for(src, Path("/root"), Path("/out"), "wav", filename_template="{nope}")
    assert out.name == "a.wav"


# --------------------------------------------------------------- existing policy


def test_unique_path_avoids_collision(tmp_path: Path) -> None:
    target = tmp_path / "a.wav"
    target.write_bytes(b"x")
    assert _unique_path(target) == tmp_path / "a (2).wav"


def test_on_existing_overwrite_replaces(tmp_path: Path, fake_engine: None) -> None:
    src = tmp_path / "src"
    _seed(src, ["a.txt"])
    out = tmp_path / "out"
    opts = BatchExportOptions(source_folder=src, output_folder=out, on_existing="overwrite")
    files = discover_files(src, [".txt"], recursive=False)
    _run(opts, files)
    second = _run(opts, files)
    assert second[0].status == "done"
    assert second[0].output_path == out / "a.wav"


def test_on_existing_rename_keeps_both(tmp_path: Path, fake_engine: None) -> None:
    src = tmp_path / "src"
    _seed(src, ["a.txt"])
    out = tmp_path / "out"
    files = discover_files(src, [".txt"], recursive=False)
    _run(BatchExportOptions(source_folder=src, output_folder=out, on_existing="overwrite"), files)
    second = _run(
        BatchExportOptions(source_folder=src, output_folder=out, on_existing="rename"), files
    )
    assert second[0].output_path == out / "a (2).wav"
    assert (out / "a.wav").exists() and (out / "a (2).wav").exists()


def test_skip_existing_alias_still_skips(tmp_path: Path, fake_engine: None) -> None:
    src = tmp_path / "src"
    _seed(src, ["a.txt"])
    out = tmp_path / "out"
    opts = BatchExportOptions(source_folder=src, output_folder=out, skip_existing=True)
    files = discover_files(src, [".txt"], recursive=False)
    _run(opts, files)
    second = _run(opts, files)
    assert second[0].status == "skipped"


# --------------------------------------------------------------- error policy


def test_retry_recovers_after_transient_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"n": 0}

    def flaky(text: str, out: Path, opts: BatchExportOptions) -> None:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("engine hiccup")
        _fake_synth(text, out)

    monkeypatch.setattr(batch_export, "_synthesize_one", flaky)
    src = tmp_path / "src"
    _seed(src, ["a.txt"])
    files = discover_files(src, [".txt"], recursive=False)
    results = _run(
        BatchExportOptions(source_folder=src, output_folder=tmp_path / "o", retry_count=2), files
    )
    assert results[0].status == "done"
    assert calls["n"] == 3


def test_stop_on_error_halts_remaining(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def always_fail(text: str, out: Path, opts: BatchExportOptions) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(batch_export, "_synthesize_one", always_fail)
    src = tmp_path / "src"
    _seed(src, ["a.txt", "b.txt"])
    files = discover_files(src, [".txt"], recursive=False)
    results = _run(
        BatchExportOptions(source_folder=src, output_folder=tmp_path / "o", stop_on_error=True),
        files,
    )
    statuses = [r.status for r in results]
    assert statuses[0] == "error"
    assert statuses[1] == "skipped"  # not attempted after the stop


# --------------------------------------------------------------- concurrency


def test_effective_workers_clamps_single_apartment() -> None:
    base = dict(source_folder=Path("."), output_folder=Path("o"))
    assert _effective_workers(BatchExportOptions(engine="sapi5", max_workers=4, **base)) == 1
    assert _effective_workers(BatchExportOptions(engine="kokoro", max_workers=4, **base)) == 1
    assert _effective_workers(BatchExportOptions(engine="piper", max_workers=4, **base)) == 4


def test_parallel_run_processes_all(tmp_path: Path, fake_engine: None) -> None:
    src = tmp_path / "src"
    _seed(src, [f"f{i}.txt" for i in range(6)])
    files = discover_files(src, [".txt"], recursive=False)
    results = _run(
        BatchExportOptions(
            source_folder=src, output_folder=tmp_path / "o", engine="piper", max_workers=3
        ),
        files,
    )
    assert all(r.status == "done" for r in results)
    assert len(results) == 6


# --------------------------------------------------------------- manifest


def test_manifest_written(tmp_path: Path, fake_engine: None) -> None:
    src = tmp_path / "src"
    _seed(src, ["a.txt", "b.txt"])
    out = tmp_path / "out"
    files = discover_files(src, [".txt"], recursive=False)
    _run(BatchExportOptions(source_folder=src, output_folder=out, write_manifest=True), files)
    manifest = out / "manifest.json"
    assert manifest.exists() and (out / "manifest.csv").exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(data["files"]) == 2
    assert {row["status"] for row in data["files"]} == {"done"}


# --------------------------------------------------------------- metadata / ffmpeg


def test_file_metadata_defaults_title_and_track() -> None:
    opts = BatchExportOptions(
        source_folder=Path("."),
        output_folder=Path("o"),
        metadata=AudioMetadata(album="My Book", artist="Jeff"),
    )
    meta = _file_metadata(opts, Path("/out/chapter-3.mp3"), index=3)
    assert meta.title == "chapter-3"  # falls back to stem
    assert meta.track == "3"  # falls back to index
    assert meta.album == "My Book" and meta.artist == "Jeff"


def test_encode_command_per_format() -> None:
    a, b = Path("a.wav"), Path("a.opus")
    cmd = build_encode_command("ffmpeg", a, b, "opus")
    assert "libopus" in cmd and "-f" not in cmd  # opus has no muxer override
    m4b = build_encode_command("ffmpeg", a, Path("a.m4b"), "m4b")
    assert "aac" in m4b and m4b[m4b.index("-f") + 1] == "ipod"


def test_encode_command_mp3_quality() -> None:
    cmd = build_encode_command("ffmpeg", Path("a.wav"), Path("a.mp3"), "mp3", mp3_vbr_quality="0")
    assert cmd[cmd.index("-q:a") + 1] == "0"


def test_transform_preview_applies_pronunciation_and_counts() -> None:
    from quill.core.speech.batch_export import transform_preview
    from quill.core.speech.pronunciation import PronunciationDictionary, PronunciationEntry

    dicts = [
        PronunciationDictionary(
            id="d", entries=[PronunciationEntry(term="QUILL", replacement="kwill")]
        )
    ]
    preview = transform_preview(
        "QUILL meets QUILL.", engine="sapi5", pronunciation_dictionaries=dicts
    )
    assert "kwill" in preview.text and "QUILL" not in preview.text
    assert preview.substitutions >= 1


def test_transform_preview_without_dicts_is_polish_only() -> None:
    from quill.core.speech.batch_export import transform_preview

    preview = transform_preview("Hello world.")
    assert preview.substitutions == 0
    assert "Hello" in preview.text


def test_wav_conform_command_sets_rate_and_channels() -> None:
    cmd = build_wav_conform_command(
        "ffmpeg", Path("a.wav"), Path("b.wav"), sample_rate=44100, channels=1
    )
    assert cmd[cmd.index("-ar") + 1] == "44100"
    assert cmd[cmd.index("-ac") + 1] == "1"


# --------------------------------------------------------------- engine knobs


def test_piper_command_appends_shaping_flags() -> None:
    from quill.core.read_aloud import build_piper_command

    cmd = build_piper_command(
        Path("piper.exe"),
        Path("m.onnx"),
        Path("o.wav"),
        length_scale=1.2,
        noise_scale=0.6,
        noise_w=0.8,
    )
    assert cmd[cmd.index("--length_scale") + 1] == "1.2"
    assert cmd[cmd.index("--noise_scale") + 1] == "0.6"
    assert cmd[cmd.index("--noise_w") + 1] == "0.8"


def test_piper_command_omits_unset_flags() -> None:
    from quill.core.read_aloud import build_piper_command

    cmd = build_piper_command(Path("piper.exe"), Path("m.onnx"), Path("o.wav"))
    assert "--length_scale" not in cmd and "--noise_scale" not in cmd


def test_profile_threads_piper_and_espeak_knobs(tmp_path: Path) -> None:
    from quill.core.speech.project_profile import (
        SpeechProjectProfile,
        SynthesizerProfile,
        to_batch_options,
    )

    piper = SpeechProjectProfile(
        synthesizer=SynthesizerProfile(
            engine="piper",
            extra={"piper_length_scale": "1.3", "piper_noise_scale": 0.5},
        )
    )
    popts = to_batch_options(piper, tmp_path / "s", tmp_path / "o")
    assert popts.piper_length_scale == 1.3
    assert popts.piper_noise_scale == 0.5
    assert popts.piper_noise_w is None

    espeak = SpeechProjectProfile(
        synthesizer=SynthesizerProfile(
            engine="espeak", extra={"espeak_pitch": "70", "espeak_word_gap_ms": 50}
        )
    )
    eopts = to_batch_options(espeak, tmp_path / "s", tmp_path / "o")
    assert eopts.espeak_pitch == 70
    assert eopts.espeak_word_gap_ms == 50
