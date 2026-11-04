"""The shared project commands: the Developer gate, Safe Mode, Ctrl+3's two doors, undo."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.ai import project_task_words as words
from quill.core.ai.project import Project
from quill.ui.project_task_commands import ProjectTaskMixin


class _Editor(ProjectTaskMixin):
    def __init__(self, data_dir: Path, *, developer: bool = True, safe: bool = False) -> None:
        self.host = SimpleNamespace(
            data_dir=data_dir,
            feature_enabled=lambda name: developer and name == "coding",
            ai_project=None,
            ai_project_window=None,
        )
        self.safe = safe
        self.said: list[str] = []
        self.document_tasks = 0
        self.reloaded: list[Path] = []

    def _ai_host(self) -> Any:
        return self.host

    def _ai_safe_mode(self) -> bool:
        return self.safe

    def _announce(self, text: str, **_kw: Any) -> None:
        self.said.append(text)

    def _open_document_task(self, starter: str = "") -> None:  # AgentTaskMixin's door
        self.document_tasks += 1

    def _reload_agent_changed(self, paths: list[Path]) -> None:
        self.reloaded.extend(paths)


@pytest.fixture
def project(tmp_path: Path) -> Project:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "cli.py").write_text("one\n", encoding="utf-8")
    return Project(root)


def test_outside_the_developer_profile_project_tasks_say_why(tmp_path: Path) -> None:
    editor = _Editor(tmp_path, developer=False)
    editor.cmd_open_project_folder()
    editor.cmd_project_task()
    assert editor.said == [words.NEEDS_DEVELOPER, words.NEEDS_DEVELOPER]


def test_safe_mode_refuses_project_tasks(tmp_path: Path, project: Project) -> None:
    from quill.core.ai.connection_words import SAFE_MODE_ABOUT

    editor = _Editor(tmp_path, safe=True)
    editor.host.ai_project = project
    editor.cmd_project_task()
    editor.cmd_open_project_folder()
    assert editor.said == [SAFE_MODE_ABOUT, SAFE_MODE_ABOUT]


def test_ctrl_3_is_a_document_task_until_a_project_is_open(tmp_path: Path) -> None:
    editor = _Editor(tmp_path)
    editor.cmd_ai_task()
    assert editor.document_tasks == 1


def test_ctrl_3_stays_a_document_task_outside_the_developer_profile(
    tmp_path: Path, project: Project
) -> None:
    editor = _Editor(tmp_path, developer=False)
    editor.host.ai_project = project
    editor.cmd_ai_task()
    assert editor.document_tasks == 1


def test_commands_that_need_a_project_say_so(tmp_path: Path) -> None:
    editor = _Editor(tmp_path)
    for command in (
        editor.cmd_close_project,
        editor.cmd_undo_agent_turn,
        editor.cmd_open_command_output,
        editor.cmd_project_transcript,
        editor.cmd_project_allowed_commands,
        editor.cmd_project_engine_tools,
    ):
        command()
    assert editor.said == [words.NO_PROJECT] * 6


def test_stop_agent_with_nothing_running_says_so(tmp_path: Path) -> None:
    editor = _Editor(tmp_path)
    editor.cmd_stop_agent()
    assert editor.said == [words.NO_TASK_RUNNING]


def test_undo_works_without_the_window_from_the_checkpoints_on_disk(
    tmp_path: Path, project: Project
) -> None:
    from quill.core.ai.checkpoints import CheckpointStore

    data = tmp_path / "data"
    store = CheckpointStore(project, data)
    store.ensure_turn()
    (project.root / "cli.py").write_text("two\n", encoding="utf-8")
    store.close_turn()
    editor = _Editor(data)
    editor.host.ai_project = project
    editor.cmd_undo_agent_turn()
    assert (project.root / "cli.py").read_text(encoding="utf-8") == "one\n"
    assert editor.said[-1].startswith("Undid turn 1.")
    assert editor.reloaded == [project.root / "cli.py"]


def test_close_project_puts_ctrl_3_back(tmp_path: Path, project: Project) -> None:
    editor = _Editor(tmp_path)
    editor.host.ai_project = project
    editor.cmd_close_project()
    assert editor.host.ai_project is None and editor.said == [words.PROJECT_CLOSED]
    editor.cmd_ai_task()
    assert editor.document_tasks == 1


def test_a_refused_undo_offers_the_file_as_it_was(
    tmp_path: Path, project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    from quill.core.ai.checkpoints import CheckpointStore

    data = tmp_path / "data"
    store = CheckpointStore(project, data)
    store.ensure_turn()
    (project.root / "cli.py").write_text("two\n", encoding="utf-8")
    store.close_turn()
    (project.root / "cli.py").write_text("my own edit\n", encoding="utf-8")
    asked: list[str] = []
    monkeypatch.setattr(
        "quill.ui.dialog_contract.show_message_box",
        lambda message, *_a, **_k: asked.append(message) or wx.YES,
    )
    opened: list[Path] = []
    editor = _Editor(data)
    editor.host.ai_project = project
    editor._ai_parent = lambda: None
    editor._ai_open_file = opened.append
    editor.cmd_undo_agent_turn()
    assert (project.root / "cli.py").read_text(encoding="utf-8") == "my own edit\n"
    assert "Undo would lose your edits" in asked[0] and "compare" in asked[0]
    assert opened and opened[0].read_text(encoding="utf-8") == "one\n"
    assert project.root not in opened[0].parents


def test_the_project_cell_is_empty_without_a_project_and_names_it_with_one(
    tmp_path: Path, project: Project
) -> None:
    from quill.apps.lite_status_cells import SHOWN_ONLY_WITH_TEXT, project_cell

    editor = _Editor(tmp_path)
    assert editor.project_status_text() == "" and project_cell(editor) == ""
    assert "project" in SHOWN_ONLY_WITH_TEXT
    editor.host.ai_project = project
    editor.host.ai_project_branch = "main"
    assert editor.project_status_text() == "Project proj, main"
    editor.host.ai_project_window = SimpleNamespace(_present_next=[object()], _running=True)
    assert editor.project_status_text() == "Project proj, main, waiting for you"
