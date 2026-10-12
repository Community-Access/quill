from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.ui import undo_file_jobs, undo_last_ui


class Manager:
    def __init__(self) -> None:
        self.queue: list[tuple[Any, dict[str, Any]]] = []

    def submit(self, _name: str, work: Any, **options: Any) -> None:
        self.queue.append((work, options))

    def run_next(self) -> None:
        work, options = self.queue.pop(0)
        try:
            result = work()
        except Exception as error:
            options["on_failure"]("work", error)
        else:
            options["on_success"]("work", result)

    def drain(self) -> None:
        while self.queue:
            self.run_next()


@pytest.fixture
def runner(tmp_path: Path):
    manager = Manager()
    said: list[str] = []
    owner = SimpleNamespace(_announce=said.append)
    undo_last_ui.activate(tmp_path, task_manager=manager, owner=owner)
    manager.drain()
    try:
        yield manager, owner, said
    finally:
        manager.drain()
        undo_last_ui.deactivate(owner)


def test_holding_files_does_no_filesystem_work_in_the_submitter(runner, tmp_path: Path) -> None:
    manager, owner, _said = runner
    source = tmp_path / "episode.mp3"
    source.write_bytes(b"audio")
    held = undo_last_ui.hold_or_delete([source])
    assert source.exists()
    assert held == {}
    assert undo_file_jobs.pending_for(owner) == 1
    manager.drain()
    assert not source.exists()
    assert len(held) == 1
    assert undo_file_jobs.pending_for(owner) == 0


def test_undo_during_hold_waits_for_a_durable_recovery_record(runner, tmp_path: Path) -> None:
    from quill.core.undo_recovery import MARKER

    manager, owner, said = runner
    source = tmp_path / "episode.mp3"
    source.write_bytes(b"audio")
    held = undo_last_ui.hold_or_delete([source])
    metadata: list[str] = []

    def undo() -> None:
        assert (next(iter(held)).parent / MARKER).exists()
        metadata.append("restored")
        undo_last_ui.restore(held)

    undo_last_ui.remember("Unfollow", "Show", "1 episode and 1 download", undo, files=held)
    action = undo_last_ui.slot().take()
    undo_file_jobs.execute_undo(action, said.append)
    assert metadata == []
    assert not any(message.startswith("Undid") for message in said)
    manager.run_next()
    assert metadata == []
    manager.run_next()
    assert metadata == ["restored"]
    assert not any(message.startswith("Undid") for message in said)
    manager.drain()
    assert source.read_bytes() == b"audio"
    assert said[-1].startswith("Undid Unfollow.")
    assert undo_file_jobs.pending_for(owner) == 0


def test_history_eviction_during_hold_disposes_after_the_hold_finishes(
    runner, tmp_path: Path
) -> None:
    manager, owner, _said = runner
    source = tmp_path / "episode.mp3"
    source.write_bytes(b"audio")
    held = undo_last_ui.hold_or_delete([source])
    undo_last_ui.discard(held)
    assert source.exists()
    manager.drain()
    assert not source.exists()
    assert all(not target.exists() for target in held)
    assert undo_file_jobs.pending_for(owner) == 0


def test_retention_capture_keeps_the_same_mapping_until_completion(runner, tmp_path: Path) -> None:
    from quill.core.podcasts import retention

    manager, _owner, _said = runner
    source = tmp_path / "episode.mp3"
    source.write_bytes(b"audio")
    with undo_last_ui.capturing_deletes() as held:
        retention._delete_file(str(source))
    assert source.exists()
    manager.drain()
    assert len(held) == 1
    undo_last_ui.restore(held)
    manager.drain()
    assert source.read_bytes() == b"audio"


def test_failed_preparation_keeps_the_action_available_to_retry(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager, owner, said = runner
    source = tmp_path / "episode.mp3"
    source.write_bytes(b"audio")
    held = undo_last_ui.hold_or_delete([source])
    manager.drain()
    metadata: list[str] = []
    undo_last_ui.remember(
        "Unfollow", "Show", "1 episode", lambda: metadata.append("restored"), files=held
    )
    history = undo_last_ui.slot()
    original = history.peek()

    def fail_prepare(_held) -> None:
        raise OSError("Recovery storage is unavailable")

    monkeypatch.setattr(undo_file_jobs, "prepare_restore", fail_prepare)
    host = SimpleNamespace(_announce=said.append)
    undo_last_ui.UndoLastMixin.undo_last_action(host)
    manager.drain()
    assert metadata == []
    assert history.peek() is original
    assert undo_file_jobs.pending_for(owner) == 0
    assert "still available to retry" in said[-1]


def test_missing_files_cannot_produce_a_successful_download_count(runner, tmp_path: Path) -> None:
    manager, _owner, said = runner
    held = undo_last_ui.hold_or_delete([tmp_path / "missing.mp3"])
    undo_last_ui.remember(
        "Unfollow", "Show", "1 download", lambda: undo_last_ui.restore(held), files=held
    )
    host = SimpleNamespace(_announce=said.append)
    undo_last_ui.UndoLastMixin.undo_last_action(host)
    manager.drain()
    assert "some files could not be restored" in said[-1]
    assert not any("Brought back" in message for message in said)


def test_destroying_an_old_owner_cannot_clear_a_new_owners_undo(runner, tmp_path: Path) -> None:
    _manager, old_owner, _said = runner
    manager = Manager()
    new_owner = SimpleNamespace(_announce=lambda _message: None)
    undo_last_ui.activate(tmp_path, task_manager=manager, owner=new_owner)
    manager.drain()
    undo_last_ui.deactivate(old_owner)
    assert undo_last_ui.is_active()
    assert undo_file_jobs.jobs().owner is new_owner
    undo_last_ui.deactivate(new_owner)
    assert not undo_last_ui.is_active()
    assert undo_file_jobs.jobs() is None


def test_failed_retention_holding_repairs_the_download_path(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.podcasts import retention
    from quill.core.podcasts.models import PodcastEpisode

    manager, owner, _said = runner
    saved: list[bool] = []
    owner._save_podcast_library = lambda: saved.append(True)
    source = tmp_path / "kept.mp3"
    source.write_bytes(b"audio")
    episode = PodcastEpisode(
        guid="kept",
        title="Kept",
        audio_url="https://x.invalid/audio",
        downloaded_path=str(source),
    )

    def cannot_hold(paths, _directory, *, on_error):
        for path in paths:
            on_error(path, PermissionError("File is in use"))
        return {}

    monkeypatch.setattr(undo_file_jobs, "hold_files", cannot_hold)
    with undo_last_ui.capturing_deletes():
        assert retention.remove_downloaded_copy(episode)
    assert episode.downloaded_path == ""
    manager.drain()
    assert episode.downloaded_path == str(source)
    assert source.exists()
    assert saved == [True]


def test_missing_restore_clears_the_stale_download_metadata(runner, tmp_path: Path) -> None:
    from quill.core.podcasts.models import PodcastEpisode

    manager, _owner, said = runner
    source = tmp_path / "missing.mp3"
    episode = PodcastEpisode(
        guid="missing",
        title="Missing",
        audio_url="https://x.invalid/audio",
        downloaded_path=str(source),
    )
    held = undo_last_ui.hold_or_delete([source], downloads=[episode])

    def undo() -> None:
        episode.downloaded_path = str(source)
        undo_last_ui.restore(held)

    undo_last_ui.remember("Remove Download", "Missing", "1 download", undo, files=held)
    undo_last_ui.UndoLastMixin.undo_last_action(SimpleNamespace(_announce=said.append))
    manager.drain()
    assert episode.downloaded_path == ""
    assert "some files could not be restored" in said[-1]


def test_problem_record_failure_cannot_lose_files_already_held(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core import problem_log

    manager, owner, _said = runner
    source = tmp_path / "available.mp3"
    source.write_bytes(b"audio")

    def cannot_record(*_args, **_kwargs):
        raise OSError("Problem storage is unavailable")

    monkeypatch.setattr(problem_log, "record_problem", cannot_record)
    held = undo_last_ui.hold_or_delete([source, tmp_path / "missing.mp3"])
    manager.drain()
    assert len(held) == 1
    assert next(iter(held)).read_bytes() == b"audio"
    assert undo_file_jobs.pending_for(owner) == 0


def test_metadata_save_failure_cannot_strand_a_pending_undo(runner, tmp_path: Path) -> None:
    from quill.core.podcasts.models import PodcastEpisode

    manager, owner, said = runner
    source = tmp_path / "unavailable.mp3"
    episode = PodcastEpisode(
        guid="missing",
        title="Missing",
        audio_url="https://x.invalid/audio",
        downloaded_path=str(source),
    )

    def cannot_save() -> None:
        raise OSError("Library storage is unavailable")

    owner._save_podcast_library = cannot_save
    held = undo_last_ui.hold_or_delete([source], downloads=[episode])

    def undo() -> None:
        episode.downloaded_path = str(source)
        undo_last_ui.restore(held)

    undo_last_ui.remember("Remove Download", "Missing", "1 download", undo, files=held)
    undo_last_ui.UndoLastMixin.undo_last_action(SimpleNamespace(_announce=said.append))
    manager.drain()

    assert undo_file_jobs.pending_for(owner) == 0
    assert episode.downloaded_path == ""
    assert "did not complete" in said[-1]


def test_restore_exception_checks_missing_paths_and_keeps_recovery_copies(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.podcasts.models import PodcastEpisode

    manager, owner, said = runner
    source = tmp_path / "episode.mp3"
    source.write_bytes(b"audio")
    episode = PodcastEpisode(
        guid="episode",
        title="Episode",
        audio_url="https://x.invalid/audio",
        downloaded_path=str(source),
    )
    held = undo_last_ui.hold_or_delete([source], downloads=[episode])
    manager.drain()
    target = next(iter(held))

    def cannot_restore(_mapping):
        raise OSError("Destination storage is unavailable")

    monkeypatch.setattr(undo_file_jobs, "restore_files", cannot_restore)
    undo_last_ui.remember(
        "Remove Download", "Episode", "1 download", lambda: undo_last_ui.restore(held), files=held
    )
    undo_last_ui.UndoLastMixin.undo_last_action(SimpleNamespace(_announce=said.append))
    manager.drain()

    assert target.read_bytes() == b"audio"
    assert episode.downloaded_path == ""
    assert undo_file_jobs.pending_for(owner) == 0
    assert "some files could not be restored" in said[-1]


def test_diagnostic_submission_cannot_replace_the_original_undo_error(
    runner, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manager, owner, said = runner

    def cannot_submit(*_args, **_kwargs):
        raise RuntimeError("Task manager is closing")

    monkeypatch.setattr(undo_file_jobs.jobs(), "submit", cannot_submit)

    def cannot_undo() -> None:
        raise ValueError("The podcast is already followed")

    undo_last_ui.remember("Unfollow", "Show", "1 podcast", cannot_undo)
    undo_last_ui.UndoLastMixin.undo_last_action(SimpleNamespace(_announce=said.append))

    assert any("already followed" in message for message in said)
    assert "problem could not be recorded" in said[-1]
    assert undo_file_jobs.pending_for(owner) == 0
