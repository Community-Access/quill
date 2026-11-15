"""Self-lockout guards on a Properties save (complete.md WP-A), apart from the sheets (GATE-11).

- :func:`setting_cleared`: a site setting that would lock anyone out is
  refused with the reason; any other is previewed before it is sent.

A person's Role saved from their sheet goes through
:func:`quill.core.wordpress.workbench_people.check_role_save`, the same guard
as Change Role, inside the save's background work.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.wordpress.workbench_permissions import setting_preview, setting_refusal
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["setting_cleared"]


def setting_cleared(provider: Any, row: WbRow, body: Mapping[str, Any]) -> bool:
    """True when the setting change in *body* may be sent: not refused, and the preview accepted."""
    key = str(row.raw.get("key", ""))
    refused = setting_refusal(key, body.get(key))
    if refused:
        provider.say(refused)
        return False
    label = row.cell("setting") or key
    summary, lines = setting_preview(label, key, row.raw.get("value"), body.get(key), row.site)
    return bool(
        wdlg.ask_preview(
            provider.parent,
            provider.show_modal,
            title="Change a Setting",
            summary=summary,
            lines=lines,
            yes="Change",
        )
    )
