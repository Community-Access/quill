"""Batch export applies pronunciation dictionaries as a silent text transform.

Batch writes audio files to disk and never reads aloud; here we monkeypatch the
synthesis call so no engine runs, and assert the *text* handed to synthesis was
corrected and the per-file substitution count recorded (§4.7.4, §4.7.10).
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from quill.core.speech import batch_export
from quill.core.speech.batch_export import (
    BatchExportOptions,
    BatchFileResult,
    run_batch_export,
)
from quill.core.speech.pronunciation import PronunciationDictionary, PronunciationEntry


def _options(src: Path, out: Path, **kw: object) -> BatchExportOptions:
    return BatchExportOptions(source_folder=src, output_folder=out, **kw)  # type: ignore[arg-type]


def test_pronunciations_corrected_before_synthesis_silently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "doc.md").write_text("I love QUILL.", encoding="utf-8")
    out = tmp_path / "out"

    seen: list[str] = []
    monkeypatch.setattr(
        batch_export,
        "_synthesize_one",
        lambda text, output_path, opts: seen.append(text),
    )

    dictionary = PronunciationDictionary(
        id="d", entries=[PronunciationEntry(term="QUILL", replacement="kwill")]
    )
    options = _options(src, out, pronunciation_dictionaries=[dictionary])
    results = [BatchFileResult(source_path=src / "doc.md")]

    run_batch_export(options, results, lambda *_: None, threading.Event())

    assert seen and "kwill" in seen[0]  # the corrected text reached synthesis
    assert "QUILL" not in seen[0]
    assert results[0].status == "done"
    assert results[0].pronunciation_applied == 1


def test_no_dictionaries_leaves_text_untouched(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "doc.md").write_text("Plain QUILL text.", encoding="utf-8")
    out = tmp_path / "out"

    seen: list[str] = []
    monkeypatch.setattr(
        batch_export,
        "_synthesize_one",
        lambda text, output_path, opts: seen.append(text),
    )

    options = _options(src, out)  # no pronunciation_dictionaries
    results = [BatchFileResult(source_path=src / "doc.md")]
    run_batch_export(options, results, lambda *_: None, threading.Event())

    assert seen and "QUILL" in seen[0]
    assert results[0].pronunciation_applied == 0


def test_normalization_cleans_text_before_synthesis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from quill.core.speech.text_normalize import TextNormalizationOptions

    src = tmp_path / "src"
    src.mkdir()
    (src / "doc.md").write_text("“Smart” quotes—and 50%.", encoding="utf-8")
    out = tmp_path / "out"

    seen: list[str] = []
    monkeypatch.setattr(
        batch_export,
        "_synthesize_one",
        lambda text, output_path, opts: seen.append(text),
    )

    options = _options(src, out, normalization=TextNormalizationOptions())
    results = [BatchFileResult(source_path=src / "doc.md")]
    run_batch_export(options, results, lambda *_: None, threading.Event())

    assert seen
    assert "“" not in seen[0] and "”" not in seen[0]  # curly quotes normalized
    assert "—" not in seen[0]  # em-dash handled
    assert "percent" in seen[0]  # 50% spoken
