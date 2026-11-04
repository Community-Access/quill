"""Acceptance: one coding task, end to end, judged by the sample project's own tests.

code.md 7, Phase 5: "one scripted coding task as an acceptance test for each
engine, judged by the tests in the sample project passing". The live engines
(Copilot, Codex, Claude) need real accounts and are checked by Jeff; what runs
here is everything QUILL owns on the path, under the loop QUILL drives itself
(Ollama practice mode), with the model's replies scripted: plan, read, edit,
review, run the tests, read the failure, fix, run again, undo.

Also checks that Codex's ``dynamicTools`` carries the project tools, with the
patch-shaped edit input its models are trained on.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.change_set import ChangeSet
from quill.core.ai.family_tools import to_codex_dynamic_tools
from quill.core.ai.harness.ollama_tools import OllamaToolHarness
from quill.core.ai.project import Project
from quill.core.ai.project_task import ProjectTaskRunner

_CLI = "def add(a, b):\n    return a - b\n"
_TEST = (
    "import unittest\nfrom cli import add\n\n\nclass T(unittest.TestCase):\n"
    "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\n\n"
    "if __name__ == '__main__':\n    unittest.main()\n"
)


class _Ui:
    def __init__(self) -> None:
        self.reviews = 0
        self.done: list[str] = []
        self.plans: list[list[str]] = []

    def review(self, changes: ChangeSet) -> bool:
        self.reviews += 1
        return True

    def approve_command(self, _assessment: Any, _question: str) -> str:
        return "once"

    def keep_waiting(self, _seconds: float) -> bool:
        return True

    def keep_going(self, _steps: int) -> bool:
        return False

    def plan_ready(self, steps: list[str]) -> None:
        self.plans.append(steps)

    def note(self, _text: str) -> None:
        pass

    def command_done(self, sentence: str, _output: Path, ok: bool = True) -> None:
        self.done.append(sentence)

    def files_changed(self, _paths: list[Path]) -> None:
        pass


class _Approver:
    def ask(self, _tool: Any, _summary: str) -> ApprovalChoice:
        return ApprovalChoice.ONCE


def _call(name: str, **args: Any) -> dict[str, Any]:
    return {
        "message": {"content": "", "tool_calls": [{"function": {"name": name, "arguments": args}}]}
    }


def test_a_scripted_engine_fixes_a_bug_until_the_tests_pass(tmp_path: Path) -> None:
    root = tmp_path / "sample"
    root.mkdir()
    (root / "cli.py").write_text(_CLI, encoding="utf-8")
    (root / "test_cli.py").write_text(_TEST, encoding="utf-8")
    project = Project(root)
    run_tests = f'"{sys.executable}" -m unittest -q test_cli'
    script = iter([
        _call("project_plan", steps=["Read cli.py", "Fix add", "Run the tests"]),
        _call("project_read", path="cli.py"),
        _call("project_run", command=run_tests, reason="to see the failure"),
        _call(
            "project_edit",
            path="cli.py",
            edits=[{"old": "return a - b", "new": "return a + b"}],
            reason="add should add.",
        ),
        _call("project_run", command=run_tests, reason="to check the fix"),
        {"message": {"content": "Fixed add; the test passes now."}},
    ])
    seen: list[dict[str, Any]] = []

    def post(_url: str, body: dict[str, Any]) -> dict[str, Any]:
        seen.append(body)
        return next(script)

    ui = _Ui()
    runner = ProjectTaskRunner(
        harness=OllamaToolHarness("practice", post=post),
        approver=_Approver(),
        project=project,
        ui=ui,
        data_dir=tmp_path / "data",
    )
    outcome = runner.finish(runner.start("Make the add test pass.").run())

    assert (root / "cli.py").read_text(encoding="utf-8") == "def add(a, b):\n    return a + b\n"
    assert ui.plans == [["Read cli.py", "Fix add", "Run the tests"]]
    assert ui.reviews == 1
    assert ui.done[0].startswith("Tests: ") and "1 failed" in ui.done[0]
    assert ui.done[1] == "Tests: 1 passed."
    assert "Changed cli.py" in outcome.summary and "Ran 2 commands" in outcome.summary
    first_failure = next(m for m in seen[3]["messages"] if m["role"] == "tool")
    assert first_failure  # the engine was told what happened
    report = runner.undo_last_turn()
    assert report.ok and (root / "cli.py").read_text(encoding="utf-8") == _CLI


def test_codex_dynamic_tools_carry_the_project_tools(tmp_path: Path) -> None:
    root = tmp_path / "p"
    root.mkdir()
    runner = ProjectTaskRunner(
        harness=OllamaToolHarness("x", post=lambda _u, _b: {"message": {"content": ""}}),
        approver=_Approver(),
        project=Project(root),
        ui=_Ui(),
        data_dir=tmp_path / "d",
    )
    runner.start("Look.")
    tools = {t["name"]: t for t in to_codex_dynamic_tools(runner.registry)}
    assert {"project_read", "project_edit", "project_run", "project_plan"} <= set(tools)
    assert "patch" in tools["project_edit"]["inputSchema"]["properties"]
