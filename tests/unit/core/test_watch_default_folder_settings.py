"""The Watch Folders page's default folder and its three switches (question 38).

``watch_folder_path``, ``watch_folder_include_subfolders``,
``watch_folder_process_existing`` and ``watch_folder_auto_start`` were drawn in
Settings and read by nothing. Each test here flips one of them and shows that
what the watcher does changes.
"""

from __future__ import annotations

import os
import time
from dataclasses import replace
from pathlib import Path

from quill.core.settings import Settings
from quill.core.watch_default import (
    DEFAULT_WATCH_PROFILE_ID,
    default_watch_profile,
    launch_plan,
)
from quill.core.watch_service import WatchService
from quill.ui.main_frame_watch_folder import WatchFolderRuntimeMixin


def _old_file(path: Path) -> Path:
    """A settled file: older than the watcher's two-second settle age."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("hello", encoding="utf-8")
    past = time.time() - 60
    os.utime(path, (past, past))
    return path


def _settings(folder: Path, **overrides: object) -> Settings:
    base = Settings(
        watch_folder_path=str(folder),
        watch_folder_auto_start=True,
        watch_folder_poll_interval_seconds=2,
    )
    return replace(base, **overrides)


def _queued_names(service: WatchService) -> set[str]:
    return {Path(item.source_path).name for item in service.queue_items()}


def _wait(predicate, seconds: float = 6.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return bool(predicate())


def _service(tmp_path: Path, settings: Settings) -> WatchService:
    # The open action is wired to nothing so items stay visible in the queue.
    return WatchService(data_dir=tmp_path / "data", settings=settings)


# -- watch_folder_path + watch_folder_auto_start ---------------------------


def test_no_default_folder_means_no_default_watch(tmp_path: Path) -> None:
    assert default_watch_profile(Settings()) is None
    service = _service(tmp_path, Settings(watch_folder_auto_start=True))
    try:
        assert DEFAULT_WATCH_PROFILE_ID not in service.start()
    finally:
        service.stop()


def test_start_watching_automatically_decides_whether_the_default_folder_runs(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "drop"
    folder.mkdir()
    on = _service(tmp_path / "on", _settings(folder, watch_folder_auto_start=True))
    off = _service(tmp_path / "off", _settings(folder, watch_folder_auto_start=False))
    try:
        assert DEFAULT_WATCH_PROFILE_ID in on.start()
        assert DEFAULT_WATCH_PROFILE_ID not in off.start()
    finally:
        on.stop()
        off.stop()


def test_launch_plan_reads_both_switches_and_safe_mode(tmp_path: Path) -> None:
    folder = str(tmp_path)
    assert launch_plan(Settings(), safe_mode=False) == (False, False)
    assert launch_plan(
        Settings(watch_folder_path=folder, watch_folder_auto_start=True), safe_mode=False
    ) == (False, True)
    assert launch_plan(Settings(watch_folder_enabled=True), safe_mode=False) == (True, False)
    # A switch with no folder chosen has nothing to watch.
    assert launch_plan(Settings(watch_folder_auto_start=True), safe_mode=False) == (False, False)
    # Safe Mode disables the watch folder outright.
    assert launch_plan(
        Settings(watch_folder_path=folder, watch_folder_auto_start=True, watch_folder_enabled=True),
        safe_mode=True,
    ) == (False, False)


class _Host(WatchFolderRuntimeMixin):
    def __init__(self, settings: Settings, *, safe_mode: bool = False) -> None:
        self.settings = settings
        self._safe_mode = safe_mode
        self.calls: list[object] = []
        host = self

        class _Service:
            def start(self, *, profiles: bool = True) -> list[str]:
                host.calls.append(("start", profiles))
                return []

        self._watch_service = _Service()

    def _feature_enabled(self, _feature_id: str) -> bool:
        return True

    def _start_watch_folder_monitoring(self, *, announce: bool = True) -> bool:
        self.calls.append("monitoring")
        return True


def test_launch_starts_only_the_default_folder_when_only_auto_start_is_on(
    tmp_path: Path,
) -> None:
    settings = Settings(watch_folder_path=str(tmp_path), watch_folder_auto_start=True)
    host = _Host(settings)
    host._maybe_start_watch_folder()
    assert host.calls == [("start", False)]
    # Not recorded as "profiles on", which would start every profile next launch.
    assert settings.watch_folder_enabled is False

    off = _Host(Settings(watch_folder_path=str(tmp_path), watch_folder_auto_start=False))
    off._maybe_start_watch_folder()
    assert off.calls == []

    safe = _Host(settings, safe_mode=True)
    safe._maybe_start_watch_folder()
    assert safe.calls == []


def test_changing_the_switch_applies_to_a_running_watch(tmp_path: Path) -> None:
    folder = tmp_path / "drop"
    folder.mkdir()
    settings = _settings(folder, watch_folder_auto_start=False)
    service = _service(tmp_path, settings)
    try:
        service.start()
        assert DEFAULT_WATCH_PROFILE_ID not in service.manager.active_profile_ids()
        service.refresh_policy(replace(settings, watch_folder_auto_start=True))
        assert DEFAULT_WATCH_PROFILE_ID in service.manager.active_profile_ids()
    finally:
        service.stop()


# -- watch_folder_include_subfolders ---------------------------------------


def _run_until_top_level_seen(tmp_path: Path, **overrides: object) -> set[str]:
    folder = tmp_path / "drop"
    _old_file(folder / "top.txt")
    _old_file(folder / "nested" / "deep.txt")
    service = _service(tmp_path, _settings(folder, watch_folder_process_existing=True, **overrides))
    try:
        service.start(profiles=False)
        assert _wait(lambda: "top.txt" in _queued_names(service))
        return _queued_names(service)
    finally:
        service.stop()


def test_include_subfolders_on_picks_up_nested_files(tmp_path: Path) -> None:
    names = _run_until_top_level_seen(tmp_path, watch_folder_include_subfolders=True)
    assert "deep.txt" in names


def test_include_subfolders_off_ignores_nested_files(tmp_path: Path) -> None:
    names = _run_until_top_level_seen(tmp_path, watch_folder_include_subfolders=False)
    assert "deep.txt" not in names


# -- watch_folder_process_existing -----------------------------------------


def test_process_existing_on_actions_files_already_there(tmp_path: Path) -> None:
    folder = tmp_path / "drop"
    _old_file(folder / "waiting.txt")
    service = _service(tmp_path, _settings(folder, watch_folder_process_existing=True))
    try:
        service.start(profiles=False)
        assert _wait(lambda: "waiting.txt" in _queued_names(service))
        assert service.primed_count() == 0
    finally:
        service.stop()


def test_process_existing_off_leaves_files_already_there_alone(tmp_path: Path) -> None:
    folder = tmp_path / "drop"
    _old_file(folder / "waiting.txt")
    service = _service(tmp_path, _settings(folder, watch_folder_process_existing=False))
    try:
        service.start(profiles=False)
        assert _wait(lambda: service.primed_count() >= 1)
        assert "waiting.txt" not in _queued_names(service)
    finally:
        service.stop()


def test_worker_resolves_the_default_folder_rule(tmp_path: Path) -> None:
    folder = tmp_path / "drop"
    folder.mkdir()
    service = _service(tmp_path, _settings(folder))
    resolved = service._lookup_profile(DEFAULT_WATCH_PROFILE_ID)
    assert resolved is not None
    assert resolved.folder_path == str(folder)
    assert resolved.action_id == "open"
    assert resolved.include_subfolders is False
