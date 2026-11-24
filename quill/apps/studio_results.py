"""QUILL Studio's way back to a result it already said (FUX-04).

Studio keeps every save, export and run result in Activity (quill.core.activity),
with Open Folder. These are the two doors to it on Studio's Help menu --
**Activity...** (Shift+F9) and **Repeat Last Result** (F9), the family's keys --
and the diagnostics bundle's own result, kept here so ``studio.py`` does not
grow (GATE-11).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

__all__ = ["append_result_items", "diagnostics_saved"]


def append_result_items(host: Any, help_menu: Any) -> list[tuple[Any, Callable[[], None]]]:
    """Append Activity and Repeat Last Result to *help_menu*; their (id, handler) pairs."""
    import wx

    activity_id, repeat_id = wx.NewIdRef(), wx.NewIdRef()
    help_menu.Append(activity_id, host._menu_label("Activit&y...", "app.activity"))
    help_menu.Append(repeat_id, host._menu_label("Repeat Last Resul&t", "app.repeat_last_result"))
    return [(activity_id, host.open_activity), (repeat_id, host.repeat_last_result)]


def diagnostics_saved(host: Any, target: Path) -> None:
    """``Diagnostics bundle saved to diag.zip in Support.``, said once and kept."""
    from quill.core.action_feedback import written_result
    from quill.ui.outcome_report import report_outcome

    said = written_result("Diagnostics bundle saved", target)
    report_outcome(host, "Save Diagnostics", said, object_name=target.name, path=target)
