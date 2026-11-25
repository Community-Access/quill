from __future__ import annotations

from pathlib import Path

from quill.core.windows_dictation.file_queue import (
    DONE,
    FAILED,
    QUEUED,
    STOPPED,
    TRANSCRIBING,
    TranscriptionJob,
    TranscriptionQueue,
)


def _job(tmp_path: Path, name: str = "meeting.mp3") -> TranscriptionJob:
    return TranscriptionJob(
        app="QUILL",
        source_path=str(tmp_path / name),
        model="moonshine",
        keywords=["Acme", "Quarterly Review"],
    )


def test_jobs_are_durable_without_transcript_or_secret_content(tmp_path: Path) -> None:
    queue = TranscriptionQueue(tmp_path)
    job = _job(tmp_path)
    queue.add([job])

    again = TranscriptionQueue(tmp_path).jobs()
    assert len(again) == 1
    assert again[0].source_path == job.source_path
    assert again[0].keywords == ["Acme", "Quarterly Review"]
    text = queue.path.read_text(encoding="utf-8")
    assert "transcript" not in text
    assert "api_key" not in text


def test_claims_in_order_and_recovers_an_interrupted_run(tmp_path: Path) -> None:
    clock = [100.0]
    queue = TranscriptionQueue(tmp_path, clock=lambda: clock[0])
    first, second = _job(tmp_path, "one.mp3"), _job(tmp_path, "two.mp3")
    first.created_at, second.created_at = 1.0, 2.0
    queue.add([second, first])

    claimed = queue.claim_next()
    assert claimed is not None and claimed.id == first.id
    assert claimed.state == TRANSCRIBING
    assert claimed.started_at == 100.0
    assert claimed.attempts == 1

    reopened = TranscriptionQueue(tmp_path, clock=lambda: clock[0])
    recovered = reopened.recover_interrupted()
    assert [job.id for job in recovered] == [first.id]
    assert recovered[0].state == QUEUED
    assert all(job.state in {QUEUED} for job in reopened.jobs())
    assert reopened.claim_next().id == first.id  # retry the interrupted one before newer work


def test_progress_failure_retry_and_stop_are_read_back(tmp_path: Path) -> None:
    queue = TranscriptionQueue(tmp_path)
    job = queue.add([_job(tmp_path)])[0]
    assert queue.claim_next().id == job.id
    queue.update(job.id, progress=0.42, message="Transcribing: 42 percent")
    assert queue.get(job.id).progress == 0.42
    assert (
        queue.update(
            job.id,
            state=FAILED,
            message="The model stopped",
            output_id="partial",
            output_path="partial.txt",
        )
        is not None
    )
    assert queue.retry(job.id)
    assert queue.get(job.id).state == QUEUED
    assert queue.get(job.id).output_id == queue.get(job.id).output_path == ""
    assert queue.stop(job.id, "No longer wanted")
    assert queue.get(job.id).state == STOPPED
    assert queue.retry(job.id)
    assert queue.get(job.id).state == QUEUED


def test_only_finished_jobs_can_be_removed(tmp_path: Path) -> None:
    queue = TranscriptionQueue(tmp_path)
    running = queue.add([_job(tmp_path, "run.mp3")])[0]
    assert not queue.remove(running.id)
    queue.update(running.id, state=DONE, output_id="transcript-1")
    assert queue.remove(running.id)
    assert queue.jobs() == []


def test_corrupt_rows_are_ignored_and_newer_states_are_preserved(tmp_path: Path) -> None:
    folder = tmp_path / "dictation"
    folder.mkdir()
    (folder / "transcription-queue.json").write_text(
        '{"version":1,"jobs":[{"id":null},{"id":"ok","source_path":"a.mp3",'
        '"state":"new-shape","progress":"bad"}]}',
        encoding="utf-8",
    )
    jobs = TranscriptionQueue(tmp_path).jobs()
    assert len(jobs) == 1
    assert jobs[0].state == "new-shape"
    assert jobs[0].progress == 0.0


def test_a_newer_queue_keeps_its_version_and_unknown_fields(tmp_path: Path) -> None:
    import json

    folder = tmp_path / "dictation"
    folder.mkdir()
    path = folder / "transcription-queue.json"
    path.write_text(
        json.dumps({
            "version": 2,
            "future_top": {"kept": True},
            "jobs": [
                {
                    "id": "future",
                    "source_path": "later.wav",
                    "state": "needs_model",
                    "future_job": 42,
                }
            ],
        }),
        encoding="utf-8",
    )
    queue = TranscriptionQueue(tmp_path)

    assert queue.update("future", message="Waiting for a newer QUILL") is not None

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"] == 2
    assert raw["future_top"] == {"kept": True}
    assert raw["jobs"][0]["state"] == "needs_model"
    assert raw["jobs"][0]["future_job"] == 42


def test_runner_lock_prevents_two_apps_from_claiming_work(tmp_path: Path) -> None:
    first = TranscriptionQueue(tmp_path)
    second = TranscriptionQueue(tmp_path)
    assert first.try_acquire("QUILL")
    assert not second.try_acquire("QUILL Transcribe")
    first.release()
    assert second.try_acquire("QUILL Transcribe")
