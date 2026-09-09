"""Back and Forward: the undo for moving about.

Without these, every jump in QuillLite is one-way. Somebody who pressed F3 to
check a word elsewhere in the document, or followed a heading, or went to a line
number, can only return to the paragraph they were writing if they happen to
know its line number -- and the line number is exactly the thing a listener was
never told. A sighted reader glances back; there is no equivalent gesture, so it
has to be a key.

**Alt+Left and Alt+Right**, which is what Back and Forward have meant in every
browser and file window for thirty years, and the pair QUILL binds for
``navigate.back_location`` / ``forward_location``. The ring itself is QUILL's
:class:`~quill.core.locations.LocationRing`; this is the wiring.

Two things make the difference between a Back key that works and one that only
appears to, and both are easy to get wrong:

* **Every jump records, at one seam.** ``DocumentCommandsMixin._go_to`` is what
  Go To Line, Go To Anything, the heading commands, the heading list and the
  bookmarks all call, so the recording happens there once instead of beside each
  caller. The failure mode of the other arrangement is a jump somebody forgot to
  record, and a Back key that silently skips one of the places you have been is
  worse than no Back key -- it teaches you to distrust it. Find records too,
  separately, because a search hit lands by selection rather than through
  ``_go_to``.
* **Back and Forward do not record.** Moving here through ``_go_to`` would push
  the place just left onto the ring, so a second Back would return to the first
  and the pair would bounce between two positions for ever while looking like it
  worked.

Unlike the bookmarks next door this is per window and in memory: "where I was a
moment ago" is a fact about this sitting, not about the document.
"""

from __future__ import annotations

__all__ = ["DocumentHistoryMixin"]


class DocumentHistoryMixin:
    """The location ring's commands.

    Mixed into :class:`~quill.apps.lite_window.DocumentFrame`, which supplies
    ``control``, ``locations``, ``_announce`` and ``_touch_status``.
    """

    def _record_location(self) -> None:
        """Remember where the caret is now, before something moves it."""
        self.locations.record(self.control.GetInsertionPoint())

    def cmd_back_location(self) -> None:
        """Go back to where you were before the last jump.

        The undo for navigation. Without it every jump is one-way: a listener
        who pressed Go To Line, or followed a heading, or landed on a search hit
        has no way back to the paragraph they were writing except to remember a
        line number they never read. Alt+Left and Alt+Right because that is what
        Back and Forward have meant in every browser and file manager for
        thirty years -- QUILL binds the same pair.
        """
        target = self.locations.back(self.control.GetInsertionPoint())
        if target is None:
            self._announce("No earlier place")
            return
        self._move_without_recording(target)
        self._announce("Went back")

    def cmd_forward_location(self) -> None:
        """Undo a Back. Nothing to go forward to until you have gone back."""
        target = self.locations.forward(self.control.GetInsertionPoint())
        if target is None:
            self._announce("No later place")
            return
        self._move_without_recording(target)
        self._announce("Went forward")

    def _move_without_recording(self, position: int) -> None:
        """Move for a Back or Forward, which the ring is already tracking.

        Deliberately not :meth:`_go_to`: recording here would push the place we
        just left onto the ring, and pressing Back twice would then land on the
        same two positions for ever instead of walking further back.

        Announced, unlike an ordinary jump, because "went back" is the outcome
        and the screen reader cannot infer it -- it reads the line the caret
        landed on, which is the same thing it would read for a jump forwards.
        """
        position = max(0, min(int(position), self.control.GetLastPosition()))
        self.control.SetInsertionPoint(position)
        self.control.ShowPosition(position)
        self.control.SetFocus()
        self._touch_status()
