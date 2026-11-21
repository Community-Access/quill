"""Help > Take the Tour, and the tour on the first visit (PRD D15, GH-R-115).

The steps are :mod:`quill.core.github.workbench_tour`'s; the frame's Walk Me
Through It speaks them through the window's announcements. The first-run tour
is offered once per person, after the first list arrives, and never with
Show First time here? help turned off.
"""

from __future__ import annotations

from typing import Any

__all__ = ["TOUR_REASONS", "TOUR_VERBS", "GitHubWorkbenchTourMixin"]

TOUR_VERBS: dict[str, frozenset[str]] = {"tour": frozenset({"view"})}
TOUR_REASONS: dict[str, str] = {"tour": "The tour is always here."}


class GitHubWorkbenchTourMixin:
    frame: Any

    def _fits_tour(self, _row: object) -> bool:
        return True

    def _do_tour(self, _ref: Any, _row: object) -> None:
        from quill.core.github.workbench_tour import TOUR_STEPS, TOUR_TITLE

        self.frame.tree.SetFocus()  # the tour starts where its first step is
        self.frame.start_walk(TOUR_TITLE, "", TOUR_STEPS)

    def maybe_first_tour(self) -> None:
        """The first visit: the tour, once per person, unless first-time help is off."""
        if getattr(self, "_tour_checked", False) or self.frame is None:
            return
        self._tour_checked = True
        from quill.core.github.workbench_prefs import load_prefs
        from quill.core.github.workbench_tips import TipMoments
        from quill.core.github.workbench_tour import TOUR_ID, TOUR_STEPS, TOUR_TITLE

        if not load_prefs().first_time_help:
            return
        moments = getattr(self, "_tip_moments", None) or TipMoments.load()
        self._tip_moments = moments
        if TOUR_ID in moments.offered:
            return
        moments.offered.add(TOUR_ID)  # kept when the window closes (save_tip_moments)
        self.frame._wx.CallAfter(self.frame.start_walk, TOUR_TITLE, "", TOUR_STEPS)
