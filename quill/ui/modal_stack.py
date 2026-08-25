"""Which window a message box belongs to, when a dialog is already open.

**"Show Notes leaves focus in an odd state"** (reported 2026-08-25, against the
ACB Media Schedule). wxMSW hands focus back to a message box's *parent* when
the box closes. Both hosts got that parent wrong in the same way and for the
same reason: ``AppShellFrame`` passed ``self.frame`` unconditionally and
``MainFrame`` passed nothing at all, so a box raised from inside a modal dialog
returned the listener to the main window -- while the dialog they were working
in was still open in front of them. Nothing was broken, which is what made it
hard to describe; the focus had simply gone somewhere nobody asked it to go.

The fix is not per-message-box. Every modal in this app goes through one funnel
(``_show_modal_dialog``), so the funnel can record what is on screen and the
message box can ask. That fixes every existing caller at once and, more to the
point, every future one -- a new dialog that shows a message box inherits the
right answer without its author having to know this rule exists.

A **stack**, not a single slot: a dialog can open a dialog, and a box raised
from the inner one belongs to the inner one.

wx-free by design (it only ever holds and returns opaque window objects), so
the rule is testable without a display.
"""

from __future__ import annotations

from typing import Any


class ModalStack:
    """The modal dialogs on screen, outermost first."""

    __slots__ = ("_windows",)

    def __init__(self) -> None:
        self._windows: list[Any] = []

    def push(self, dialog: Any) -> None:
        self._windows.append(dialog)

    def pop(self, dialog: Any) -> None:
        """Remove *dialog* if it is on top.

        Guarded rather than unconditional: callers pop in a ``finally``, and a
        dialog that raised on the way up may never have been the top one. A pop
        that removed somebody else's entry would leave later message boxes
        parented to a destroyed window, which is worse than the bug this
        module fixes.
        """
        if self._windows and self._windows[-1] is dialog:
            self._windows.pop()

    def top(self) -> Any:
        """The innermost dialog still alive, or ``None``.

        Walks outward past any dead entry: a destroyed wx window is falsy, and
        parenting to one is how a fix for a focus bug becomes a crash.
        """
        for candidate in reversed(self._windows):
            try:
                if candidate:
                    return candidate
            except Exception:  # noqa: BLE001 - a half-torn-down window is not a parent
                continue
        return None

    def parent_for(self, explicit: Any = None, *, fallback: Any = None) -> Any:
        """The window a message box should belong to.

        *explicit* wins when a caller names one -- the default follows the
        stack rather than ignoring it, which is the whole change.
        """
        if explicit is not None:
            return explicit
        found = self.top()
        return fallback if found is None else found

    def __len__(self) -> int:
        return len(self._windows)


def stack_of(host: Any) -> ModalStack:
    """*host*'s modal stack, created on first use.

    Never assumes ``__init__`` ran. ``MainFrame`` is large enough to have
    partial-construction paths -- Safe Mode, crash recovery, and the tests that
    exercise one method on a bare instance -- and a focus fix that turns those
    into ``AttributeError`` is not a fix. One mechanism, so there is no second
    place that can forget to create it.
    """
    stack = getattr(host, "_modal_stack", None)
    if not isinstance(stack, ModalStack):
        stack = ModalStack()
        host._modal_stack = stack
    return stack


def parent_window(host: Any) -> Any:
    """The window a dialog opened by *host* should belong to.

    For the helper modules that open a ``wx.FileDialog`` / ``TextEntryDialog``
    / ``SingleChoiceDialog`` of their own. They all used to hardcode
    ``host.frame``, which is right only while the verb is offered from the main
    window -- and each of them is one menu item away from being offered from a
    dialog instead, at which point they reproduce the Show Notes focus bug
    without anybody touching them. Asking the host is correct wherever the verb
    is reached from.

    Defensive about the protocol: a host without ``_dialog_parent`` (a test
    double, an embedded caller) still gets its frame rather than a crash.
    """
    resolver = getattr(host, "_dialog_parent", None)
    if callable(resolver):
        try:
            return resolver()
        except Exception:  # noqa: BLE001 - a parent lookup must never break a verb
            pass
    return getattr(host, "frame", None)


__all__ = ["ModalStack", "parent_window"]
