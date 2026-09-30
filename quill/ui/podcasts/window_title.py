"""QUILL Cast's window title, and the Inbox count in it (ear.md R15).

    QUILL Cast
    QUILL Cast - Inbox (12)

**Free for the reader, and deliberately not spoken.** A window title is
something a screen reader announces on arrival and on every Alt+Tab back,
without being asked -- so putting the count there gives it to the listener at
exactly the moments they are orienting, and costs nothing at any other moment.
Announcing it would be the same fact twice (GATE-13), and announcing it when it
*changes* would mean a sentence over the top of whatever they were doing every
time a feed refreshed.

The count is the Inbox as the Inbox view counts it -- ``inbox_pairs``, so caps
and Episode Filters are already applied and the title cannot disagree with the
list it is counting.

The title is dropped back to the bare app name when the Inbox is empty rather
than showing "(0)": a zero is a number somebody has to read before finding out
there is nothing to read.
"""

from __future__ import annotations

from typing import Any

__all__ = ["CastWindowTitleMixin", "compose_title", "inbox_count"]


def inbox_count(library: Any) -> int:
    """How many episodes are in the Inbox right now."""
    from quill.core.podcasts.inbox import inbox_pairs

    try:
        return len(inbox_pairs(library))
    except Exception:  # noqa: BLE001 - a title is never worth a crash
        return 0


def compose_title(app_title: str, count: int) -> str:
    """``"QUILL Cast - Inbox (12)"``, or the bare title when the Inbox is empty."""
    return f"{app_title} - Inbox ({count})" if count > 0 else app_title


class CastWindowTitleMixin:
    """One method, called wherever the library changes."""

    def _refresh_window_title(self) -> None:
        from quill.apps.podcasts_menu import APP_TITLE

        library = getattr(self, "_podcast_library", None)
        if library is None:
            return
        wanted = compose_title(APP_TITLE, inbox_count(library))
        frame = getattr(self, "frame", None)
        if frame is not None and frame.GetTitle() != wanted:
            # Only when it differs: SetTitle fires a window-name change that the
            # reader may speak, and setting the same string again would be a
            # notification that nothing happened.
            frame.SetTitle(wanted)
