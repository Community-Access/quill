"""Beacon's results list stays still while it refills (FUX-06).

The results list is virtual: it holds row numbers, not beacons. When a capture
from the browser, a sync or an action refilled it, the native selection stayed
on the old row *number* -- now somebody else's beacon -- while the details
showed row 0, so Delete, Rename or Enter could act on a beacon the reader never
chose. And every refill said the count again, once a minute under auto-sync.

Now the reader stays on their own beacon by identity, with the rest of a
multiple selection, on the same line of the screen, and the details follow
it. The count is said when the reader changed what is shown (the search, the
sort, the destination), not when the list changed under them. A beacon that
left because of a sync is said once, after the screen reader has read the
beacon that took its place.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.list_follow import gone_sentence, land
from quill.ui.list_stay_still import capture_report, restore_report, say_when_settled
from quill.ui.list_stay_still import selected_rows as _selected_rows

__all__ = ["show", "say_with"]


def show(frame: Any, results: list[Any], *, say_count: bool, filtered: bool) -> str:
    """Put *results* in the list, keeping the reader on their beacon.

    Returns the sentence to add when the reader's beacon has gone ("" when it
    has not): the caller says it with its own news, once, after the screen
    reader has read the beacon the reader landed on.
    """
    control = frame.results
    old = list(frame._results_cache)
    old_keys = [b.beacon_id for b in old]
    anchor = capture_report(control)
    reader = old[anchor.index] if 0 <= anchor.index < len(old) else None
    others = [old_keys[row] for row in _selected_rows(control) if row < len(old_keys)]
    frame._results_cache = results
    gone = ""
    frame._following = True  # the selection events below are not the reader's
    try:
        control.SetItemCount(len(results))
        if results:
            control.RefreshItems(0, len(results) - 1)
        shown = results[0] if results else None
        if reader is not None and results:
            keys = [b.beacon_id for b in results]
            landing = land(keys, reader.beacon_id, anchor.index)
            index = landing.index
            if not landing.kept and say_count:
                index = 0  # a new search: the old row number means nothing now
            also = [keys.index(key) for key in others if key in keys]
            restore_report(wx, control, anchor, index, also=also)
            shown = results[index]
            if not landing.kept:
                gone = gone_sentence(reader.title or "")
                _refocus(control, index)
    finally:
        frame._following = False
    if say_count:
        frame.announcer.announce_count(len(results), filtered=filtered)
    if shown is not None:
        frame._show_details(shown)
    return gone


def _refocus(control: Any, index: int) -> None:
    """Tell the screen reader the row it is on now holds another beacon.

    A virtual list's row number may not change when the next beacon slides up
    into it, so no event would fire and the screen reader and the braille
    display would go on showing the beacon that left. Taking the focus state
    off the row and putting it back makes them read the row again.
    """
    focused = wx.LIST_STATE_FOCUSED
    control.SetItemState(index, 0, focused)
    control.SetItemState(index, focused, focused)


def say_with(frame: Any, news: str, gone: str, **say: Any) -> None:
    """Say *news* and the gone sentence as one, after the row has been read."""
    text = f"{news} {gone}".strip()
    if not text:
        return
    say_when_settled(wx, frame.results, lambda words: frame.announcer.say(words, **say), text)
