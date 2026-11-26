from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.windows_dictation.file_queue import (
    DONE,
    TRANSCRIBING,
    TranscriptionJob,
    TranscriptionQueue,
)
from quill.ui import transcription_queue_repository
from quill.ui import transcription_queue_runtime as runtime


class _Host:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def _dictation_data_dir(self) -> Path:
        return self.data_dir

    def _dictation_app_name(self) -> str:
        return "QUILL"

    def _dictation_status(self, _text: str) -> None:
        return None


def test_a_second_app_does_not_recover_a_live_runners_job(tmp_path: Path) -> None:
    transcription_queue_repository._REPOSITORIES.clear()
    owner = TranscriptionQueue(tmp_path)
    job = TranscriptionJob(app="QUILL", source_path=str(tmp_path / "one.mp3"))
    owner.add([job])
    assert owner.try_acquire("QUILL")
    assert owner.claim_next() is not None

    assert runtime.resume(_Host(tmp_path)) == 0

    stored = owner.get(job.id)
    assert stored is not None and stored.state == TRANSCRIBING


def test_a_waiting_app_retries_when_the_other_runner_releases(tmp_path: Path, monkeypatch) -> None:
    from quill.ui import transcription_queue_poll as poll

    callbacks: list = []

    class _Timer:
        stopped = False

        def Stop(self) -> None:  # noqa: N802 - wx shape
            self.stopped = True

    def later(_delay: int, callback) -> _Timer:
        callbacks.append(callback)
        return _Timer()

    monkeypatch.setattr(poll.wx, "GetApp", lambda: object())
    monkeypatch.setattr(poll.wx, "CallLater", later)
    host = _Host(tmp_path)
    resumed: list[_Host] = []
    poll.after_lock(host, tmp_path / "runner", lambda owner: resumed.append(owner) or 0)
    poll.after_lock(host, tmp_path / "runner", lambda _owner: 0)
    assert len(callbacks) == 1
    callbacks[0]()
    assert resumed == [host]


def test_resume_does_not_requeue_work_this_process_is_running(tmp_path: Path, monkeypatch) -> None:
    from quill.ui import windows_dictation_transcribe

    transcription_queue_repository._REPOSITORIES.clear()
    host = _Host(tmp_path)
    repository = runtime.repository_for(host)
    job = repository.add([
        TranscriptionJob(app="QUILL", source_path=str(tmp_path / "running.mp3"))
    ])[0]
    assert repository.try_acquire("QUILL")
    claimed = repository.claim_next()
    assert claimed is not None
    current = runtime.Entry(claimed.file_job(), host, queue_job=claimed)
    monkeypatch.setattr(
        windows_dictation_transcribe,
        "_QUEUE",
        runtime.RuntimeQueue(current=current),
    )

    assert runtime.resume(host) == 0

    stored = repository.get(job.id)
    assert stored is not None and stored.state == TRANSCRIBING


def test_lite_queue_entries_belong_to_the_app_not_a_document(tmp_path: Path) -> None:
    from quill.ui.transcription_queue_host import durable_host

    said: list[str] = []
    document = SimpleNamespace(_dictation_say=said.append)
    app = SimpleNamespace(
        data_dir=tmp_path,
        frames=[document],
        voice=SimpleNamespace(speak=said.append),
        active_frame=document,
    )
    host = durable_host(SimpleNamespace(app=app))
    host._dictation_say("Queued")

    assert durable_host(SimpleNamespace(app=app)) is host
    assert said == ["Queued"]


def test_a_completed_job_does_not_get_requeued_when_its_host_closes(
    tmp_path: Path, monkeypatch
) -> None:
    from quill.ui import windows_dictation_transcribe

    transcription_queue_repository._REPOSITORIES.clear()
    host = _Host(tmp_path)
    repository = runtime.repository_for(host)
    job = repository.add([
        runtime.stored_job(
            SimpleNamespace(
                path=tmp_path / "done.mp3",
                model="moonshine",
                language="en",
                timestamps=False,
                obey_commands=False,
                remove_fillers=False,
                dash="em",
                translate=False,
                keywords=(),
            ),
            host,
            batch="",
            cloud_approved=False,
        )
    ])[0]
    claimed = repository.claim_next()
    assert claimed is not None
    entry = runtime.Entry(claimed.file_job(), host, queue_job=claimed, suspended=True)
    monkeypatch.setattr(
        windows_dictation_transcribe,
        "_QUEUE",
        runtime.RuntimeQueue(current=entry),
    )

    runtime._finish(entry, runtime.Result(output_id="abc", output_path="saved.txt"), None)

    stored = repository.get(job.id)
    assert stored is not None
    assert stored.state == DONE
    assert (stored.output_id, stored.output_path) == ("abc", "saved.txt")
