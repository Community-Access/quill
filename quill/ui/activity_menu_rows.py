"""Help > Activity... and Help > Repeat Last Result, for an app without the support rows.

Every app on the shell registers the two commands (qc.md F-10), and the shell
falls back to the family keys, F9 and Shift+F9. But an app reaches a command
only through a menu row: Quill Inkwell had none, so the results it kept were in
Activity with no way in. These are the same two commands
:func:`quill.ui.support_menu.append_support_items` gives the apps that carry
the full set, for an app that wants these two alone; Repeat Last Result takes R
here because Inkwell's Check for Updates already owns U (FUX-04: after missing the
spoken result, the same result remains reachable).
"""

from __future__ import annotations

from typing import Any

__all__ = ["append_activity_rows"]


def append_activity_rows(host: Any, help_menu: Any) -> tuple[Any, Any]:
    """Append the two rows to *help_menu*, bound to *host*; the id refs, pinned."""
    import wx

    activity_id, repeat_id = wx.NewIdRef(), wx.NewIdRef()
    help_menu.Append(activity_id, host._menu_label("Activit&y...", "app.activity"))
    help_menu.Append(repeat_id, host._menu_label("&Repeat Last Result", "app.repeat_last_result"))
    host.frame.Bind(wx.EVT_MENU, lambda _e: host.open_activity(), id=activity_id)
    host.frame.Bind(wx.EVT_MENU, lambda _e: host.repeat_last_result(), id=repeat_id)
    keep = getattr(host, "_keep_menu_ids", None)
    if callable(keep):
        keep(activity_id, repeat_id)
    return activity_id, repeat_id
