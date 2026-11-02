"""Find the Part Where, Quill Media Player's agent task (codex.md 6.11, Phase 4c).

Two halves. The command, called for real on a real Quill Media Player window,
with the agent window patched where the shared opener imports it
(``quill.ui.agent_window``). Then every tool through a real
``FamilyToolRegistry``: where am I, the chapters and the bookmarks answer as
text without a question; going somewhere asks "Go to 1:02:30 in <title>.",
seeks the way Go to Position does, and does nothing when refused. There is no
transcript source, and the tools do not pretend to one.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.apps.player_ai_task import APP, FIND_THE_PART, player_task_tools  # noqa: E402
from quill.core.ai.activity_log import ActivityLog  # noqa: E402
from quill.core.ai.approvals import ApprovalChoice  # noqa: E402
from quill.core.ai.family_tools import FamilyToolRegistry  # noqa: E402
from quill.core.ai.permissions import PermissionBroker, RiskLevel  # noqa: E402
from quill.core.ai.tool_gateway import AgentIdentity  # noqa: E402
from quill.core.media.bookmarks import BookmarkStore  # noqa: E402

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
def player(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch, request):
    from tests.unit.docs._app_menu_bar import real_app_shell

    with real_app_shell(monkeypatch, request, "quill.apps.player", "QuillMediaPlayerFrame") as app:
        app._safe_mode = False
        said: list[str] = []
        app._announce = lambda message, **_kw: said.append(str(message))
        app.said = said
        monkeypatch.setattr(app, "_show_ai_window", lambda window: None)
        try:
            yield app
        finally:
            try:
                app._player.shutdown()
            except Exception:  # noqa: BLE001 - no engine to stop
                pass


# --------------------------------------------------------------------------- #
# The command
# --------------------------------------------------------------------------- #


def test_on_copilot_it_opens_on_the_players_tools(player, agent_window, monkeypatch) -> None:
    service = _Service("copilot", tools=True)
    monkeypatch.setattr(player, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_task())(player)

    assert service.harnesses == ["copilot"]
    hooks = agent_window.last["args"][1]
    assert hooks.title == "Find the Part Where"
    assert hooks.starter == ""
    assert "chapters, bookmarks and times" in hooks.instruction_help
    runner = hooks.make_runner(object(), SimpleNamespace(on_ui=lambda fn, default=None: fn()))
    assert runner.spec is FIND_THE_PART
    assert runner.context() == "Nothing is open."
    assert [tool.name for tool in runner.tools()] == [
        "player.where_am_i",
        "player.list_chapters",
        "player.list_bookmarks",
        "player.go_to",
    ]
    assert player.said == []


def test_on_a_connection_without_agent_tools_it_sends_nothing(
    player, agent_window, monkeypatch
) -> None:
    import quill.ui.hosted_ai_connections as connections

    service = _Service("free", tools=False)
    monkeypatch.setattr(player, "_ai_service", lambda: service)
    asked: list[str] = []
    monkeypatch.setattr(
        connections, "ask_yes_no", lambda _p, sentence, **_kw: asked.append(sentence) or False
    )

    (lambda w: w.cmd_ai_task())(player)

    assert asked and asked[0].startswith("Agent tasks need a connection that runs tasks.")
    assert agent_window.last is None
    assert service.harnesses == []


def test_safe_mode_refuses_it(player, agent_window, monkeypatch) -> None:
    monkeypatch.setattr(player, "_ai_service", lambda: _Service("copilot", tools=True))
    player._safe_mode = True

    (lambda w: w.cmd_ai_task())(player)

    assert agent_window.last is None
    assert any("Safe Mode" in said for said in player.said)


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
    def on_ui(self, fn, default=None):
        return fn()

    def preview(self, title: str, text: str) -> bool:
        raise AssertionError("moving the place asks; it has no text to preview")

    def note(self, text: str) -> None:
        pass


class _Engine:
    def __init__(self) -> None:
        self.position = 720_000
        self.sought: list[int] = []

    def playhead_ms(self) -> int:
        return self.position

    def length_ms(self) -> int:
        return 4_000_000

    def current_chapter_index(self) -> int:
        return 1

    def seek_to(self, ms: int) -> None:
        self.sought.append(ms)
        self.position = ms


@pytest.fixture
def host(tmp_path: Path):
    key = "book-key"
    marks = BookmarkStore(tmp_path / "bookmarks.json")
    marks.add(key, 3_750_000, note="the map in the chest")
    titles = (("The Old Sea-dog", 0), ("Black Dog Appears", 600_000), ("The Storm", 1_100_000))
    chapters = [SimpleNamespace(title=t, start_ms=s) for t, s in titles]
    return SimpleNamespace(
        _book_key=key,
        _book_path=tmp_path / "Treasure Island.m4b",
        _chapters=chapters,
        _chapter_nodes=[(c.title, ("seek", c.start_ms), 1) for c in chapters],
        _now_playing=SimpleNamespace(GetValue=lambda: "Treasure Island"),
        _player=_Engine(),
        _bookmarks=marks,
    )


def _registry(host: Any, approver: _Approver) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(),
        ActivityLog(),
        AgentIdentity("player-find-the-part", RiskLevel.LOW),
        app_scope=APP,
    )
    registry.register_app(APP, player_task_tools(host, _Ctx()))
    registry.gate.begin_task(approver)
    return registry


def test_the_reads_answer_as_text_without_asking(host) -> None:
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(host, approver)

    where = registry.call("player_where_am_i", {})
    chapters = registry.call("player_list_chapters", {})
    marks = registry.call("player_list_bookmarks", {})

    assert where.text.splitlines() == [
        "Open: Treasure Island",
        "Place: 0:12:00",
        "Length: 1:06:40",
        "Chapter: 2 of 3, Black Dog Appears",
    ]
    assert chapters.text.splitlines() == [
        "3 chapters:",
        "C1. The Old Sea-dog at 0:00:00",
        "C2. Black Dog Appears at 0:10:00",
        "C3. The Storm at 0:18:20",
    ]
    assert marks.text.splitlines() == ["1 bookmark:", "B1. 1:02:30: the map in the chest"]
    assert approver.asked == []


def test_go_to_asks_with_the_time_and_title_then_seeks(host) -> None:
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _registry(host, approver)

    result = registry.call("player_go_to", {"position": "1:02:30"})

    assert approver.asked == ["Go to 1:02:30 in Treasure Island."]
    assert result.ok and result.text.startswith("Jumped to 1 hour 2 minutes 30 seconds")
    assert host._player.sought == [3_750_000]
    assert registry.mutated()


def test_go_to_a_chapter_or_bookmark_names_it_in_the_question(host) -> None:
    approver = _Approver(ApprovalChoice.TASK)
    registry = _registry(host, approver)

    registry.call("player_go_to", {"position": "C3"})
    registry.call("player_go_to", {"position": "B1"})

    assert approver.asked == [
        "Go to 0:18:20 (chapter 3, The Storm) in Treasure Island.",
    ]  # Allow for this task asks once
    assert host._player.sought == [1_100_000, 3_750_000]


def test_go_to_refused_does_not_move(host) -> None:
    registry = _registry(host, _Approver(ApprovalChoice.DENY))

    result = registry.call("player_go_to", {"position": "0:30:00"})

    assert not result.ok
    assert host._player.sought == []


def test_bad_places_and_nothing_open_are_explained(host) -> None:
    registry = _registry(host, _Approver(ApprovalChoice.TASK))

    bad = registry.call("player_go_to", {"position": "soon"})
    missing = registry.call("player_go_to", {"position": "C9"})
    host._book_key, host._book_path = "", None
    closed = registry.call("player_where_am_i", {})

    assert not bad.ok and "1:02:30" in bad.text
    assert not missing.ok and "player_list_chapters" in missing.text
    assert not closed.ok and closed.text.startswith("No book or file is open.")
    assert host._player.sought == []
