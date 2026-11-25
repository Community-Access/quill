"""Small shared import surface for release-channel menu rows."""

from __future__ import annotations

from typing import Any


def append(host: Any, help_menu: Any, app_key: str, check_menu_id: Any) -> Any:
    from quill.ui.updates.shell import append_release_channel_item

    return append_release_channel_item(host, help_menu, app_key, check_menu_id)


__all__ = ["append"]
