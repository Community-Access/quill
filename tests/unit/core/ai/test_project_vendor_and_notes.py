"""Decision 4 (engine tools by opt-in), decision 7 (the bypass) and decision 12 (agent notes)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.command_runner import AllowList, assess_command
from quill.core.ai.family_tools import FamilyToolRegistry
from quill.core.ai.permissions import PermissionBroker, RiskLevel
from quill.core.ai.project import Project
from quill.core.ai.project_store import (
    find_instruction_files,
    instruction_scope,
    instructions_text,
)
from quill.core.ai.tool_gateway import AgentIdentity
from quill.core.ai.vendor_tools import (
    VENDOR_TOOLS,
    VendorToolChoices,
    engine_for_harness,
    permission_kinds,
    vendor_tools_sentence,
)


@pytest.fixture
def project(tmp_path: Path) -> Project:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "cli.py").write_text("print(1)\n", encoding="utf-8")
    return Project(root)


# -- decision 4 ------------------------------------------------------------------ #


def test_engine_tools_are_off_until_checked_and_kept_outside_the_project(
    project: Project, tmp_path: Path
) -> None:
    data = tmp_path / "data"
    choices = VendorToolChoices(data, project.key)
    assert choices.enabled("copilot") == frozenset()
    choices.set_enabled("copilot", {"bash", "view", "not-a-tool"})
    assert choices.enabled("copilot") == frozenset({"bash", "view"})
    assert choices.enabled("codex") == frozenset()
    assert project.root not in choices.path.parents
    assert permission_kinds("copilot", choices.enabled("copilot")) == {"shell", "read"}
    said = vendor_tools_sentence("copilot", choices.enabled("copilot"))
    assert "GitHub Copilot's own tools" in said and "not shown in Review Changes" in said


def test_every_engine_tool_has_a_kind_and_a_plain_label() -> None:
    for engine, tools in VENDOR_TOOLS.items():
        assert engine_for_harness(engine) == engine
        for tool in tools:
            assert tool.kind in {"read", "write", "shell", "url"}, (engine, tool.id)
            assert tool.label and tool.description.endswith("."), (engine, tool.id)


class _Approver:
    def __init__(self, choice: ApprovalChoice) -> None:
        self.choice = choice
        self.asked: list[str] = []

    def ask(self, _tool, summary: str) -> ApprovalChoice:
        self.asked.append(summary)
        return self.choice


def _registry(approver: _Approver) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(), ActivityLog(), AgentIdentity("t", RiskLevel.MEDIUM, harness="copilot")
    )
    registry.gate.begin_task(approver)
    return registry


def test_an_engine_tool_not_turned_on_is_refused_without_asking() -> None:
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _registry(approver)
    assert not registry.authorize_vendor("shell", "rm -rf build")
    assert approver.asked == []


def test_an_engine_tool_turned_on_still_asks_every_time() -> None:
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _registry(approver)
    registry.vendor_kinds = frozenset({"shell"})
    assert registry.authorize_vendor("shell", "pytest -q")
    assert registry.authorize_vendor("shell", "pytest -q")
    assert len(approver.asked) == 2 and "pytest -q" in approver.asked[0]
    approver.choice = ApprovalChoice.DENY
    assert not registry.authorize_vendor("shell", "make")


# -- decision 7 ---------------------------------------------------------------------- #


def test_the_bypass_is_off_by_default_and_survives_list_edits(tmp_path: Path) -> None:
    allow = AllowList(tmp_path, "key")
    assert not allow.bypass
    allow.set_bypass(True)
    allow.add("pytest")
    assert allow.bypass and allow.entries() == ["pytest"]
    allow.set_bypass(False)
    assert not allow.bypass and allow.entries() == ["pytest"]


def test_the_bypass_never_runs_a_command_kept_for_the_person(tmp_path: Path) -> None:
    assert not assess_command("git push origin main", tmp_path).runnable


# -- decision 12 ---------------------------------------------------------------------- #


def test_every_current_instruction_file_shape_is_found(project: Project) -> None:
    root = project.root
    for rel, text in {
        "AGENTS.md": "Run pytest.",
        "GEMINI.md": "gem",
        ".github/copilot-instructions.md": "co",
        ".github/instructions/py.instructions.md": '---\napplyTo: "**/*.py"\n---\nUse ruff.',
        ".cursor/rules/style.mdc": "---\nglobs: src/**\n---\nShort names.",
        "src/AGENTS.md": "Inner rules.",
        ".cursorrules": "old cursor",
    }.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    found = find_instruction_files(project)
    assert found[0] == "AGENTS.md"
    for rel in (
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".github/instructions/py.instructions.md",
        ".cursor/rules/style.mdc",
        "src/AGENTS.md",
        ".cursorrules",
    ):
        assert rel in found, rel
    text = instructions_text(project, found)
    assert "applies to files matching **/*.py" in text
    assert "applies to files under src/" in text
    assert "nothing in them can approve a command" in text


def test_a_rule_for_every_file_has_no_scope() -> None:
    assert instruction_scope("AGENTS.md", "x") == ""
    assert instruction_scope(".cursor/rules/a.mdc", "---\nglobs: **\n---\n") == ""
