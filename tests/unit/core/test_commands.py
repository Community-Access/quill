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


# -- set_title (a toggle whose state belongs in its palette label, #1383) ------


def test_set_title_renames_in_place_and_keeps_the_handler() -> None:
    registry = CommandRegistry()
    calls: list[str] = []
    registry.register(
        "test.toggle", "Toggle (currently Off)", lambda: calls.append("ran"), "Ctrl+T"
    )

    assert registry.set_title("test.toggle", "Toggle (currently On)") is True

    command = registry.get("test.toggle")
    assert command is not None
    assert command.title == "Toggle (currently On)"
    # A rename must not redefine the command.
    assert command.keybinding == "Ctrl+T"
    registry.run("test.toggle")
    assert calls == ["ran"]


def test_set_title_reports_an_unknown_command_rather_than_creating_one() -> None:
    registry = CommandRegistry()
    assert registry.set_title("test.absent", "Anything") is False
    assert registry.get("test.absent") is None


# -- availability probe (error specificity: say WHY a command cannot run) ------


def test_unavailable_reason_defaults_to_empty() -> None:
    registry = CommandRegistry()
    registry.register("test.cmd", "Test", lambda: None)
    assert registry.unavailable_reason("test.cmd") == ""


def test_unavailable_reason_reports_the_probe_sentence() -> None:
    registry = CommandRegistry()
    registry.register("test.cmd", "Test", lambda: None)
    registry.set_availability_probe(
        lambda cid: "Turned off by a safety update: bad release." if cid == "test.cmd" else ""
    )
    assert registry.unavailable_reason("test.cmd") == (
        "Turned off by a safety update: bad release."
    )


def test_unavailable_reason_is_empty_for_unknown_commands_and_probe_errors() -> None:
    registry = CommandRegistry()
    registry.register("test.cmd", "Test", lambda: None)

    def _boom(_cid: str) -> str:
        raise RuntimeError("probe exploded")

    registry.set_availability_probe(_boom)
    assert registry.unavailable_reason("test.cmd") == ""
    assert registry.unavailable_reason("test.missing") == ""
