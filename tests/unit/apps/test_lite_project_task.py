"""Project tasks in QUILL Lite (code.md 6.4): every Coding handler, called for real.

Every handler is **called** in a lambda: ``quill.tools.lite_command_coverage``
finds coverage by walking the AST for real calls. The handlers are the shared
mixin's (quill/ui/project_task_commands.py), the same ones QUILL runs through
its adapter, so these also stand for QUILL's rows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.ai import project_task_words as words
from quill.core.ai.project import Project


@pytest.fixture
def coder(lite_window, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A Lite window in the Developer profile, with a project folder beside it."""
    win = lite_window("Some text.")
    host = win._ai_host()
    monkeypatch.setattr(host, "feature_enabled", lambda name: True, raising=False)
    monkeypatch.setattr(host, "data_dir", tmp_path / "data", raising=False)
    root = tmp_path / "proj"
    root.mkdir()
    (root / "cli.py").write_text("one\n", encoding="utf-8")
    win.project_root = root
    return win


def _open(win: Any, monkeypatch: pytest.MonkeyPatch) -> Project:
    import quill.ui.project_open_dialog as dialogs

    monkeypatch.setattr(dialogs, "choose_project_folder", lambda _parent, _recent: win.project_root)
    (lambda w: w.cmd_open_project_folder())(win)
    return win._ai_project()


def test_open_project_folder_makes_the_folder_the_project(coder, monkeypatch) -> None:
    project = _open(coder, monkeypatch)
    assert project is not None and project.root == coder.project_root.resolve()
    assert coder.announcements[-1] == words.project_opened("proj")
    assert coder.project_status_text() == "Project proj"


def test_close_project_puts_ctrl_3_back(coder, monkeypatch) -> None:
    _open(coder, monkeypatch)
    (lambda w: w.cmd_close_project())(coder)
    assert coder._ai_project() is None and coder.announcements[-1] == words.PROJECT_CLOSED


def test_project_task_needs_a_project(coder) -> None:
    (lambda w: w.cmd_project_task())(coder)
    assert coder.announcements[-1] == words.NO_PROJECT


def test_stop_agent_with_nothing_running(coder) -> None:
    (lambda w: w.cmd_stop_agent())(coder)
    assert coder.announcements[-1] == words.NO_TASK_RUNNING


def test_undo_last_agent_turn_from_the_menu(coder, monkeypatch) -> None:
    from quill.core.ai.checkpoints import CheckpointStore

    project = _open(coder, monkeypatch)
    store = CheckpointStore(project, Path(coder._ai_host().data_dir))
    store.ensure_turn()
    (project.root / "cli.py").write_text("two\n", encoding="utf-8")
    store.close_turn()
    (lambda w: w.cmd_undo_agent_turn())(coder)
    assert (project.root / "cli.py").read_text(encoding="utf-8") == "one\n"
    assert coder.announcements[-1].startswith("Undid turn 1.")


def test_explain_last_turn_with_no_task(coder) -> None:
    (lambda w: w.cmd_explain_agent_turn())(coder)
    assert coder.announcements[-1] == words.NOTHING_TO_EXPLAIN


def test_command_output_and_transcript_before_anything_ran(coder, monkeypatch) -> None:
    _open(coder, monkeypatch)
    (lambda w: w.cmd_open_command_output())(coder)
    assert coder.announcements[-1] == words.NO_OUTPUT
    (lambda w: w.cmd_project_transcript())(coder)
    assert coder.announcements[-1] == words.NO_TRANSCRIPT_YET


def test_allowed_commands_opens_on_this_projects_list(coder, monkeypatch) -> None:
    import quill.ui.project_command_dialog as dialogs

    project = _open(coder, monkeypatch)
    seen: list[Any] = []
    monkeypatch.setattr(dialogs, "edit_allowed_commands", lambda *a: seen.append(a))
    (lambda w: w.cmd_project_allowed_commands())(coder)
    allow, name = seen[0][1], seen[0][2]
    assert name == "proj" and project.root not in allow.path.parents


def test_engine_tools_opens_for_the_connection_in_use(coder, monkeypatch) -> None:
    import quill.ui.project_open_dialog as dialogs

    _open(coder, monkeypatch)
    monkeypatch.setattr(
        coder, "_ai_service", lambda: type("S", (), {"connection_in_use": "copilot"})()
    )
    seen: list[Any] = []
    monkeypatch.setattr(dialogs, "edit_engine_tools", lambda *a: seen.append(a))
    (lambda w: w.cmd_project_engine_tools())(coder)
    assert seen[0][1] == "copilot"
