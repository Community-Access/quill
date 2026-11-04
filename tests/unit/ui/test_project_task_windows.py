"""The project task's windows: review, command approval, allowed commands, the task window."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.ai.change_set import ChangeSet  # noqa: E402
from quill.core.ai.command_runner import WARN_NETWORK, AllowList, assess_command  # noqa: E402


def _changes() -> ChangeSet:
    changes = ChangeSet()
    changes.propose_edit("cli.py", "a\nb\nc\nd\n", "A\nb\nc\nD\n", "Capitalise.")
    changes.propose_create("tests/test_cli.py", "def test():\n    pass\n", "A test.")
    return changes


def test_review_marks_one_change_at_a_time_and_says_so(wx_session_app: Any) -> None:
    from quill.ui.project_review_dialog import ProjectReviewDialog

    said: list[str] = []
    changes = _changes()
    dialog = ProjectReviewDialog(None, changes, said.append)
    try:
        assert dialog.files.GetCount() == 2
        assert dialog.files.GetString(0) == "cli.py, changed, 2 changes, taken"
        assert "Change 1 of 2, line 1" in dialog.details.GetValue()
        dialog._mark(False)
        assert said[-1] == "Change 1 rejected."
        assert dialog.files.GetString(0) == "cli.py, changed, 2 changes, 1 of 2 taken"
        dialog._step(1)
        assert "Change 2 of 2" in dialog.details.GetValue()
        dialog._step(1)
        assert "New file tests/test_cli.py" in dialog.details.GetValue()
        dialog._why()
        assert said[-1] == "The agent's reason: A test."
        dialog._step(1)
        assert said[-1] == "That was the last change."
    finally:
        dialog.Destroy()
    assert changes.files[0].result_text() == "a\nb\nc\nD\n"


def test_always_allow_is_offered_only_without_a_warning(wx_session_app: Any, tmp_path) -> None:
    from quill.ui.project_command_dialog import CommandApprovalDialog

    plain = CommandApprovalDialog(None, assess_command("pytest -q", tmp_path), "Run pytest.")
    try:
        assert plain.always is not None and plain.warnings is None
        assert plain.command.GetValue() == "pytest -q"
    finally:
        plain.Destroy()
    warned = assess_command("pip install requests", tmp_path)
    risky = CommandApprovalDialog(None, warned, "Install.")
    try:
        assert risky.always is None
        assert WARN_NETWORK in risky.warnings.GetValue()
    finally:
        risky.Destroy()


def test_the_allow_list_editor_adds_and_removes(wx_session_app: Any, tmp_path: Path) -> None:
    from quill.ui.project_command_dialog import AllowedCommandsDialog

    allow = AllowList(tmp_path, "k")
    dialog = AllowedCommandsDialog(None, allow, "proj")
    try:
        dialog.new_entry.SetValue("  pytest   -q ")
        dialog.add()
        assert allow.entries() == ["pytest -q"]
        dialog.entries.SetSelection(0)
        dialog.remove()
        assert allow.entries() == []
        assert not dialog.bypass.GetValue()
    finally:
        dialog.Destroy()


def test_the_task_window_reaches_plan_changes_and_output_by_key(wx_session_app: Any) -> None:
    from quill.ui.project_task_window import ProjectTaskHooks, ProjectTaskWindow

    said: list[str] = []
    hooks = ProjectTaskHooks(
        announce=said.append,
        connection="copilot",
        make_runner=lambda _a, _u: None,
        make_host=lambda _b, _n: None,
        project="proj",
    )
    window = ProjectTaskWindow(None, hooks)
    try:
        assert window.GetTitle() == "Do a Project Task"
        assert "Project proj" in window.status.GetValue()
        labels = set(window.project_buttons)
        for name in ("Plan", "Changes", "Output", "Transcript", "Undo Last Turn"):
            assert name in labels
        window.go_to_plan()
        assert said[-1] == "There is no plan yet in this task."
        window.show_plan(["Read cli.py", "Add the flag"])
        assert said[-1] == "The plan is ready. 2 steps."
        window.go_to_plan()
        text = window.transcript.GetValue()
        assert text[window.transcript.GetInsertionPoint() :].startswith("Plan:")
        window.open_output()
        assert said[-1] == "No command has run in this task yet."
    finally:
        window.Destroy()


def test_every_new_control_has_f1_help(wx_session_app: Any, tmp_path: Path) -> None:
    from quill.ui.app_context_help import ensure_help_provider
    from quill.ui.project_command_dialog import AllowedCommandsDialog, CommandApprovalDialog
    from quill.ui.project_review_dialog import ProjectReviewDialog

    ensure_help_provider()  # SetHelpText stores nothing without a provider
    built = [
        ProjectReviewDialog(None, _changes()),
        CommandApprovalDialog(None, assess_command("rm -rf x", tmp_path), "Remove."),
        AllowedCommandsDialog(None, AllowList(tmp_path, "k"), "p"),
    ]
    try:
        for dialog in built:
            for child in dialog.GetChildren():
                if isinstance(child, (wx.Button, wx.TextCtrl, wx.ListBox, wx.CheckBox)):
                    assert child.GetHelpText().strip(), (type(dialog).__name__, child.GetLabel())
    finally:
        for dialog in built:
            dialog.Destroy()
