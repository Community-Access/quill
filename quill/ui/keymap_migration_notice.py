"""The words of the once-only "QUILL updated your settings" notice.

Moved out of :mod:`quill.ui.main_frame_keymap_io` (GATE-11) unchanged: which
sentences the notice says, in order, for what this launch migrated.
"""

from __future__ import annotations

from collections.abc import Iterable


def migration_message(
    migrated_stores: object, retired_keys: object, shortcut_summaries: Iterable[str]
) -> str:
    """The notice: settings migrated, settings retired, then each shortcut change."""
    parts: list[str] = []
    if migrated_stores:
        parts.append("QUILL updated your saved settings for this version. A backup was saved.")
    if retired_keys:
        parts.append(
            "Your editor settings were simplified; the braille fix is now on "
            "by default under Preferences > Braille."
        )
    parts.extend(shortcut_summaries)
    return " ".join(parts)
