"""The Command Key's host inside a Workbench window (command-key.md 13.12, 16.4).

The editor, QUILL Lite and Quill Radio each answer the Command Key's four
questions in :mod:`quill.ui.command_key_hosts`. A Workbench window is not any
of them: it has its own menu bar, its own keys and its own dispatcher, and
F11 in it must run *its* commands, not the editor's. This is its answer, the
same for the GitHub and the WordPress Workbench, because both are a
:class:`~quill.ui.workbench_frame.WorkbenchFrame` over a provider.

- **Which registry:** :class:`WorkbenchRegistry`, a view of the window's menu
  bar. ``run`` is ``frame.run``, the dispatcher every menu row, key and
  context-menu row reaches, so a sentence passes the same write gate (the
  account's level, Safe Mode) and the same previews as the menu.
- **How it speaks:** the frame's own voice, so F9 says it again.
- **How it shows a modal:** the dialog contract, which keeps the editor usable.
- **What is switched off here:** the frame's own answer: a command the window
  greys on its menu is one the Command Key will not run, with the same reason.

The catalogue rows are :mod:`quill.core.command_catalogue.workbench`. Requests
are matched on this computer: the Jev and own-AI assists read a catalogue the
gateway holds, which has no Workbench rows yet, so nothing typed here leaves
the computer. Both editors open the same windows, so QUILL and QUILL Lite get
this together.
"""

from __future__ import annotations

from typing import Any

from quill.core.command_catalogue import rows_for_app

__all__ = [
    "WorkbenchRegistry",
    "workbench_app",
    "workbench_command_key",
    "workbench_what_can_i_say_here",
]

#: The provider's keymap id is its catalogue app (both are the window's name).
_APPS = frozenset({"github_workbench", "wordpress_workbench"})


def workbench_app(frame: Any) -> str:
    """The catalogue app for this Workbench window ("" for one with no rows)."""
    app = str(getattr(frame.provider, "keymap_id", "") or "")
    return app if app in _APPS else ""


class WorkbenchRegistry:
    """The window's commands, as the Command Key's policy asks about them."""

    def __init__(self, frame: Any) -> None:
        from quill.core.workbench.menus import all_rows

        self._frame = frame
        self._ids = frozenset(row.command_id for _menu, row in all_rows(frame.provider.menu))
        self._repeat = 1

    def get(self, command_id: str) -> str | None:
        """The id when this window has the command on its bar, else None."""
        return command_id if command_id in self._ids else None

    def unavailable_reason(self, command_id: str) -> str:
        """Why the window would grey it, or "" when it can run here now."""
        frame = self._frame
        if frame.can_run(command_id) and (
            frame.current is not None or command_id in frame.provider.go_nodes
        ):
            return ""
        return str(frame.reason(command_id))

    def keybinding_for(self, command_id: str) -> str:
        return str(getattr(self._frame, "_keys", {}).get(command_id, ""))

    def arm_repeat(self, steps: int) -> None:
        self._repeat = max(1, int(steps))

    def run(self, command_id: str) -> None:
        """The menu's own path: ``frame.run``, write gate and previews included."""
        steps, self._repeat = self._repeat, 1
        for _step in range(steps):
            self._frame.run(command_id)


def _host(frame: Any) -> Any:
    import wx

    from quill.ui.command_key_ui import WxCommandKeyHost
    from quill.ui.dialog_contract import show_modal_dialog

    registry = WorkbenchRegistry(frame)
    return WxCommandKeyHost(
        wx=wx,
        parent=frame.frame,
        app=workbench_app(frame),
        registry=registry,
        show_modal=lambda dialog, label: int(show_modal_dialog(dialog, label)),
        announce=frame._say,
        key_for=registry.keybinding_for,
    )


def workbench_command_key(frame: Any) -> None:
    """F11 in a Workbench window: say or type one of this window's commands."""
    from quill.ui.command_key_hosts import hint_shown
    from quill.ui.command_key_ui import run_command_key

    if not workbench_app(frame) or not rows_for_app(workbench_app(frame)):
        frame._say("Say or Type a Command has nothing to offer in this window yet.")
        return
    frame._command_key_session = run_command_key(
        _host(frame),
        getattr(frame, "_command_key_session", None),
        first_time=not hint_shown(),
        assist=None,  # matched on this computer only (see the module docstring)
    )


def workbench_what_can_i_say_here(frame: Any) -> None:
    """Help, What Can I Say Here (Ctrl+Alt+Shift+F1) in a Workbench window."""
    from quill.core.command_catalogue.policy import CommandKeySession

    if not workbench_app(frame):
        frame._say("Say or Type a Command has nothing to offer in this window yet.")
        return
    host = _host(frame)
    picked = host.show_help("")
    if picked is None:
        return
    session = getattr(frame, "_command_key_session", None) or CommandKeySession(host)
    session.host = host
    session.run_candidate(picked)
    frame._command_key_session = session
