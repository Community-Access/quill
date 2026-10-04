"""One way to change a status line in QUILL Cast: set it, and say it (qc.md P4).

A status label is silent. A screen reader does not read a ``wx.StaticText``
when its text changes, so every "the button did nothing" report in Cast's
history was a status line that changed where nobody could hear it: a Find
that failed, a feed that could not be followed, a sign-in that was needed.

:func:`say_status` is the only sanctioned way to write one (GATE-CAST-SILENT,
``quill/tools/check_cast_silence.py``): it sets the label and speaks the new
text once, when it actually changed. Clearing a line is silent, and so is a
line the caller explicitly marks ``speak=False`` -- for a progress count that
has its own paced announcement, or a line whose words the caller speaks itself
in a fuller sentence. Either way the decision is written at the call site,
where a reviewer can see it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["say_status"]


def say_status(
    label: Any,
    text: str,
    announce: Callable[[str], Any] | None = None,
    *,
    speak: bool = True,
) -> str:
    """Set *label* to *text*; speak it once when it changed. Returns *text*.

    A destroyed control (the window closed while background work finished) is
    not an error: the words are still spoken, because the outcome happened
    whether or not its window is still there to show it.
    """
    try:
        reader = getattr(label, "GetLabel", None)
        before = str(reader()) if callable(reader) else ""
        label.SetLabel(text)
    except RuntimeError:
        before = ""
    if speak and text and text != before and announce is not None:
        try:
            announce(text)
        except Exception:  # noqa: BLE001 - speech must never break the action
            pass
    return text
