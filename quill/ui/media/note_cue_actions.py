"""Reading a bookmark's note aloud when playback reaches it (x.md item 4).

The rule for *which* notes have been crossed lives in
:mod:`quill.core.media.note_cues`, which is wx-free and where the awkward cases
(seeking, pausing, skipping back) are decided and tested. This module is the
other half: the bit that needs a player and a screen reader.

It is here rather than in ``quill/apps/player.py`` because that module was at
its GATE-11 budget, and because this is the same shape as its neighbour
``bookmark_actions`` -- a host-taking helper, so the Player and any other
surface that grows a playhead can share one behaviour rather than each
reimplementing the anchoring.

The anchor is the whole subtlety. Announcing needs to know where playback *was*
a second ago, and that value has to be reset -- not merely updated -- whenever
the answer would be misleading: when a book opens, when the feature is switched
on mid-book, and whenever there is no book at all. Every one of those, left
un-reset, produces the same bug from the listener's side: a note read out for a
stretch of audio they never actually listened through.
"""

from __future__ import annotations

from typing import Any

from quill.core.media.bookmarks import BookmarkStore
from quill.core.media.note_cues import announcement_for, cues_reached

#: The anchor value meaning "nothing has been listened through yet".
NO_ANCHOR = -1


def announce_reached(
    host: Any,
    store: BookmarkStore,
    book_key: str,
    previous_ms: int,
    current_ms: int,
) -> int:
    """Speak the note on every bookmark just crossed. Returns the new anchor.

    Returning the anchor rather than writing it back on *host* keeps this
    testable without a frame, and keeps the caller's state where the caller can
    see it.

    A first tick (``previous_ms`` is :data:`NO_ANCHOR`) announces nothing: there
    is no interval behind it yet, only a position.
    """
    if not book_key:
        return NO_ANCHOR
    if previous_ms == NO_ANCHOR:
        return current_ms
    for mark in cues_reached(store.list(book_key), previous_ms, current_ms):
        host._announce(announcement_for(mark))
    return current_ms


class NoteCuesMixin:
    """The Player's half of note cues: one menu toggle and one tick hook.

    A mixin for the same reason ``MediaListenMixin`` and
    ``MediaWinampKeysMixin`` are: ``quill/apps/player.py`` sits exactly at its
    GATE-11 budget, and a feature that is four lines of wiring plus thirty of
    behaviour should put the thirty somewhere else.
    """

    # Provided by the host.
    frame: Any
    _bookmarks: BookmarkStore
    _book_key: str
    _player: Any

    #: On by default -- writing the note is the opt-in. Somebody who has left
    #: notes on a book has already said they want them.
    _note_cues_on: bool = True
    _last_cue_position_ms: int = NO_ANCHOR

    def _add_note_cue_menu_item(self, menu: Any, wx: Any) -> Any:
        """Append the toggle to *menu* and bind it. Returns the new id."""
        cue_id = wx.NewIdRef()
        item = menu.AppendCheckItem(cue_id, "Read My &Notes Aloud as I Reach Them")
        item.Check(self._note_cues_on)
        self.frame.Bind(wx.EVT_MENU, self._on_toggle_note_cues, id=cue_id)
        return cue_id

    def _on_toggle_note_cues(self, event: Any) -> None:
        self._note_cues_on = bool(event.IsChecked())
        # Re-anchor rather than keep the old position: switching back on
        # mid-book must not read out notes you skipped past while it was off.
        self._last_cue_position_ms = NO_ANCHOR
        self._announce(
            "Reading notes aloud on." if self._note_cues_on else "Reading notes aloud off."
        )

    def _announce_reached_notes(self) -> None:
        """Rides the host's one-second status tick; a separate timer would be a
        second thing to remember to stop when playback stops."""
        if not self._note_cues_on:
            self._last_cue_position_ms = NO_ANCHOR
            return
        self._last_cue_position_ms = announce_reached(
            self,
            self._bookmarks,
            self._book_key,
            self._last_cue_position_ms,
            self._player.playhead_ms(),
        )

    def _announce(self, message: str) -> None:  # pragma: no cover - host provides
        raise NotImplementedError
