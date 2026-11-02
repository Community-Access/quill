"""Find and Follow, QUILL Cast's agent task (codex.md 6.5, Phase 4c).

Two halves. The command, called for real on a real QUILL Cast window, with the
agent window patched where the shared opener imports it
(``quill.ui.agent_window``). Then every tool through a real
``FamilyToolRegistry`` over a real ``PodcastLibrary``: reads answer without a
question; following, making a folder and moving a podcast ask, show the change
as text, and change nothing when refused or not applied. The directory and the
feed are stand-ins, so nothing leaves the machine.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.family_tools import FamilyToolRegistry
from quill.core.ai.permissions import PermissionBroker, RiskLevel
from quill.core.ai.tool_gateway import AgentIdentity
from quill.core.podcasts.itunes_search import PodcastSearchResult
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.cast_ai_task import APP, FIND_AND_FOLLOW, cast_task_tools

# --------------------------------------------------------------------------- #
# The command, on a real QUILL Cast window
# --------------------------------------------------------------------------- #


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
def cast(quill_data_dir: Path, wx_app, quiet_cast_startup, close_cast, monkeypatch):
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = PodcastsAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    frame._podcast_history.ai_help_enabled = True
    monkeypatch.setattr(type(frame), "_show_ai_window", lambda self, window: None)
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        close_cast(frame)


_REAL = pytest.mark.machine_global  # a real Cast window registers global hotkeys


@_REAL
def test_on_copilot_find_and_follow_opens_on_casts_tools(cast, agent_window, monkeypatch) -> None:
    service = _Service("copilot", tools=True)
    monkeypatch.setattr(cast, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_task())(cast)

    assert service.harnesses == ["copilot"]
    hooks = agent_window.last["args"][1]
    assert hooks.title == "Find and Follow"
    assert hooks.starter == ""
    assert "follow or organise" in hooks.instruction_help
    runner = hooks.make_runner(object(), SimpleNamespace(on_ui=lambda fn, default=None: fn()))
    assert runner.spec is FIND_AND_FOLLOW
    assert isinstance(runner.context(), str)
    assert [tool.name for tool in runner.tools()] == [
        "podcasts.find_shows",
        "podcasts.list_followed",
        "podcasts.recent_episodes",
        "podcasts.follow_show",
        "podcasts.new_folder",
        "podcasts.move_to_folder",
        "podcasts.queue_episode",
    ]
    assert cast.said == []


@_REAL
def test_on_a_connection_without_agent_tools_it_sends_nothing(
    cast, agent_window, monkeypatch
) -> None:
    import quill.ui.hosted_ai_connections as connections

    service = _Service("free", tools=False)
    monkeypatch.setattr(cast, "_ai_service", lambda: service)
    asked: list[str] = []
    monkeypatch.setattr(
        connections, "ask_yes_no", lambda _p, sentence, **_kw: asked.append(sentence) or False
    )

    (lambda w: w.cmd_ai_task())(cast)

    assert asked and asked[0].startswith("Agent tasks need a connection that runs tasks.")
    assert agent_window.last is None
    assert service.harnesses == []


@_REAL
def test_safe_mode_refuses_find_and_follow(cast, agent_window, monkeypatch) -> None:
    monkeypatch.setattr(cast, "_ai_service", lambda: _Service("copilot", tools=True))
    cast._safe_mode = True

    (lambda w: w.cmd_ai_task())(cast)

    assert agent_window.last is None
    assert any("Safe Mode" in said for said in cast.said)


@_REAL
def test_the_row_is_in_ai_features_on_ctrl_f3_without_a_digit(cast) -> None:
    labels: list[str] = []
    bar = cast.frame.GetMenuBar()
    for index in range(bar.GetMenuCount()):
        for item in bar.GetMenu(index).GetMenuItems():
            if item.GetSubMenu():
                labels += [sub.GetItemLabel() for sub in item.GetSubMenu().GetMenuItems()]
    row = next(label for label in labels if label.startswith("Find and Fo&llow"))
    assert row.endswith("\tCtrl+F3")
    assert cast.commands.get("tools.hosted_ai_task") is not None


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


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    show = PodcastShow(id="s1", title="Bird Notes", feed_url="http://x.invalid/birds")
    for day in (1, 2):
        show.episodes.append(
            PodcastEpisode(
                guid=f"b{day}",
                title=f"Robins {day}",
                audio_url="http://x.invalid/a.mp3",
                published=f"2026-10-0{day}T06:00:00+00:00",
                duration_seconds=1200,
            )
        )
    library.add_show(show)
    library.add_folder("Nature")
    return library


def _host(library: PodcastLibrary | None = None) -> SimpleNamespace:
    host = SimpleNamespace(_podcast_library=library or _library(), _safe_mode=False, saved=[])
    host._save_podcast_library = lambda: host.saved.append("save")
    return host


_FOUND = SimpleNamespace(
    results=[
        PodcastSearchResult(title="Bird Notes", feed_url="http://x.invalid/birds", artist="BN"),
        PodcastSearchResult(title="Owl Hour", feed_url="http://x.invalid/owls", artist="Ann"),
    ],
    problems=[],
)


def _feed(_url: str, _safe: bool) -> Any:
    return SimpleNamespace(
        title="Owl Hour",
        homepage="",
        artwork_url="",
        tags=None,
        episodes=[
            PodcastEpisode(guid="o1", title="Barn Owls", audio_url="u", published="2026-10-03"),
            PodcastEpisode(guid="o2", title="Snowy Owls", audio_url="u", published="2026-10-04"),
        ],
    )


def _registry(host: Any, approver: _Approver, ctx: _Ctx | None = None) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(),
        ActivityLog(),
        AgentIdentity("cast-find-and-follow", RiskLevel.LOW),
        app_scope=APP,
    )
    tools = cast_task_tools(
        host, ctx or _Ctx(), search=lambda _q, _s: _FOUND, fetch=lambda u, s: _feed(u, s)
    )
    registry.register_app(APP, tools)
    registry.gate.begin_task(approver)
    return registry


def test_find_shows_lists_numbered_rows_and_says_what_is_already_followed() -> None:
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(_host(), approver)

    result = registry.call("podcasts_find_shows", {"query": "birds"})

    assert result.text.splitlines() == [
        "2 podcasts for birds:",
        "P1. Bird Notes, by BN. You already follow it.",
        "P2. Owl Hour, by Ann.",
    ]
    assert approver.asked == []


def test_followed_and_recent_episodes_are_reads() -> None:
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(_host(), approver)

    followed = registry.call("podcasts_list_followed", {})
    recent = registry.call("podcasts_recent_episodes", {"show": "F1"})

    assert followed.text.splitlines() == [
        "1 podcast followed:",
        "F1. Bird Notes. In the top level. 2 episodes not played.",
        "Folders: Nature.",
    ]
    assert recent.text.splitlines() == [
        "The newest 2 episodes of Bird Notes:",
        "E1. Robins 2. 2026-10-02. 20 minutes. not played.",
        "E2. Robins 1. 2026-10-01. 20 minutes. not played.",
    ]
    assert approver.asked == []


def test_follow_asks_shows_the_feed_and_follows_on_apply() -> None:
    host = _host()
    approver = _Approver(ApprovalChoice.ONCE)
    ctx = _Ctx(apply=True)
    registry = _registry(host, approver, ctx)
    registry.call("podcasts_find_shows", {"query": "owls"})

    result = registry.call("podcasts_follow_show", {"result": "P2"})

    assert approver.asked == ["Follow the podcast Owl Hour."]
    title, text = ctx.previews[0]
    assert title == "Follow Owl Hour"
    assert text.splitlines()[:5] == [
        "Follow: Owl Hour",
        "By: Ann",
        "Episodes in the feed: 2",
        "- Snowy Owls",
        "- Barn Owls",
    ]
    assert result.ok and result.text == "Now following Owl Hour, 2 episodes."
    assert host._podcast_library.find_show_by_feed_url("http://x.invalid/owls") is not None
    assert host.saved == ["save"]
    assert registry.mutated()


def test_follow_not_applied_follows_nothing() -> None:
    host = _host()
    ctx = _Ctx(apply=False)
    registry = _registry(host, _Approver(ApprovalChoice.ONCE), ctx)
    registry.call("podcasts_find_shows", {"query": "owls"})

    result = registry.call("podcasts_follow_show", {"result": "P2"})

    assert not result.ok and result.text == "The person did not apply it."
    assert len(host._podcast_library.shows) == 1
    assert host.saved == []


def test_follow_refused_reads_no_feed_and_shows_nothing() -> None:
    host = _host()
    ctx = _Ctx()
    registry = _registry(host, _Approver(ApprovalChoice.DENY), ctx)
    registry.call("podcasts_find_shows", {"query": "owls"})

    result = registry.call("podcasts_follow_show", {"result": "P2"})

    assert not result.ok
    assert ctx.previews == []
    assert len(host._podcast_library.shows) == 1


def test_following_a_show_already_followed_is_refused_before_any_preview() -> None:
    ctx = _Ctx()
    registry = _registry(_host(), _Approver(ApprovalChoice.TASK), ctx)
    registry.call("podcasts_find_shows", {"query": "birds"})

    result = registry.call("podcasts_follow_show", {"result": "P1"})

    assert not result.ok and result.text == "You already follow Bird Notes."
    assert ctx.previews == []


def test_new_folder_and_move_each_ask_and_show_the_change() -> None:
    host = _host()
    approver = _Approver(ApprovalChoice.ONCE)
    ctx = _Ctx(apply=True)
    registry = _registry(host, approver, ctx)

    made = registry.call("podcasts_new_folder", {"name": "Birds", "inside": "Nature"})
    moved = registry.call("podcasts_move_to_folder", {"show": "F1", "folder": "Birds"})

    assert approver.asked == [
        "Make a folder called Birds.",
        "Move Bird Notes to the folder Birds.",
    ]
    assert ctx.previews == [
        ("New folder Birds", "Make a folder: Birds\nInside: Nature"),
        ("Move Bird Notes", "Move: Bird Notes\nFrom: the top level\nTo: Birds"),
    ]
    assert made.ok and moved.ok
    library = host._podcast_library
    birds = next(f for f in library.folders if f.name == "Birds")
    assert birds.parent_folder_id == next(f.id for f in library.folders if f.name == "Nature")
    assert library.find_show("s1").folder_id == birds.id
    assert host.saved == ["save", "save"]


def test_move_not_applied_moves_nothing_and_a_missing_folder_is_explained() -> None:
    host = _host()
    registry = _registry(host, _Approver(ApprovalChoice.TASK), _Ctx(apply=False))

    refused = registry.call("podcasts_move_to_folder", {"show": "F1", "folder": "Nature"})
    missing = registry.call("podcasts_move_to_folder", {"show": "F1", "folder": "Jazz"})

    assert refused.text == "The person did not apply it."
    assert host._podcast_library.find_show("s1").folder_id is None
    assert "There is no folder called Jazz" in missing.text
    assert host.saved == []


def test_new_folder_refused_makes_nothing() -> None:
    host = _host()
    ctx = _Ctx()
    registry = _registry(host, _Approver(ApprovalChoice.DENY), ctx)

    result = registry.call("podcasts_new_folder", {"name": "Birds"})

    assert not result.ok
    assert [f.name for f in host._podcast_library.folders] == ["Nature"]
    assert ctx.previews == []


def test_queue_asks_with_the_episode_and_adds_it_once() -> None:
    host = _host()
    approver = _Approver(ApprovalChoice.TASK)
    registry = _registry(host, approver)
    registry.call("podcasts_recent_episodes", {"show": "F1"})

    first = registry.call("podcasts_queue_episode", {"episode": "E1"})
    again = registry.call("podcasts_queue_episode", {"episode": "E1"})

    assert approver.asked == ["Add Robins 2 from Bird Notes to the Play Queue."]
    assert first.ok and first.text == "Added Robins 2 to the Play Queue."
    assert not again.ok
    assert [item.episode_guid for item in host._podcast_library.queue] == ["b2"]


def test_safe_mode_finds_nothing() -> None:
    host = _host()
    host._safe_mode = True
    registry = _registry(host, _Approver(ApprovalChoice.DENY))

    result = registry.call("podcasts_find_shows", {"query": "birds"})

    assert not result.ok and result.text == "Finding podcasts is off in Safe Mode."
