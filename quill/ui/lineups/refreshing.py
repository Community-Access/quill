"""Running the rules in the background, and noticing the other app's edits.

Part of the Lineups window (a mixin). Rules run when the window opens, when a
store the rules read changes (either app's), every ten minutes for the
time-based Keep choices, and on Refresh Now. The catalogue is gathered off the
UI thread and each Lineup is folded under the store's lock on the file as it is
*then*, so a move the other app made a moment ago is never undone by a refresh.

A refresh with the window in focus says what changed in one sentence, queued
through the listener's feedback setting and said *after* the cursor has moved; a
timed refresh with nothing to report says nothing; a background one never
speaks, and its arrivals show as "2 new" on the Lineup's row instead.
"""

from __future__ import annotations

from typing import Any

from quill.core.lineups import describe
from quill.core.lineups.merge import Catalogue, RefreshResult
from quill.core.lineups.ops import apply_refresh

#: How often time-based Keep choices are re-checked while the window is open.
TIMED_REFRESH_SECONDS = 600.0


class LineupsRefreshMixin:
    """``request_refresh`` and the window's tick."""

    _lineups_host: Any
    _store: Any
    _book: Any
    _win: Any
    _new: dict[str, int]
    _refreshing: bool
    _refresh_again: bool | None
    _catalogue: Catalogue | None
    _stamp: tuple[int, int]
    _source_stamps: tuple[tuple[int, int], ...]
    _last_timed: float

    # -- refreshing ------------------------------------------------------------------------

    def request_refresh(self, *, speak: bool) -> None:
        """Run every rule in the background. *speak*: answer even "No changes"."""
        if self._refreshing:
            self._refresh_again = bool(self._refresh_again) or speak
            return
        self._refreshing = True
        host = self._lineups_host
        store = self._store
        ids = [lineup.id for lineup in self._book.lineups if lineup.rules]

        def work() -> tuple[Catalogue, dict[str, RefreshResult]]:
            now = host.now()
            catalogue = host.catalogue(now)
            results: dict[str, RefreshResult] = {}
            for lineup_id in ids:
                _book, outcome = store.update(apply_refresh(lineup_id, catalogue, now=now))
                if outcome.refresh is not None:
                    results[lineup_id] = outcome.refresh
            return catalogue, results

        def done(result: Any) -> None:
            self._refreshing = False
            if not self._win:
                return
            catalogue, results = result
            self._after_refresh(catalogue, results, speak=speak)
            self._follow_up()

        def failed(error: BaseException) -> None:
            self._refreshing = False
            if self._win:
                host.announce(f"Lineups could not be refreshed: {error}.")
                self._follow_up()

        host.submit("lineups-refresh", work, done, failed)

    def _follow_up(self) -> None:
        again = self._refresh_again
        self._refresh_again = None
        if again is not None:
            self.request_refresh(speak=again)

    def _after_refresh(
        self, catalogue: Catalogue, results: dict[str, RefreshResult], *, speak: bool
    ) -> None:
        self._catalogue = catalogue
        self._book = self._load_book()
        self._stamp = self._store.stamp()
        current = self.current_lineup()
        sentence = ""
        for lineup_id, result in results.items():
            if current is not None and lineup_id == current.id:
                selected = set(self.selected_refs())
                left_here = [d.reason for d in result.left if d.ref in selected]
                sentence = describe.refresh_sentence(
                    result, selected_left=left_here[0] if left_here else ""
                )
            elif result.added:
                self._new[lineup_id] = self._new.get(lineup_id, 0) + len(result.added)
        if not sentence and speak:
            sentence = "No changes."
        self.reload()
        if sentence and self._win.IsActive():
            # After the reload has put the cursor where it goes: a sentence said
            # just before a focus change is cut off by it (review M5).
            self._lineups_host.say_outcome_soon(sentence)

    def _tick(self) -> None:
        stamp = self._store.stamp()
        if stamp != self._stamp:
            self._stamp = stamp
            self._book = self._load_book()
            self.reload()  # the other app changed something; the cursor stays put
        sources = self._sources_stamp()
        now = self._lineups_host.now()
        if sources != self._source_stamps or now - self._last_timed >= TIMED_REFRESH_SECONDS:
            self._source_stamps = sources
            self._last_timed = now
            self.request_refresh(speak=False)


__all__ = ["TIMED_REFRESH_SECONDS", "LineupsRefreshMixin"]
