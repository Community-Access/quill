"""Organize What I Saved, QuillBeacon's agent task (codex.md 6.10, Phase 4c).

Two halves. The command, called for real on a real QuillBeacon window, with the
agent window patched where the shared opener imports it
(``quill.ui.agent_window``). Then every tool through a real
``FamilyToolRegistry`` over a real, temporary ``BeaconStore``: search, read and
the local tag ideas answer without a question; tagging and moving ask, show the
change as text, change nothing when refused or not applied, and are one undo
step when applied.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.apps.beacon.ai_task import APP, ORGANIZE, beacon_task_tools  # noqa: E402
from quill.apps.beacon.db import BeaconStore  # noqa: E402
from quill.apps.beacon.model import Beacon, Resource  # noqa: E402
from quill.apps.beacon.undo import UndoManager  # noqa: E402
from quill.core.ai.activity_log import ActivityLog  # noqa: E402
from quill.core.ai.approvals import ApprovalChoice  # noqa: E402
from quill.core.ai.family_tools import FamilyToolRegistry  # noqa: E402
from quill.core.ai.permissions import PermissionBroker, RiskLevel  # noqa: E402
from quill.core.ai.tool_gateway import AgentIdentity  # noqa: E402


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
def beacon(quill_data_dir: Path, wx_session_app, closed_machine_doors, monkeypatch):
    import quill.apps.beacon.app as beacon_app
    from quill.apps.beacon.announce import Announcer

    class _StatusBarOnly(Announcer):
        def _speak(self, *_args, **_kwargs) -> None:  # type: ignore[no-untyped-def]
            return None

    monkeypatch.setenv("QUILLBEACON_DATA", str(quill_data_dir / "beacon"))
    monkeypatch.setattr(beacon_app, "Announcer", _StatusBarOnly)
    monkeypatch.setattr(beacon_app, "init_app_sound", lambda *_a, **_k: None)
    monkeypatch.setattr(beacon_app.app_sounds, "apply", lambda *_a, **_k: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_start_capture_bridge", lambda self: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_start_tray", lambda self: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_setup_auto_sync", lambda self: None)
    frame = beacon_app.BeaconFrame()
    frame._safe_mode = False
    said: list[str] = []
    frame._announce = lambda message, *_a, **_kw: said.append(str(message))
    frame.said = said
    monkeypatch.setattr(frame, "_show_ai_window", lambda window: None)
    try:
        yield frame
    finally:
        frame.Close()
        if frame:
            frame.Destroy()


# --------------------------------------------------------------------------- #
# The command
# --------------------------------------------------------------------------- #


def test_on_copilot_it_opens_on_beacons_tools(beacon, agent_window, monkeypatch) -> None:
    service = _Service("copilot", tools=True)
    monkeypatch.setattr(beacon, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_task())(beacon)

    assert service.harnesses == ["copilot"]
    hooks = agent_window.last["args"][1]
    assert hooks.title == "Organize What I Saved"
    assert hooks.starter == ""
    assert "Ctrl+Z undoes it" in hooks.instruction_help
    runner = hooks.make_runner(object(), SimpleNamespace(on_ui=lambda fn, default=None: fn()))
    assert runner.spec is ORGANIZE
    assert isinstance(runner.context(), str)
    assert [tool.name for tool in runner.tools()] == [
        "beacon.search",
        "beacon.read_item",
        "beacon.suggest_tags",
        "beacon.tag",
        "beacon.move",
    ]
    assert beacon.said == []


def test_on_a_connection_without_agent_tools_it_sends_nothing(
    beacon, agent_window, monkeypatch
) -> None:
    import quill.ui.hosted_ai_connections as connections

    service = _Service("free", tools=False)
    monkeypatch.setattr(beacon, "_ai_service", lambda: service)
    asked: list[str] = []
    monkeypatch.setattr(
        connections, "ask_yes_no", lambda _p, sentence, **_kw: asked.append(sentence) or False
    )

    (lambda w: w.cmd_ai_task())(beacon)

    assert asked and asked[0].startswith("Agent tasks need a connection that runs tasks.")
    assert agent_window.last is None
    assert service.harnesses == []


def test_safe_mode_refuses_it(beacon, agent_window, monkeypatch) -> None:
    monkeypatch.setattr(beacon, "_ai_service", lambda: _Service("copilot", tools=True))
    beacon._safe_mode = True

    (lambda w: w.cmd_ai_task())(beacon)

    assert agent_window.last is None
    assert any("Safe Mode" in said for said in beacon.said)


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


@pytest.fixture
def host(tmp_path: Path):
    store = BeaconStore(tmp_path / "beacon.db")
    host = SimpleNamespace(store=store, undo=UndoManager(), refreshed=[], _results_cache=[])
    host._refresh_results = lambda: host.refreshed.append("results")
    for title, note, tags, cols, uri in (
        (
            "Knitting socks",
            "A pattern for knitting warm wool socks",
            ["wool"],
            ["Old"],
            "https://k.test/socks",
        ),
        ("Tax return", "Forms for this year", [], [], "C:\\Users\\me\\tax.pdf"),
    ):
        res = Resource(title=title, type="web", primary_uri=uri)
        store.put_beacon(
            Beacon(
                resource_id=res.resource_id, title=title, note=note, tags=tags, collections=cols
            ),
            resource=res,
        )
    try:
        yield host
    finally:
        store.close()


def _registry(host: Any, approver: _Approver, ctx: _Ctx | None = None) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(),
        ActivityLog(),
        AgentIdentity("beacon-organize", RiskLevel.LOW),
        app_scope=APP,
    )
    registry.register_app(APP, beacon_task_tools(host, ctx or _Ctx()))
    registry.gate.begin_task(approver)
    return registry


def _item(host, title: str) -> Beacon:
    return next(b for b in host.store.list_beacons() if b.title == title)


def test_search_read_and_tag_ideas_are_reads(host) -> None:
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(host, approver)

    found = registry.call("beacon_search", {"query": "knitting"})
    read = registry.call("beacon_read_item", {"item": "I1"})
    ideas = registry.call("beacon_suggest_tags", {"item": "I1"})

    assert found.text.splitlines() == [
        "1 item for knitting:",
        "I1. Knitting socks. Tags: wool. In: Old.",
        "Collections: Old.",
        "Tags in use: wool.",
    ]
    assert read.text.splitlines()[:5] == [
        "Title: Knitting socks",
        "Kind: web",
        "Points to: https://k.test/socks",
        "Tags: wool",
        "Collections: Old",
    ]
    assert "knitting" in ideas.text and "worked out on this computer" in ideas.text
    assert approver.asked == []


def test_a_file_on_this_computer_is_never_named_by_its_path(host) -> None:
    registry = _registry(host, _Approver(ApprovalChoice.DENY))
    registry.call("beacon_search", {"query": "tax"})

    read = registry.call("beacon_read_item", {"item": "I1"})

    assert "Points to: a file on this computer" in read.text
    assert "Users" not in read.text


def test_tag_asks_shows_the_change_and_is_one_undo_step(host) -> None:
    approver = _Approver(ApprovalChoice.ONCE)
    ctx = _Ctx(apply=True)
    registry = _registry(host, approver, ctx)
    registry.call("beacon_search", {"query": "knitting"})

    result = registry.call("beacon_tag", {"item": "I1", "add": ["crafts", "Wool"]})

    assert approver.asked == ["On Knitting socks, add the tag crafts."]
    assert ctx.previews == [
        (
            "Tag Knitting socks",
            "Item: Knitting socks\nTags now: wool\nAdd: crafts\nRemove: none\n"
            "Tags after: wool, crafts",
        )
    ]
    assert result.ok
    assert sorted(_item(host, "Knitting socks").tags) == ["crafts", "wool"]
    assert host.refreshed == ["results"]
    host.undo.undo()
    assert _item(host, "Knitting socks").tags == ["wool"]


def test_tag_not_applied_or_refused_changes_nothing(host) -> None:
    ctx = _Ctx(apply=False)
    registry = _registry(host, _Approver(ApprovalChoice.ONCE), ctx)
    registry.call("beacon_search", {"query": "knitting"})
    not_applied = registry.call("beacon_tag", {"item": "I1", "add": ["crafts"]})

    refused_ctx = _Ctx()
    refused = _registry(host, _Approver(ApprovalChoice.DENY), refused_ctx)
    refused.call("beacon_search", {"query": "knitting"})
    denied = refused.call("beacon_tag", {"item": "I1", "add": ["crafts"]})

    assert not not_applied.ok and not_applied.text == "The person did not apply it."
    assert not denied.ok and refused_ctx.previews == []
    assert _item(host, "Knitting socks").tags == ["wool"]
    assert not host.undo.can_undo()


def test_move_asks_shows_from_and_to_and_moves_on_apply(host) -> None:
    approver = _Approver(ApprovalChoice.ONCE)
    ctx = _Ctx(apply=True)
    registry = _registry(host, approver, ctx)
    registry.call("beacon_search", {"query": "knitting"})

    result = registry.call("beacon_move", {"item": "I1", "collection": "Crafts"})

    assert approver.asked == ["Move Knitting socks from Old to Crafts (a new collection)."]
    assert ctx.previews == [
        (
            "Move Knitting socks",
            "Move: Knitting socks\nFrom: Old\nTo: Crafts (a new collection)\n"
            "Collections after: Crafts",
        )
    ]
    assert result.ok
    assert _item(host, "Knitting socks").collections == ["Crafts"]
    host.undo.undo()
    assert _item(host, "Knitting socks").collections == ["Old"]


def test_move_not_applied_moves_nothing_and_unknown_items_are_explained(host) -> None:
    registry = _registry(host, _Approver(ApprovalChoice.TASK), _Ctx(apply=False))

    unknown = registry.call("beacon_move", {"item": "I7", "collection": "Crafts"})
    registry.call("beacon_search", {"query": "knitting"})
    not_applied = registry.call("beacon_move", {"item": "I1", "collection": "Crafts"})

    assert not unknown.ok and "beacon_search" in unknown.text
    assert not not_applied.ok
    assert _item(host, "Knitting socks").collections == ["Old"]
