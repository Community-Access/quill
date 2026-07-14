"""Tests for Quiet Mode and the verbosity undo stack (§9, §11)."""

from __future__ import annotations

from quill.core.verbosity.quiet import QuietMode, VerbosityUndoStack


def test_quiet_starts_inactive() -> None:
    assert not QuietMode().is_active


def test_enter_exit_announcements() -> None:
    quiet = QuietMode()
    assert quiet.enter() == "Quiet Mode on"
    assert quiet.is_active
    assert quiet.exit() == "Quiet Mode off"
    assert not quiet.is_active


def test_toggle_flips_state() -> None:
    quiet = QuietMode()
    assert quiet.toggle() == "Quiet Mode on"
    assert quiet.toggle() == "Quiet Mode off"


def test_undo_empty_stack() -> None:
    assert VerbosityUndoStack().undo() == "Nothing to undo"


def test_undo_reverses_last_transition() -> None:
    state = {"quiet": False}
    stack = VerbosityUndoStack()
    state["quiet"] = True
    stack.push("Quiet Mode on", lambda: state.__setitem__("quiet", False))
    message = stack.undo()
    assert message == "Undid Quiet Mode on"
    assert state["quiet"] is False


def test_undo_two_transitions_in_order() -> None:
    log: list[str] = []
    stack = VerbosityUndoStack()
    stack.push("first", lambda: log.append("undo-first"))
    stack.push("second", lambda: log.append("undo-second"))
    assert stack.undo() == "Undid second"
    assert stack.undo() == "Undid first"
    assert log == ["undo-second", "undo-first"]


def test_stack_bounded_to_max_entries() -> None:
    stack = VerbosityUndoStack(max_entries=2)
    for i in range(5):
        stack.push(str(i), lambda: None)
    assert stack.depth == 2
