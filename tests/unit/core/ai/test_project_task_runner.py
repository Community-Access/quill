"""Do a Project Task end to end on a fake engine, and GATE-PROJECT-REVIEW (code.md 4.9, 5.4)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

import pytest

from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.change_set import ChangeSet
from quill.core.ai.harness import HarnessCapabilities, HarnessResult
from quill.core.ai.project import Project
from quill.core.ai.project_task import ProjectTaskRunner
from quill.core.ai.project_tools import (
    COACH_TOOL_NAMES,
    apply_search_replace,
    apply_unified_diff,
)

CLI = "import argparse\n\ndef main():\n    parser = argparse.ArgumentParser()\n    return parser\n"


class _Session:
    def __init__(self, registry, approver, script) -> None:
        self.registry = registry
        self.approver = approver
        self.script = script
        self.results: list[Any] = []

    @property
    def session_id(self) -> str:
        return "s"

    def run(self) -> HarnessResult:
        self.registry.gate.begin_task(self.approver)
        try:
            for name, args in self.script:
                ok, _why = self.registry.authorize(name, args)
                self.results.append(self.registry.call(name, args) if ok else None)
            return HarnessResult("completed", "I added the flag.")
        finally:
            self.registry.gate.end_task()

    def cancel(self) -> None:
        pass

    def send(self, _text: str) -> None:
        pass

    def end(self) -> None:
        pass


class _Harness:
    id = "copilot"

    def __init__(self, script) -> None:
        self.script = script
        self.sessions: list[_Session] = []
        self.contexts: list[Any] = []
        self.tool_names: list[list[str]] = []

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(app_tools=True)

    def start_tool_session(self, agent, ctx, tools, approver, emit, **_kw):
        self.contexts.append(ctx)
        self.tool_names.append(tools.names())
        session = _Session(tools, approver, self.script)
        self.sessions.append(session)
        return session


class _Approver:
    def __init__(self) -> None:
        self.asked: list[str] = []

    def ask(self, tool, summary: str) -> ApprovalChoice:
        self.asked.append(summary)
        return ApprovalChoice.ONCE


class _Ui:
    def __init__(self, accept: bool = True, command: str = "once") -> None:
        self.accept = accept
        self.command = command
        self.reviews: list[list[str]] = []
        self.questions: list[str] = []
        self.notes: list[str] = []
        self.plans: list[list[str]] = []
        self.done: list[str] = []
        self.changed: list[Path] = []

    def review(self, changes: ChangeSet) -> bool:
        self.reviews.append([f.row_text() for f in changes.files])
        if not self.accept:
            changes.reject_all()
        return self.accept

    def approve_command(self, assessment, question: str) -> str:
        self.questions.append(question)
        return self.command

    def keep_waiting(self, seconds: float) -> bool:
        return True

    def keep_going(self, steps: int) -> bool:
        return False

    def plan_ready(self, steps: list[str]) -> None:
        self.plans.append(steps)

    def note(self, text: str) -> None:
        self.notes.append(text)

    def command_done(self, sentence: str, output: Path) -> None:
        self.done.append(sentence)

    def files_changed(self, paths: list[Path]) -> None:
        self.changed.extend(paths)


@pytest.fixture
def project(tmp_path: Path) -> Project:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "cli.py").write_text(CLI, encoding="utf-8")
    (root / ".env").write_text("TOKEN=abc\n", encoding="utf-8")
    return Project(root)


def _runner(
    project: Project, script, ui: _Ui, tmp_path: Path, **kw
) -> tuple[ProjectTaskRunner, _Harness]:
    harness = _Harness(script)
    runner = ProjectTaskRunner(
        harness=harness,
        approver=_Approver(),
        project=project,
        ui=ui,
        data_dir=tmp_path / "data",
        **kw,
    )
    return runner, harness


def _python(code: str) -> str:
    return f'"{sys.executable}" -c "{code}"'


def test_a_whole_turn(project: Project, tmp_path: Path) -> None:
    script = [
        ("project_plan", {"steps": ["Read cli.py", "Add the flag", "Add a test"]}),
        ("project_list", {}),
        ("project_read", {"path": "cli.py"}),
        ("project_read", {"path": ".env"}),
        (
            "project_edit",
            {
                "path": "cli.py",
                "reason": "Add --verbose.",
                "edits": [
                    {
                        "old": "    return parser\n",
                        "new": "    parser.add_argument('--verbose')\n    return parser\n",
                    }
                ],
            },
        ),
        (
            "project_create",
            {"path": "tests/test_cli.py", "text": "def test_x():\n    assert True\n"},
        ),
        ("project_run", {"command": _python("print('1 passed')"), "reason": "to check the test"}),
    ]
    ui = _Ui()
    runner, harness = _runner(project, script, ui, tmp_path)
    session = runner.start("Add a --verbose flag and a test.")
    outcome = runner.finish(session.run())
    results = harness.sessions[0].results
    assert "hidden by QUILL" in results[1].text
    assert "looks like a secret" in results[3].text
    assert "Nothing is written yet" in results[4].text
    assert ui.plans == [["Read cli.py", "Add the flag", "Add a test"]]
    # The command made the change set go to review first, then ran.
    assert ui.reviews and ui.reviews[0][0].startswith("cli.py, changed, 1 change")
    assert "Accepted all 1 change in cli.py." in results[6].text
    assert ui.questions and ui.questions[0].startswith("Run ")
    assert "to check the test" in ui.questions[0]
    assert ui.done and ui.done[0].startswith("The command finished")
    assert "--verbose" in (project.root / "cli.py").read_text(encoding="utf-8")
    assert (project.root / "tests" / "test_cli.py").exists()
    assert outcome.summary.startswith("Turn 1. Done. Changed cli.py and added tests/test_cli.py.")
    assert "Undo Last Turn" in outcome.summary
    # Undo puts every file back.
    report = runner.undo_last_turn()
    assert report.ok, report.sentence
    assert (project.root / "cli.py").read_text(encoding="utf-8") == CLI
    assert not (project.root / "tests" / "test_cli.py").exists()
    md = runner.transcript_markdown()
    assert md.startswith("# Project task: Add a --verbose flag and a test.")
    assert "## Turn 1: you asked" in md and "### Plan" in md and "### Changes" in md
    assert "### Commands" in md and "### Result" in md


def test_rejected_review_writes_nothing_and_tells_the_model(
    project: Project, tmp_path: Path
) -> None:
    script = [
        (
            "project_edit",
            {
                "path": "cli.py",
                "edits": [
                    {"old": "argparse.ArgumentParser()", "new": "argparse.ArgumentParser(1)"}
                ],
            },
        ),
        ("project_run", {"command": _python("print(1)")}),
    ]
    ui = _Ui(accept=False, command="deny")
    runner, harness = _runner(project, script, ui, tmp_path)
    outcome = runner.finish(runner.start("Change it.").run())
    assert (project.root / "cli.py").read_text(encoding="utf-8") == CLI
    text = harness.sessions[0].results[1].text
    assert "Rejected every change in cli.py" in text
    assert "did not allow this command" in text
    assert "No files were changed" in outcome.summary
    assert "1 proposed change was not taken" in outcome.summary


def test_pending_changes_are_reviewed_when_the_turn_ends(project: Project, tmp_path: Path) -> None:
    script = [("project_edit", {"path": "cli.py", "edits": [{"old": "main", "new": "start"}]})]
    ui = _Ui()
    runner, _harness = _runner(project, script, ui, tmp_path)
    runner.finish(runner.start("Rename main.").run())
    assert len(ui.reviews) == 1
    assert "def start()" in (project.root / "cli.py").read_text(encoding="utf-8")


def test_never_list_is_refused_without_asking(project: Project, tmp_path: Path) -> None:
    ui = _Ui()
    runner, harness = _runner(
        project, [("project_run", {"command": "git push origin main"})], ui, tmp_path
    )
    runner.finish(runner.start("Push it.").run())
    assert ui.questions == []
    assert "keeps this step for themselves" in harness.sessions[0].results[0].text


def test_always_allow_skips_the_question_next_time(project: Project, tmp_path: Path) -> None:
    command = _python("print(2)")
    ui = _Ui(command="always")
    runner, _harness = _runner(project, [("project_run", {"command": command})], ui, tmp_path)
    runner.finish(runner.start("Run it.").run())
    runner.finish(runner.start("Run it again.").run())
    assert len(ui.questions) == 1


def test_coach_mode_has_no_way_to_change_or_run(project: Project, tmp_path: Path) -> None:
    runner, harness = _runner(project, [], _Ui(), tmp_path, coach=True)
    runner.start("Teach me.")
    names = set(harness.tool_names[0])
    assert names == set(COACH_TOOL_NAMES)
    assert "project.edit" not in names and "project.run" not in names


def test_next_turn_is_told_what_happened(project: Project, tmp_path: Path) -> None:
    script = [("project_plan", {"steps": ["Look"]})]
    runner, harness = _runner(project, script, _Ui(), tmp_path)
    runner.finish(runner.start("First thing.").run())
    runner.finish(runner.start("Second thing.").run())
    assert "Earlier in this task" in harness.contexts[1].context_text
    assert "First thing." in harness.contexts[1].context_text


def test_step_cap_stops_a_runaway_turn(project: Project, tmp_path: Path) -> None:
    script = [("project_list", {})] * 45
    runner, harness = _runner(project, script, _Ui(), tmp_path)
    runner.finish(runner.start("Loop.").run())
    texts = [r.text for r in harness.sessions[0].results if r is not None]
    assert any("stopped the task here" in t for t in texts)


def test_search_replace_and_unified_diff() -> None:
    assert apply_search_replace("a\nb\nc\n", [{"old": "b", "new": "B"}], "x") == "a\nB\nc\n"
    with pytest.raises(Exception, match="appears 2 times"):
        apply_search_replace("b b", [{"old": "b", "new": "c"}], "x")
    diff = "--- a/x\n+++ b/x\n@@ -2,2 +2,2 @@\n b\n-c\n+C\n"
    assert apply_unified_diff("a\nb\nc\nd\n", diff, "x") == "a\nb\nC\nd\n"


# -- GATE-PROJECT-REVIEW ------------------------------------------------------ #

_WRITERS = {
    "write_text",
    "write_bytes",
    "unlink",
    "rename",
    "rmdir",
    "mkdir",
    "rmtree",
    "remove",
    "move",
    "copy",
    "copyfile",
    "touch",
    "symlink_to",
}
#: Names a string or list also has; they count only as ``os.x`` or ``shutil.x``.
_AMBIGUOUS = frozenset({"replace", "remove", "copy"})
_SCANNED = (
    "project.py",
    "project_tools.py",
    "project_task.py",
    "project_outline.py",
    "code_diff.py",
    "project_transcript.py",
)


@pytest.mark.parametrize("name", _SCANNED)
def test_gate_project_review_no_tool_writes_files(name: str) -> None:
    """No project module writes a file: only ChangeSet.apply does, after review.

    project_task.py may write its own task history into app data through the
    change set's atomic writer, and nothing else.
    """
    root = Path(__file__).resolve().parents[4] / "quill" / "core" / "ai"
    tree = ast.parse((root / name).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            attr = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            owner = (
                func.value.id
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                else ""
            )
            if attr in _AMBIGUOUS:
                # str.replace is everywhere; only os/shutil's file versions count.
                assert owner not in ("os", "shutil"), f"{name} line {node.lineno} calls {attr}"
                continue
            assert attr not in _WRITERS, f"{name} line {node.lineno} calls {attr}"
            if attr == "open":
                mode = node.args[1] if len(node.args) > 1 else None
                for kw in node.keywords:
                    if kw.arg == "mode":
                        mode = kw.value
                assert not (
                    isinstance(mode, ast.Constant) and set(str(mode.value)) & set("wax+")
                ), f"{name} line {node.lineno} opens a file for writing"
            if attr in ("write_text_atomic", "write_bytes_atomic"):
                assert name == "project_task.py", f"{name} writes through the atomic writer"
