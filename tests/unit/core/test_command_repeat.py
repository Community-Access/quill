from __future__ import annotations

from quill.core.commands import CommandRegistry


def _registry_with_counter() -> tuple[CommandRegistry, list[str]]:
    reg = CommandRegistry()
    calls: list[str] = []
    reg.register("edit.thing", "Thing", lambda: calls.append("thing"))
    return reg, calls


def test_default_runs_once() -> None:
    reg, calls = _registry_with_counter()
    reg.run("edit.thing")
    assert calls == ["thing"]


def test_armed_repeat_multiplies_next_command_then_clears() -> None:
    reg, calls = _registry_with_counter()
    reg.arm_repeat(3)
    assert reg.pending_repeat == 3
    reg.run("edit.thing")
    assert calls == ["thing", "thing", "thing"]
    # Count is consumed; the next run is single.
    reg.run("edit.thing")
    assert calls.count("thing") == 4


def test_count_is_clamped() -> None:
    reg, _calls = _registry_with_counter()
    reg.arm_repeat(0)
    assert reg.pending_repeat == 1
    reg.arm_repeat(10_000)
    assert reg.pending_repeat == CommandRegistry.MAX_REPEAT


def test_non_repeatable_command_ignores_count() -> None:
    reg = CommandRegistry()
    calls: list[str] = []
    reg.register("edit.repeat_command", "Repeat", lambda: calls.append("arm"))
    reg.register_non_repeatable("edit.repeat_command")
    reg.arm_repeat(5)
    reg.run("edit.repeat_command")
    assert calls == ["arm"]
    assert reg.pending_repeat == 1


def test_on_run_fires_per_iteration() -> None:
    reg = CommandRegistry()
    seen: list[str] = []
    reg.set_run_listener(seen.append)
    reg.register("edit.thing", "Thing", lambda: None)
    reg.arm_repeat(2)
    reg.run("edit.thing")
    assert seen == ["edit.thing", "edit.thing"]
