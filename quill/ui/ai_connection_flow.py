"""Preferences > AI Connection: open the connection dialog and report the outcome.

Moved out of :mod:`quill.ui.main_frame_preferences` under GATE-11 (that module
is at its ceiling, and qc.md X-01 needed room there for Find a setting). The
behaviour is unchanged: the status bar says whether the connection is ready.
"""

from __future__ import annotations

from typing import Any

__all__ = ["open_ai_connection"]


def open_ai_connection(frame: Any) -> None:
    """Run the AI connection dialog on *frame* (a ``MainFrame``)."""
    from quill.ui.assistant_tools import AssistantConnectionDialog

    dialog = AssistantConnectionDialog(frame.frame)
    if dialog.show_modal():
        frame._set_ai_menu_status_badge(
            dialog.last_verification_ok,
            dialog.last_verification_message,
        )
        detail = frame._compact_ai_status_detail(
            frame._plain_language_ai_status_detail(dialog.last_verification_message)
        )
        if dialog.last_verification_ok:
            frame._set_status(f"Updated AI connection settings. Ready. {detail}")
        else:
            frame._set_status(f"Updated AI connection settings. Needs attention. {detail}")
    else:
        frame._set_status("AI connection settings cancelled")
