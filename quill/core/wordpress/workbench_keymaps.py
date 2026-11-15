"""The Workbench windows' ``APP_KEYMAPS`` entries, gathered for one spread.

Each Workbench window owns its keys in the wx-free table that builds its menu
bar -- the GitHub Workbench in :mod:`quill.core.github.workbench_window_menu`,
the WordPress Workbench in :mod:`quill.core.wordpress.workbench_window_menu` -- so
a window's menu and its keymap cannot disagree. :mod:`quill.core.app_keymaps`
spreads :data:`WORKBENCH_KEYMAPS` once rather than importing each table.
"""

from __future__ import annotations

from quill.core.github.workbench_window_menu import WORKBENCH_KEYMAP_ID, WORKBENCH_KEYS
from quill.core.wordpress.workbench_window_menu import WORDPRESS_KEYMAP_ID, WORDPRESS_KEYS

__all__ = ["WORKBENCH_KEYMAPS"]

WORKBENCH_KEYMAPS: dict[str, dict[str, str]] = {
    WORKBENCH_KEYMAP_ID: dict(WORKBENCH_KEYS),  # the GitHub Workbench window (PRD Part C)
    WORDPRESS_KEYMAP_ID: dict(WORDPRESS_KEYS),  # the WordPress Workbench window (PRD Part C)
}
"""app id -> {command id: binding}, one entry per Workbench window."""
