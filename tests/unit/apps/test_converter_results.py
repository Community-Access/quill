"""Quill Converter: a batch ends with the actual result, said once and kept (FUX-04)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.apps import converter_results as results
from quill.core import activity
from quill.core.audio.convert import BatchResult, ConversionJob, ConversionSpec, JobResult


def _job(source: Path, dest: Path) -> ConversionJob:
    return ConversionJob(source, dest, ConversionSpec(fmt="mp3"))


@pytest.fixture()
def music(tmp_path: Path) -> Path:
    return tmp_path / "Music"


def _batch(music: Path, *states: str, cancelled: bool = False) -> BatchResult:
    out = music / "Converted"
    items = []
    for index, state in enumerate(states):
        job = _job(music / f"song{index}.wav", out / f"song{index}.mp3")
        if state == "ok":
            items.append(JobResult(job=job, ok=True))
        elif state == "failed":
            items.append(JobResult(job=job, ok=False, error="bad header"))
        else:
            items.append(JobResult(job=job, ok=False, skipped=True))
    return BatchResult(results=items, cancelled=cancelled)


def test_a_whole_batch_names_the_folder_it_went_into(music: Path) -> None:
    said = results.batch_sentence(_batch(music, "ok", "ok", "ok"), 3, music / "Converted")
    assert said == "Converted all 3 files into the folder Converted in Music."


def test_one_file_names_the_file_it_made(music: Path) -> None:
    said = results.batch_sentence(_batch(music, "ok"), 1, music / "Converted")
    assert said == "Converted song0.wav to song0.mp3 in Converted."


def test_failures_are_named_with_retry_and_the_report(music: Path) -> None:
    said = results.batch_sentence(
        _batch(music, "ok", "failed", "ok"), 3, music / "Converted", activity_key="Shift+F9"
    )
    assert said == (
        "Converted 2 of 3 files into the folder Converted in Music. 1 failed: song1.wav. "
        "Retry in Activity (Shift+F9) converts only the 1 file left. "
        "Press Ctrl+R for the report."
    )


def test_a_stop_says_what_exists_what_does_not_and_how_to_resume(music: Path) -> None:
    said = results.batch_sentence(
        _batch(music, "ok", "ok", "stopped", "stopped", cancelled=True),
        4,
        music / "Converted",
    )
    assert said == (
        "Stopped. Converted 2 of 4 files into the folder Converted in Music; they are kept. "
        "2 files were not converted, and nothing half-finished was left behind. "
        "Retry in Activity converts only the 2 files left."
    )
    assert "cancelled" not in said  # the old ". cancelled." ending is gone


def test_a_stop_before_anything_finished(music: Path) -> None:
    said = results.batch_sentence(_batch(music, "stopped", cancelled=True), 1, music / "out")
    assert said.startswith("Stopped. No file was converted. 1 file was not converted")


def test_failed_files_with_the_same_name_say_which_folder(tmp_path: Path) -> None:
    one = _job(tmp_path / "Disc 1" / "track01.wav", tmp_path / "out" / "Disc 1" / "track01.mp3")
    two = _job(tmp_path / "Disc 2" / "track01.wav", tmp_path / "out" / "Disc 2" / "track01.mp3")
    batch = BatchResult(
        results=[JobResult(job=one, ok=False, error="x"), JobResult(job=two, ok=False, error="x")]
    )
    said = results.batch_sentence(batch, 2, tmp_path / "out")
    assert "2 failed: track01.wav in Disc 1, track01.wav in Disc 2." in said
    assert said.startswith("None of the 2 files was converted.")


def test_left_over_is_only_what_did_not_produce_a_file(music: Path) -> None:
    batch = _batch(music, "ok", "failed", "stopped", cancelled=True)
    assert [job.source.name for job in results.left_over(batch)] == ["song1.wav", "song2.wav"]


def test_keep_batch_offers_retry_and_open_folder_in_activity(music: Path) -> None:
    from quill.ui.activity_window import can_run, run_action

    batch = _batch(music, "ok", "failed")
    asked: list[str] = []
    kept = results.keep_batch(
        "said",
        batch,
        music / "Converted",
        retry=lambda: asked.append("retry") or "Converting the 1 file left.",
        open_folder=lambda: "Opened Converted.",
    )
    assert activity.LOG.recent()[0] is kept
    assert kept.outcome == activity.PARTIAL
    assert [a.id for a in kept.next_actions] == ["retry", "open_folder"]
    assert can_run(kept, "retry") and can_run(kept, "open_folder")
    assert run_action(kept, "retry") == "Converting the 1 file left."
    assert asked == ["retry"]


def test_a_clean_batch_offers_no_retry(music: Path) -> None:
    kept = results.keep_batch(
        "said",
        _batch(music, "ok"),
        music / "Converted",
        retry=lambda: "x",
        open_folder=lambda: "y",
    )
    assert kept.outcome == activity.COMPLETED
    assert [a.id for a in kept.next_actions] == ["open_folder"]


def test_outcomes(music: Path) -> None:
    assert results.outcome_of(_batch(music, "failed")) == activity.FAILED
    assert results.outcome_of(_batch(music, "stopped", cancelled=True)) == activity.CANCELLED
    assert results.outcome_of(_batch(music, "ok", "stopped", cancelled=True)) == activity.PARTIAL
