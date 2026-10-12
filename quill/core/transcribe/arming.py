"""Starting from the tray or the window: wait for the field, then start there.

The start and stop key is pressed *in* the field you want, so dictation starts
there at once. The tray menu and the window's Start button are different: when
you choose them, QUILL Transcribe (or the taskbar) has the focus, and the one
field it must never type into is its own. So those two **arm** dictation: it
starts the moment you are back in another program, in whatever field has the
focus there, and only if that field passes the same checks as any other start.

What counts as "back": a window of another process that is not part of the
Windows shell -- the taskbar, the notification area, the desktop, a menu --
because those come forward on the way back and are never a place to type.

Arming gives up after :data:`ARM_SECONDS`, and says so, so a microphone is
never opened long after the person stopped expecting it.

wx-free.
"""

from __future__ import annotations

__all__ = ["ARM_SECONDS", "SHELL_CLASSES", "ready_to_start"]

#: How long an armed start waits for another program to come forward.
ARM_SECONDS = 20.0

#: Window classes of the Windows shell: on the way back, never a destination.
SHELL_CLASSES: frozenset[str] = frozenset({
    "shell_traywnd",
    "shell_secondarytraywnd",
    "notifyiconoverflowwindow",
    "toplevelwindowforoverflowxamlisland",
    "progman",
    "workerw",
    "#32768",
    "windows.ui.core.corewindow",
    "xaml_windowedpopupclass",
})


def ready_to_start(*, hwnd: int, process_id: int, window_class: str, own_process: int) -> bool:
    """Whether the window in front is somewhere an armed start may begin."""
    if not hwnd or process_id == own_process:
        return False
    return window_class.strip().lower() not in SHELL_CLASSES
