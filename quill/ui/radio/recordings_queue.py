"""The recordings play queue, as the dialog drives it (x.md item 12).

``winamp_keys.py`` deliberately left ``R``, ``S`` and ``Ctrl+V`` unbound while
the recordings player had no queue. :mod:`quill.core.radio.play_queue` is the
queue itself -- pure, wx-free, and where the actual rules live (shuffle is a
fixed permutation, repeat-one applies to a natural end rather than to Next,
stop-after-current outranks repeat and clears itself). This mixin is the other
half: the three key handlers, playing a row, and following a recording that
ended on its own.

Its own module because ``recordings_manager_dialog.py`` was already at its
GATE-11 budget, and this is a real seam rather than a convenient one -- every
method here is about *what plays next*, and none of them touches the list's
in-place refresh diff, which is the delicate part of that file.

**Shuffle and repeat persist; stop-after-current does not.** The first two are
standing preferences and come back from ``RadioHistory``. A stop that survived
a restart would halt playback for a reason nobody could remember asking for,
so the one-shot starts off every session.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.models import RadioStation


class RecordingsQueueMixin:
    """Shuffle, repeat, stop-after-current, and what follows a finished file."""

    #: The queue, built on first use by :meth:`_play_queue`. Class-level
    #: defaults rather than host ``__init__`` state, so the queue works on any
    #: instance that has a ``_history`` -- including the partially constructed
    #: dialogs the tests drive the key handlers against.
    _queue: Any = None
    #: The row the queue believes is playing, so a recording that ends on its
    #: own can be followed by the next. -1 = nothing queued.
    _queue_row: int = -1

    def _play_row(self, row: int) -> None:
        """Select *row*, play it, and remember it as the queue's position."""
        self._list.Select(row)
        self._list.Focus(row)
        entry = self._entries[row]
        station = RadioStation(name=entry.name, stream_url=str(entry.path))
        self._controller.play_station(station)
        self._queue_row = row
        self._announce(f"Playing recording {entry.name}.")
        self._on_selection_changed()

    # -- the play queue (item 12) -----------------------------------------

    def _play_queue(self) -> Any:
        """The queue, built on first use from the saved preferences.

        Shuffle and repeat are standing preferences and come back from
        ``RadioHistory``; stop-after-current deliberately starts off every
        session, because a stop that survived a restart would halt playback
        for a reason nobody could remember asking for.
        """
        if self._queue is None:
            from quill.core.radio.play_queue import PlayQueue

            history = getattr(self, "_history", None)
            self._queue = PlayQueue(
                shuffle=bool(getattr(history, "recordings_shuffle", False)),
                repeat=str(getattr(history, "recordings_repeat", "off")),
            )
        return self._queue

    def _winamp_toggle_shuffle(self) -> None:
        """R: shuffle on or off, rebuilding the play order either way."""
        on = self._play_queue().toggle_shuffle(self._playable_rows())
        self._history.recordings_shuffle = on
        self._save_history()
        self._announce("Shuffle on." if on else "Shuffle off.")

    def _winamp_cycle_repeat(self) -> None:
        """S: off, then all recordings, then this recording."""
        from quill.core.radio.play_queue import REPEAT_LABELS

        mode = self._play_queue().cycle_repeat()
        self._history.recordings_repeat = mode
        self._save_history()
        self._announce(REPEAT_LABELS[mode])

    def _winamp_toggle_stop_after_current(self) -> None:
        """Ctrl+V: stop when this one ends. A one-shot; it clears when it fires.

        Deliberately not remembered between sessions: a stop that survived a
        restart would halt playback for a reason nobody could remember asking
        for.
        """
        on = self._play_queue().toggle_stop_after_current()
        self._announce(
            "Will stop after this recording." if on else "Will keep playing after this recording."
        )

    def _save_history(self) -> None:
        """Ask the host to persist the standing queue preferences."""
        try:
            self._on_history_changed()
        except Exception:  # noqa: BLE001 - a preference that fails to save is not fatal
            pass

    def _advance_queue_if_finished(self) -> None:
        """Follow a recording that ended on its own with whatever is next.

        Driven from the existing refresh timer rather than a controller
        callback: the controller's single ``on_state_changed`` belongs to the
        app frame, and a modal dialog borrowing it would have to give it back
        on every exit path -- including the ones that are exceptions.
        """
        from quill.core.radio.play_queue import NO_ROW
        from quill.ui.radio.playback_state import RadioPlayerState

        if self._queue_row < 0:
            return
        state = getattr(self._controller, "state", None)
        if state is None or state.state is not RadioPlayerState.STOPPED:
            return
        finished, self._queue_row = self._queue_row, -1
        rows = self._playable_rows()
        if not rows:
            return
        self._play_queue().set_rows_if_changed(rows)
        nxt = self._play_queue().row_after_finishing(finished)
        if nxt == NO_ROW or nxt >= len(self._entries):
            return
        self._play_row(nxt)

    def _winamp_step(self, direction: int) -> None:
        """B / Z: the next or previous recording *in the queue's order*.

        With shuffle off that is the list order, exactly as before. With it on
        it is the shuffled permutation -- and because that permutation is
        fixed, Z reliably goes back to what you just heard.
        """
        from quill.core.radio.play_queue import NO_ROW

        rows = self._playable_rows()
        if not rows:
            self._announce("There are no finished recordings to play.")
            return
        queue = self._play_queue()
        queue.set_rows_if_changed(rows)
        current = self._list.GetFirstSelected()
        row = queue.next_row(current) if direction > 0 else queue.previous_row(current)
        if row == NO_ROW:
            self._announce(
                "This is the last recording." if direction > 0 else "This is the first recording."
            )
            return
        self._play_row(row)
