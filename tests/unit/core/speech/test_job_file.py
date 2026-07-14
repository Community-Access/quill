"""Tests for .quilljob save/load round trips."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.speech.job_file import JOB_EXTENSION, JobFileError, load_job, save_job
from quill.ui.audio_studio.request import BatchSpeechRequest


def _request(tmp_path: Path) -> BatchSpeechRequest:
    return BatchSpeechRequest(
        source_folder=tmp_path,
        recursive=True,
        extensions=(".docx", ".md"),
        engine="kokoro",
        voice="am_liam",
        rate=200,
        speed=1.2,
        output_format="m4b",
        sound_enabled=True,
        sound_volume=70,
        article_gap_ms=900,
        sentence_gap_ms=100,
        tail_padding_ms=250,
        speak_headings=False,
        skip_existing=True,
        round_robin_voices=("am_liam", "af_heart"),
        translation_targets=(("es", "espeak", "es-voice"),),
        make_book=True,
        book_title="My Book",
        book_credits=True,
        audition=True,
    )


def _defaults(tmp_path: Path) -> BatchSpeechRequest:
    return BatchSpeechRequest(
        source_folder=tmp_path / "other",
        recursive=False,
        extensions=(".txt",),
        engine="sapi5",
        voice="",
        rate=180,
        speed=1.0,
        output_format="mp3",
        sound_enabled=False,
        sound_volume=100,
        article_gap_ms=1200,
        sentence_gap_ms=0,
        tail_padding_ms=0,
        speak_headings=True,
        skip_existing=False,
    )


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    original = _request(tmp_path)
    job = save_job(tmp_path / "run", original)
    assert job.suffix == JOB_EXTENSION
    loaded = load_job(job, _defaults(tmp_path))
    assert loaded.source_folder == tmp_path
    assert loaded.engine == "kokoro"
    assert loaded.voice == "am_liam"
    assert loaded.rate == 200
    assert abs(loaded.speed - 1.2) < 1e-9
    assert loaded.extensions == (".docx", ".md")
    assert loaded.round_robin_voices == ("am_liam", "af_heart")
    assert loaded.translation_targets == (("es", "espeak", "es-voice"),)
    assert loaded.make_book is True and loaded.book_title == "My Book"
    assert loaded.book_credits is True and loaded.audition is True
    assert loaded.skip_existing is True


def test_load_tolerates_missing_and_unknown_keys(tmp_path: Path) -> None:
    job = save_job(tmp_path / "run", _request(tmp_path))
    body = json.loads(job.read_text(encoding="utf-8"))
    del body["request"]["engine"]  # missing key keeps the caller's default
    body["request"]["mystery_future_option"] = 42  # unknown keys are ignored
    job.write_text(json.dumps(body), encoding="utf-8")
    loaded = load_job(job, _defaults(tmp_path))
    assert loaded.engine == "sapi5"
    assert loaded.voice == "am_liam"


def test_load_rejects_non_job_files(tmp_path: Path) -> None:
    not_json = tmp_path / f"bad{JOB_EXTENSION}"
    not_json.write_text("not json", encoding="utf-8")
    with pytest.raises(JobFileError):
        load_job(not_json, _defaults(tmp_path))
    wrong_format = tmp_path / f"wrong{JOB_EXTENSION}"
    wrong_format.write_text(json.dumps({"format": "something-else"}), encoding="utf-8")
    with pytest.raises(JobFileError):
        load_job(wrong_format, _defaults(tmp_path))


def test_preview_and_private_fields_never_persist(tmp_path: Path) -> None:
    request = _request(tmp_path)
    request.preview = True
    job = save_job(tmp_path / "run", request)
    body = json.loads(job.read_text(encoding="utf-8"))["request"]
    assert "preview" not in body and "_voice_label" not in body
