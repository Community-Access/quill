"""Reopen Last Results in the Find Streams window (wx).

A mixin for :class:`quill.ui.radio.link_finder_dialog.LinkFinderDialog`, kept
apart under GATE-11. The saving, the rules and the sentences are
:mod:`quill.core.radio.last_results`; this is the part that touches the window:

* when the window opens with saved results, the **Reopen Last Results** button is
  enabled and one sentence offers them (it is said after the window's own
  reading, so it is not cut off);
* **Reopen Last Results** fills the list as it was: the same streams, the same
  sort order and filter, focus on the row that had it. Nothing is scanned and
  nothing plays;
* a scan that finds streams replaces the saved results, and one that finds
  nothing clears them (a New Search clears them); and
* closing the window keeps the filter, the order and the current row.

Saved results that are missing or damaged are ignored without a word.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import find_streams_view as view
from quill.core.radio import last_results as store

NOTHING_SAVED = "There are no saved results to reopen."


def _directory() -> Any:
    from quill.core.paths import app_data_dir

    return app_data_dir()


class LastResultsMixin:
    """Remember, offer and reopen the last scan's results."""

    _last: store.LastResults | None = None

    def _load_last(self) -> None:
        self._last = store.load(_directory())
        self._reopen_btn.Enable(self._last is not None)

    def _offer_last(self) -> None:
        """Say that results are waiting, after the window has been read."""
        if self._last is not None:
            self._wx.CallAfter(self._announce, store.offer_sentence(self._last))

    def _remember_last(self) -> None:
        """Save what is shown now: after a scan, and again when the window closes."""
        if not self._candidates:
            return
        focused = self._list.focused()
        self._last = store.LastResults(
            page_url=self._page_url,
            candidates=list(self._candidates),
            page_title=self._page_title,
            favicon_url=self._favicon_url,
            order=self._state.order,
            format=self._state.format,
            live_only=self._state.live_only,
            current=focused.url if focused else "",
        )
        store.save(_directory(), self._last)

    def _forget_last(self) -> None:
        """A New Search that found nothing: the old results no longer apply."""
        self._last = None
        store.clear(_directory())
        self._reopen_btn.Enable(False)

    def _on_reopen_last(self, _event: object = None) -> None:
        last = self._last
        if last is None or self._scanning:
            self._announce(NOTHING_SAVED if last is None else "A scan is still running.")
            return
        self._candidates = list(last.candidates)
        self._rows = view.distinct_rows(self._candidates)
        state = last.state
        if not view.visible(self._candidates, state):
            state = view.ViewState(order=state.order)
        self._state = state
        self._page_url = last.page_url
        self._page_title = last.page_title
        self._favicon_url = last.favicon_url
        self._url_ctrl.ChangeValue(last.page_url)
        sentence = store.reopened_sentence(last)
        self._status.SetLabel(sentence)
        self._refill(sentence, keep=last.current, keep_selected=False, show=False)
