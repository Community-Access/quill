"""The Run Agent menu/commands are wired in by default (off the experimental flag)."""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.ai.agent_catalog import load_catalog
from quill.ui.agent_editor_host import (
    append_agent_menu,
    append_experimental_agent_menu,
    register_agent_commands,
    register_experimental_agent_command,
    run_agent,
)

_AGENT_COUNT = len(load_catalog().agents)


class _FakeMenu:
    def __init__(self) -> None:
        self.items: list[tuple[int, str, str | None]] = []
        self.separators = 0
        self.submenus: list[tuple[object, str]] = []

    def Append(self, item_id: int, label: str, help: str | None = None) -> None:
        self.items.append((item_id, label, help))

    def AppendSeparator(self) -> None:
        self.separators += 1

    def AppendSubMenu(self, submenu: object, label: str) -> None:
        self.submenus.append((submenu, label))


class _FakeWx:
    EVT_MENU = object()

    def __init__(self) -> None:
        self._next = 1000

    def NewIdRef(self) -> int:
        self._next += 1
        return self._next

    def Menu(self) -> _FakeMenu:
        return _FakeMenu()


@dataclass
class _FakeFrame:
    binds: list[int] = field(default_factory=list)

    def Bind(self, _evt: object, _handler: object, *, id: int) -> None:
        self.binds.append(id)


@dataclass
class _FakeCommands:
    registered: list[str] = field(default_factory=list)

    def register(self, command_id: str, title: str, fn: object, accel: object) -> None:
        self.registered.append(command_id)


@dataclass
class _FakeController:
    _wx: _FakeWx = field(default_factory=_FakeWx)
    frame: _FakeFrame = field(default_factory=_FakeFrame)
    commands: _FakeCommands = field(default_factory=_FakeCommands)
    statuses: list[str] = field(default_factory=list)
    _safe_mode: bool = False

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)


def test_append_agent_menu_lists_every_agent() -> None:
    controller = _FakeController()
    ai_menu = _FakeMenu()
    append_agent_menu(controller, ai_menu)

    # One submenu titled "Run Agent" hung off the AI menu.
    assert len(ai_menu.submenus) == 1
    submenu, label = ai_menu.submenus[0]
    assert "Run" in str(label) and "Agent" in str(label)
    # Every catalog agent is an item, each with an event binding.
    assert len(submenu.items) == _AGENT_COUNT >= 15
    assert len(controller.frame.binds) == _AGENT_COUNT
    # Items carry the agent description as help text for screen readers.
    assert all(help_text for _id, _label, help_text in submenu.items)


def test_register_agent_commands_covers_quick_plus_every_agent() -> None:
    controller = _FakeController()
    register_agent_commands(controller)
    assert "tools.run_agent" in controller.commands.registered
    # One palette command per agent, namespaced.
    per_agent = [c for c in controller.commands.registered if c.startswith("tools.run_agent.")]
    assert len(per_agent) == _AGENT_COUNT


def test_experimental_names_are_back_compat_aliases() -> None:
    assert append_experimental_agent_menu is append_agent_menu
    assert register_experimental_agent_command is register_agent_commands


def test_run_agent_refuses_in_safe_mode() -> None:
    controller = _FakeController(_safe_mode=True)
    run_agent(controller, "writing-companion")
    assert controller.statuses == ["Agents are unavailable in safe mode."]
