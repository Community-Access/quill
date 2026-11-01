"""Add Abbreviations from a Document, Quill Inkwell's agent task (codex.md 6.12, Phase 4c).

Two halves. The command, called for real on a real Quill Inkwell window (Safe
Mode at construction, so no keyboard hook), with the agent window patched where
the shared opener imports it (``quill.ui.agent_window``). Then every tool
through a real ``FamilyToolRegistry`` on that window and its real library file:
choosing a document opens the picker and asks before any text goes; listing is
a read; adding asks, shows every entry as "abbreviation -> expansion", leaves
out clashes, and adds nothing when refused or not applied.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.apps.inkwell_ai_task import (  # noqa: E402
    ADD_FROM_DOCUMENT,
    APP,
    inkwell_task_tools,
)
from quill.core.ai.activity_log import ActivityLog  # noqa: E402
from quill.core.ai.approvals import ApprovalChoice  # noqa: E402
from quill.core.ai.family_tools import FamilyToolRegistry  # noqa: E402
from quill.core.ai.permissions import PermissionBroker, RiskLevel  # noqa: E402
from quill.core.ai.tool_gateway import AgentIdentity  # noqa: E402

#: A real window with its machine-wide doors closed (closed_machine_doors in conftest).
pytestmark = pytest.mark.usefixtures("closed_machine_doors")


class _Window:
    last: dict | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        type(self).last = {"args": args, "kwargs": kwargs}

    def Show(self):  # noqa: N802 - wx API shape
        pass

    def Raise(self):  # noqa: N802 - wx API shape
        pass

    def SetFocus(self):  # noqa: N802 - wx API shape
        pass

    def Bind(self, *_args: Any, **_kwargs: Any):  # noqa: N802 - wx API shape
        pass


class _Service:
    signed_in = True
    direct = True

    def __init__(self, connection: str, *, tools: bool) -> None:
        self.connection_in_use = connection
        self.tools = tools
        self.harnesses: list[str] = []

    def can_do(self, capability: str) -> bool:
        return capability != "agent_tools" or self.tools

    def needs_label(self, capability: str) -> str:
        return "" if self.can_do(capability) else "(needs Copilot or Codex)"

    def agent_harness(self, connection: str) -> object:
        self.harnesses.append(connection)
        return object()

    def capability_offer(self, capability: str) -> Any:
        from quill.core.ai.connection_caps import SwitchOffer

        return SwitchOffer(
            "Agent tasks need a connection that runs tasks. My GitHub Copilot can. "
            "Switch to it and ask?",
            target="copilot",
        )


@pytest.fixture
def agent_window(monkeypatch):
    import quill.ui.agent_window as module

    cls = type("AgentWindow", (_Window,), {"last": None})
    monkeypatch.setattr(module, "AgentWindow", cls)
    return cls


@pytest.fixture
def inkwell(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    from quill.apps.inkwell import QuillInkwellFrame

    frame = QuillInkwellFrame(safe_mode=True)  # no keyboard hook
    frame._safe_mode = False
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    monkeypatch.setattr(frame, "_show_ai_window", lambda window: None)
    try:
        yield frame
    finally:
        frame._preference_saver.flush()
        timer = getattr(frame, "_ipc_timer", None)
        if timer is not None:
            timer.Stop()
        frame._remove_tray_icon()
        frame.frame.Destroy()


def _with_library(frame, *entries: tuple[str, str]) -> None:
    from quill.core.abbreviations import (
        Abbreviation,
        AbbreviationLibrary,
        save_abbreviation_library,
    )

    library = AbbreviationLibrary(
        version=2,
        abbreviations=[
            Abbreviation(id=f"id-{name}", abbreviation=name, expansion=text)
            for name, text in entries
        ],
    )
    save_abbreviation_library(library, frame._data_dir)
    frame._library = library


# --------------------------------------------------------------------------- #
# The command
# --------------------------------------------------------------------------- #


def test_on_copilot_it_opens_on_inkwells_tools(inkwell, agent_window, monkeypatch) -> None:
    service = _Service("copilot", tools=True)
    monkeypatch.setattr(inkwell, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_task())(inkwell)

    assert service.harnesses == ["copilot"]
    hooks = agent_window.last["args"][1]
    assert hooks.title == "Add Abbreviations from a Document"
    assert hooks.starter == ""
    assert "asked before its text is sent" in hooks.instruction_help
    runner = hooks.make_runner(object(), SimpleNamespace(on_ui=lambda fn, default=None: fn()))
    assert runner.spec is ADD_FROM_DOCUMENT
    assert runner.context().startswith("Abbreviations in the library:")
    assert [tool.name for tool in runner.tools()] == [
        "inkwell.choose_document",
        "inkwell.list_abbreviations",
        "inkwell.add_abbreviations",
    ]
    assert inkwell.said == []


def test_on_a_connection_without_agent_tools_it_sends_nothing(
    inkwell, agent_window, monkeypatch
) -> None:
    import quill.ui.hosted_ai_connections as connections

    service = _Service("free", tools=False)
    monkeypatch.setattr(inkwell, "_ai_service", lambda: service)
    asked: list[str] = []
    monkeypatch.setattr(
        connections, "ask_yes_no", lambda _p, sentence, **_kw: asked.append(sentence) or False
    )

    (lambda w: w.cmd_ai_task())(inkwell)

    assert asked and asked[0].startswith("Agent tasks need a connection that runs tasks.")
    assert agent_window.last is None
    assert service.harnesses == []


def test_safe_mode_refuses_it(inkwell, agent_window, monkeypatch) -> None:
    monkeypatch.setattr(inkwell, "_ai_service", lambda: _Service("copilot", tools=True))
    inkwell._safe_mode = True

    (lambda w: w.cmd_ai_task())(inkwell)

    assert agent_window.last is None
    assert any("Safe Mode" in said for said in inkwell.said)


# --------------------------------------------------------------------------- #
# The tools, through a real registry
# --------------------------------------------------------------------------- #


class _Approver:
    def __init__(self, choice: ApprovalChoice) -> None:
        self.choice = choice
        self.asked: list[str] = []

    def ask(self, tool, summary: str) -> ApprovalChoice:
        self.asked.append(summary)
        return self.choice


class _Ctx:
    def __init__(self, apply: bool = True) -> None:
        self.apply = apply
        self.previews: list[tuple[str, str]] = []

    def on_ui(self, fn, default=None):
        return fn()

    def preview(self, title: str, text: str) -> bool:
        self.previews.append((title, text))
        return self.apply

    def note(self, text: str) -> None:
        pass


def _registry(host: Any, approver: _Approver, ctx: _Ctx | None = None) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(),
        ActivityLog(),
        AgentIdentity("inkwell-add-from-document", RiskLevel.LOW),
        app_scope=APP,
    )
    registry.register_app(APP, inkwell_task_tools(host, ctx or _Ctx()))
    registry.gate.begin_task(approver)
    return registry


def _names(frame) -> list[str]:
    from quill.core.abbreviations import load_abbreviation_library

    return sorted(a.abbreviation for a in load_abbreviation_library(frame._data_dir).abbreviations)


def test_choose_document_picks_reads_and_asks_before_any_text_goes(
    inkwell, tmp_path, monkeypatch
) -> None:
    doc = tmp_path / "Private Folder" / "report.txt"
    doc.parent.mkdir()
    doc.write_text("The Tuesday planning meeting. The Tuesday planning meeting.", "utf-8")
    monkeypatch.setattr(inkwell, "_inkwell_pick_document", lambda: doc)
    confirmed: list[str] = []
    monkeypatch.setattr(
        inkwell, "_inkwell_confirm_send", lambda name, text: confirmed.append(name) or True
    )
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(inkwell, approver)

    result = registry.call("inkwell_choose_document", {})

    assert confirmed == ["report.txt"]
    assert result.text.startswith("The text of report.txt (all of it):")
    assert "Tuesday planning meeting" in result.text
    assert "Private Folder" not in result.text
    assert approver.asked == []


def test_choose_document_cancelled_or_not_agreed_sends_no_text(
    inkwell, tmp_path, monkeypatch
) -> None:
    doc = tmp_path / "report.txt"
    doc.write_text("secret words", "utf-8")
    registry = _registry(inkwell, _Approver(ApprovalChoice.DENY))

    monkeypatch.setattr(inkwell, "_inkwell_pick_document", lambda: None)
    cancelled = registry.call("inkwell_choose_document", {})
    monkeypatch.setattr(inkwell, "_inkwell_pick_document", lambda: doc)
    monkeypatch.setattr(inkwell, "_inkwell_confirm_send", lambda name, text: False)
    refused = registry.call("inkwell_choose_document", {})

    assert cancelled.text == "The person did not choose a document."
    assert refused.text == "The person chose report.txt but did not agree to send its text."
    assert "secret" not in cancelled.text + refused.text


def test_list_abbreviations_is_a_read(inkwell) -> None:
    _with_library(inkwell, ("btw", "by the way"), ("sig", "Kind regards,\nJeff"))
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(inkwell, approver)

    result = registry.call("inkwell_list_abbreviations", {})

    assert result.text.splitlines() == [
        "2 abbreviations:",
        "btw -> by the way",
        "sig -> Kind regards, (new line) Jeff",
    ]
    assert approver.asked == []


def test_add_asks_previews_every_entry_leaves_out_clashes_and_adds(inkwell) -> None:
    _with_library(inkwell, ("btw", "by the way"))
    approver = _Approver(ApprovalChoice.ONCE)
    ctx = _Ctx(apply=True)
    registry = _registry(inkwell, approver, ctx)

    result = registry.call(
        "inkwell_add_abbreviations",
        {
            "entries": [
                {"abbreviation": "tpm", "expansion": "the Tuesday planning meeting"},
                {"abbreviation": "BTW", "expansion": "between the wars"},
                {"abbreviation": "x", "expansion": "too short"},
            ]
        },
    )

    assert approver.asked == ["Add 1 abbreviation to Quill Inkwell: tpm."]
    assert ctx.previews == [
        (
            "Add Abbreviations",
            "Add 1 abbreviation:\n"
            "tpm -> the Tuesday planning meeting\n"
            "\n"
            "Left out:\n"
            "BTW -> between the wars (you already have btw -> by the way)\n"
            "x -> too short (an abbreviation is 2 to 12 letters or digits)",
        )
    ]
    assert result.ok and result.text.startswith("Added 1 abbreviation. Left out 2:")
    assert _names(inkwell) == ["btw", "tpm"]
    assert registry.mutated()


def test_add_not_applied_or_refused_adds_nothing(inkwell) -> None:
    _with_library(inkwell, ("btw", "by the way"))
    entries = {"entries": ["tpm -> the Tuesday planning meeting"]}

    not_applied = _registry(inkwell, _Approver(ApprovalChoice.ONCE), _Ctx(apply=False)).call(
        "inkwell_add_abbreviations", entries
    )
    ctx = _Ctx()
    refused = _registry(inkwell, _Approver(ApprovalChoice.DENY), ctx).call(
        "inkwell_add_abbreviations", entries
    )

    assert not not_applied.ok and not_applied.text == "The person did not apply it."
    assert not refused.ok and ctx.previews == []
    assert _names(inkwell) == ["btw"]


def test_only_clashes_show_nothing_and_say_why(inkwell) -> None:
    _with_library(inkwell, ("btw", "by the way"))
    ctx = _Ctx()
    registry = _registry(inkwell, _Approver(ApprovalChoice.TASK), ctx)

    result = registry.call("inkwell_add_abbreviations", {"entries": ["btw -> bring the wine"]})

    assert not result.ok and "you already have btw -> by the way" in result.text
    assert ctx.previews == []
    assert _names(inkwell) == ["btw"]
