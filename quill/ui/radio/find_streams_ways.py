"""Other ways to find a stream, in the Find Streams window (wx).

A mixin for :class:`quill.ui.radio.link_finder_dialog.LinkFinderDialog`, kept
apart under GATE-11. The order and the sentences are
:mod:`quill.core.radio.find_fallback`; this is the part that touches the window:

* a name typed in the address box is looked up in the public directories
  instead of being sent to the website scanner;
* when that name is one of the recent websites, it asks first whether to check
  that site again (Yes scans it, No looks the name up);
* the setting ``find_streams_fallback`` (off by default) lets a website with no
  stream fall back to the directories, and the result says which way found it.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import find_fallback as fb
from quill.core.radio import find_fallback_io as io

LOOKING_UP = "Looking up {name} in the public directories and checking what it finds..."


class WaysMixin:
    """Choosing the way Find Streams looks, and saying which one found it."""

    def _fallback_on(self) -> bool:
        history = getattr(self._host, "_radio_history", None)
        return bool(getattr(history, "find_streams_fallback", False))

    def _recent_sites(self) -> tuple[str, ...]:
        history = getattr(self._host, "_radio_history", None)
        return tuple(getattr(history, "recent_websites", ()) or ())

    def _ask_recheck(self, site: str) -> bool:
        """Offer to check a matching recent website again. No is the way on."""
        from quill.ui import modal_stack
        from quill.ui.dialog_contract import show_modal_dialog

        title = "Check a recent website again"
        dialog = self._wx.MessageDialog(
            modal_stack.parent_window(self._host),
            f"{site} is one of your recent websites. Check it again?",
            title,
            self._wx.YES_NO | self._wx.YES_DEFAULT | self._wx.ICON_QUESTION,
        )
        try:
            return bool(show_modal_dialog(dialog, title) == self._wx.ID_YES)
        finally:
            dialog.Destroy()

    def _what_to_look_up(self, typed: str) -> str:
        """The text to run: a matching recent website when the listener says yes."""
        if fb.typed_kind(typed) == "name":
            site = fb.matching_recent_site(typed, self._recent_sites())
            if site and self._ask_recheck(site):
                self._url_ctrl.ChangeValue(site)
                return site
        return typed

    def _run_ways(self, typed: str, on_checked: Any) -> io.FoundResult:
        return io.find(
            typed,
            safe_mode=self._safe_mode,
            fallback=self._fallback_on(),
            on_checked=on_checked,
        )
