import pytest

from quill.core.commands import CommandRegistry


def test_command_registry_runs_registered_command() -> None:
    registry = CommandRegistry()
    called = {"value": False}

    def handler() -> None:
        called["value"] = True

    registry.register("test.run", "Run test", handler, "Ctrl+T")
    registry.run("test.run")
    assert called["value"] is True


def test_command_registry_rejects_duplicate_ids() -> None:
    registry = CommandRegistry()
    registry.register("test.run", "Run test", lambda: None)
    with pytest.raises(ValueError):
        registry.register("test.run", "Run test duplicate", lambda: None)


def test_command_registry_raises_for_unknown_command() -> None:
    registry = CommandRegistry()
    with pytest.raises(KeyError):
        registry.run("missing.command")


def test_command_registry_notifies_run_listener() -> None:
    registry = CommandRegistry()
    called: list[str] = []
    observed: list[str] = []

    def handler() -> None:
        called.append("ran")

    registry.register("test.run", "Run test", handler)
    registry.set_run_listener(observed.append)
    registry.run("test.run")

    assert called == ["ran"]
    assert observed == ["test.run"]


def test_command_registry_clears_run_listener() -> None:
    registry = CommandRegistry()
    observed: list[str] = []
    registry.register("test.run", "Run test", lambda: None)
    registry.set_run_listener(observed.append)
    registry.set_run_listener(None)
    registry.run("test.run")
    assert observed == []


def test_try_register_returns_true_when_id_is_new() -> None:
    registry = CommandRegistry()
    assert registry.try_register("test.new", "New test", lambda: None) is True
    assert registry.get("test.new") is not None


def test_try_register_returns_false_when_id_exists_and_keeps_original() -> None:
    registry = CommandRegistry()
    calls: list[str] = []

    def first() -> None:
        calls.append("first")

    def second() -> None:
        calls.append("second")

    registry.register("test.run", "Original title", first, "Ctrl+T")
    assert registry.try_register("test.run", "Replacement title", second, "Ctrl+U") is False

    # The original registration must still be the live one.
    command = registry.get("test.run")
    assert command is not None
    assert command.title == "Original title"
    assert command.keybinding == "Ctrl+T"
    registry.run("test.run")
    assert calls == ["first"]


def test_replace_overwrites_existing_entry() -> None:
    registry = CommandRegistry()
    calls: list[str] = []

    def first() -> None:
        calls.append("first")

    def second() -> None:
        calls.append("second")

    registry.register("test.run", "Original title", first, "Ctrl+T")
    registry.replace("test.run", "Replacement title", second, "Ctrl+U")

    command = registry.get("test.run")
    assert command is not None
    assert command.title == "Replacement title"
    assert command.keybinding == "Ctrl+U"
    registry.run("test.run")
    assert calls == ["second"]


def test_replace_creates_new_entry_when_absent() -> None:
    registry = CommandRegistry()
    registry.replace("test.new", "New", lambda: None, "Ctrl+N")
    assert registry.get("test.new") is not None
