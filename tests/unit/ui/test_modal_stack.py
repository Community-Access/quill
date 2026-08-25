"""A message box belongs to the dialog it was raised from.

Reported 2026-08-25: *"if you select show details on the community schedule
that after closing the dialog with the ok button the focus is left in an odd
state."*

wxMSW hands focus back to a message box's **parent** when the box closes. Both
hosts named the wrong one, in the same way and for the same reason:
``AppShellFrame`` passed ``self.frame`` unconditionally, ``MainFrame`` passed
no parent at all. So a box raised from inside a modal dialog returned the
listener to the main window while the dialog they were working in was still
open in front of them -- nothing crashed, nothing said anything, the focus had
simply gone somewhere nobody asked it to go, which is exactly why it was hard
to describe.

These cover the rule rather than any one message box, because the fix is in the
modal funnel every dialog already goes through.
"""

from __future__ import annotations

from pathlib import Path

from quill.ui.modal_stack import ModalStack, parent_window

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"


class _Win:
    """A stand-in wx window. Falsy once destroyed, as wx's own are."""

    def __init__(self, name: str, alive: bool = True) -> None:
        self.name, self.alive = name, alive

    def __bool__(self) -> bool:
        return self.alive

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return self.name


def test_with_nothing_open_a_box_belongs_to_the_frame() -> None:
    assert ModalStack().parent_for(fallback=_Win("frame")).name == "frame"


def test_with_a_dialog_open_the_box_belongs_to_the_dialog() -> None:
    """The whole of the reported bug."""
    stack = ModalStack()
    stack.push(_Win("schedule"))

    assert stack.parent_for(fallback=_Win("frame")).name == "schedule"


def test_a_dialog_over_a_dialog_owns_the_box() -> None:
    """A stack, not a single slot: the innermost one raised it."""
    stack = ModalStack()
    stack.push(_Win("schedule"))
    stack.push(_Win("confirm"))

    assert stack.parent_for(fallback=_Win("frame")).name == "confirm"


def test_closing_the_inner_dialog_hands_ownership_back() -> None:
    stack = ModalStack()
    schedule, confirm = _Win("schedule"), _Win("confirm")
    stack.push(schedule)
    stack.push(confirm)
    stack.pop(confirm)

    assert stack.parent_for(fallback=_Win("frame")).name == "schedule"


def test_a_caller_that_names_a_parent_still_wins() -> None:
    stack = ModalStack()
    stack.push(_Win("schedule"))

    assert stack.parent_for(_Win("named"), fallback=_Win("frame")).name == "named"


def test_a_destroyed_dialog_is_never_used_as_a_parent() -> None:
    """A fix for a focus bug must not become a crash.

    Parenting to a destroyed wx window raises; the stack walks outward past
    anything that has gone.
    """
    stack = ModalStack()
    stack.push(_Win("gone", alive=False))

    assert stack.parent_for(fallback=_Win("frame")).name == "frame"


def test_popping_a_dialog_that_is_not_on_top_leaves_the_stack_alone() -> None:
    """Callers pop in a ``finally``, and a dialog that raised on the way up may
    never have been the top one. Removing somebody else's entry would leave
    later boxes parented to a destroyed window."""
    stack = ModalStack()
    outer, inner = _Win("outer"), _Win("inner")
    stack.push(outer)
    stack.push(inner)
    stack.pop(outer)  # not on top

    assert len(stack) == 2
    assert stack.parent_for(fallback=_Win("frame")).name == "inner"


def test_a_host_without_the_protocol_still_gets_its_frame() -> None:
    """parent_window is used by helper modules that may be handed a test
    double or an embedded caller."""

    class _Bare:
        frame = _Win("frame")

    assert parent_window(_Bare()).name == "frame"
    assert parent_window(object()) is None


def test_a_host_resolver_that_raises_falls_back_rather_than_breaking_the_verb() -> None:
    class _Broken:
        frame = _Win("frame")

        def _dialog_parent(self) -> object:
            raise RuntimeError("half torn down")

    assert parent_window(_Broken()).name == "frame"


# -- the wiring, so the rule cannot be true only in this file -----------------


def test_both_hosts_route_their_message_boxes_through_the_stack() -> None:
    shell = (_UI / "app_shell.py").read_text(encoding="utf-8")
    main = (_UI / "main_frame.py").read_text(encoding="utf-8")

    for src, name in ((shell, "app_shell"), (main, "main_frame")):
        # stack_of, not a plain attribute: MainFrame has partial-construction
        # paths (Safe Mode, crash recovery) where __init__ never ran, and a
        # focus fix that turns those into AttributeError is not a fix.
        assert "modal_stack.stack_of(self)" in src, name
        assert "stack.push(dialog)" in src, name
        assert "stack.pop(dialog)" in src, name
        assert "self._dialog_parent(parent)" in src, name
    # app_shell used to hand wx the frame no matter what was open over it.
    assert "message, caption, style, self.frame" not in shell


def test_the_helpers_that_open_their_own_dialogs_ask_the_host() -> None:
    """They hardcoded host.frame, which is right only while the verb is offered
    from the main window -- one menu item away from the same bug."""
    for name in ("output_device_ui.py", "playlist_export_ui.py", "youtube_ui.py"):
        src = (_UI / "radio" / name).read_text(encoding="utf-8")
        assert "modal_stack.parent_window(" in src, name
