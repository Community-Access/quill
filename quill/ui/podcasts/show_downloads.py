"""Show-scoped download housekeeping for Quill Cast.

Split from :mod:`show_actions` at its GATE-11 ceiling the day this was
written: the symmetric counterpart to ``download_all_episodes``, for when
the listening is done and the disk space is wanted back. Same
``(..., show, *, announce)`` shape as every sibling there.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def remove_all_downloads_prompt(
    parent: object,
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Confirm, then delete *show*'s downloaded files. Episodes, played
    state, and positions are untouched.

    Episodes marked Keep This Episode are honored and skipped, same as the
    Downloads dialog's per-show remove. Returns whether anything was removed
    (the caller saves the library on True).
    """
    import wx

    from quill.core.podcasts import retention

    downloaded = [e for e in show.episodes if e.downloaded_path]
    if not downloaded:
        announce(f"Nothing is downloaded for {show.title}")
        return False
    kept = [e for e in downloaded if retention.is_protected(library, show, e)]
    removable = [e for e in downloaded if e not in kept]
    if not removable:
        announce(
            f"All {len(downloaded)} downloaded episode(s) of {show.title} are marked "
            "Keep This Episode; nothing was removed"
        )
        return False
    suffix = f" ({len(kept)} marked Keep This Episode will stay)" if kept else ""
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
        f"Remove {len(removable)} downloaded file(s) for {show.title}?{suffix} "
        "Your episodes and played state are untouched.",
        "Remove All Downloads",
        wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        parent,
    )
    if answer != wx.YES:
        return False
    removed = sum(1 for episode in removable if retention.remove_downloaded_copy(episode))
    spoken = f"Removed {removed} downloaded file(s) for {show.title}"
    if kept:
        spoken += f"; kept {len(kept)} marked Keep This Episode"
    announce(spoken)
    return removed > 0
