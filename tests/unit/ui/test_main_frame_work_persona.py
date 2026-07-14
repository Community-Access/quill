"""Tests for WorkPersonaMixin (#896): applying a persona bundle."""

from __future__ import annotations

import os
from pathlib import Path

from quill.core.work_persona import WorkPersona, WorkPersonaStore
from quill.ui.main_frame_work_persona import WorkPersonaMixin


class _FakeFeatures:
    def __init__(self) -> None:
        self.active_profile_id = "essential"
        self.switched_to: list[str] = []

    def switch_profile(self, profile_id: str) -> None:
        if profile_id not in {"essential", "writer", "full_quill"}:
            raise KeyError(profile_id)
        self.active_profile_id = profile_id
        self.switched_to.append(profile_id)


class _Host(WorkPersonaMixin):
    def __init__(self, tmp_path: Path) -> None:
        self.features = _FakeFeatures()
        self.status: list[str] = []
        self.opened: list[Path] = []
        self._tmp_path = tmp_path
        self.frame = None

    def open_file(self, path: Path, **_kwargs: object) -> None:
        self.opened.append(path)

    def _announce(self, _message: str) -> None:
        pass

    def _set_status(self, message: str) -> None:
        self.status.append(message)


def test_apply_persona_switches_feature_profile(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path)
    host.apply_persona(WorkPersona(name="Work", technical_profile="writer"))
    assert host.features.active_profile_id == "writer"
    assert "feature profile" in host.status[-1]


def test_apply_persona_unknown_profile_does_not_crash(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path)
    host.apply_persona(WorkPersona(name="Bad", technical_profile="not_a_real_profile"))
    assert host.features.active_profile_id == "essential"  # unchanged
    assert host.status  # still reports something, never raises


def test_apply_persona_changes_working_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    original_cwd = os.getcwd()
    folder = tmp_path / "novel"
    folder.mkdir()
    host = _Host(tmp_path)
    try:
        host.apply_persona(WorkPersona(name="Novel", working_folder=str(folder)))
        assert os.getcwd() == str(folder)
        assert "working folder" in host.status[-1]
    finally:
        os.chdir(original_cwd)


def test_apply_persona_nonexistent_folder_is_skipped_not_crashed(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path)
    host.apply_persona(WorkPersona(name="Ghost", working_folder=str(tmp_path / "nope")))
    assert "working folder" not in host.status[-1]


def test_apply_persona_opens_existing_favorite_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    file_a = tmp_path / "a.md"
    file_a.write_text("a", encoding="utf-8")
    file_b = tmp_path / "b.md"
    file_b.write_text("b", encoding="utf-8")
    host = _Host(tmp_path)
    files = (str(file_a), str(file_b), str(tmp_path / "gone.md"))
    host.apply_persona(WorkPersona(name="Novel", favorite_files=files))
    assert len(host.opened) == 2
    assert "2 favorite files" in host.status[-1]


def test_apply_persona_empty_bundle_reports_status_without_crashing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path)
    host.apply_persona(WorkPersona(name="Empty", technical_profile="not_a_real_profile"))
    assert "empty persona" in host.status[-1]


def test_apply_persona_by_name_reports_not_found(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path)
    assert host.apply_persona_by_name("Nonexistent") is False
    assert "not found" in host.status[-1]


def test_apply_persona_by_name_finds_and_applies_stored_persona(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    store = WorkPersonaStore(tmp_path)
    store.create(WorkPersona(name="Work", technical_profile="writer"))
    host = _Host(tmp_path)
    assert host.apply_persona_by_name("Work") is True
    assert host.features.active_profile_id == "writer"


def test_persona_store_is_lazy_and_cached(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host = _Host(tmp_path)
    first = host._persona_store()
    second = host._persona_store()
    assert first is second
