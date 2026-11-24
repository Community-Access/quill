"""QUILL's Start page says how to begin, once the window is up (FUX-09).

With **Start With No Document Open** on, QUILL opens on a read-only "Start"
tab. It said "No document open. Use File > New or File > Open." on the
status bar -- while the window was still being built, so the spoken half was
lost, and it named menu paths but not the keys. Now the sentence names New
and Open by the keys they are bound to, and it is said once, shortly after
the window is shown and focus has landed on the Start tab, so the screen
reader's own focus speech does not cut it.
"""

from __future__ import annotations

from typing import Any

from quill.core.first_task import NextAction, first_task_line

__all__ = ["SAY_AFTER_MS", "say_start_page_later", "start_page_line"]

#: After the screen reader has read the focused Start tab.
SAY_AFTER_MS = 300


def start_page_line(host: Any) -> str:
    commands = getattr(host, "commands", None)

    def key_for(command_id: str) -> str:
        return str(commands.keybinding_for(command_id) or "") if commands is not None else ""

    return first_task_line(
        "No document open.",
        (
            NextAction("New", "file.new", "starts one"),
            NextAction("Open", "file.open", "opens a file"),
        ),
        key_for,
    )


def say_start_page_later(host: Any) -> None:
    """Called as the window is shown: the Start page's sentence, once, a moment later."""
    if not getattr(host, "_empty_workspace_active", False):
        return
    if getattr(host, "_start_page_said", False):
        return  # once per launch, however often the window is shown
    host._start_page_said = True

    def say() -> None:
        if getattr(host, "_empty_workspace_active", False):
            host._set_status(start_page_line(host))

    host._wx.CallLater(SAY_AFTER_MS, say)
