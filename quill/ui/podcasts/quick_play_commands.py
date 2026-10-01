"""Play an Unheard Episode, Play Queue Shuffled, Clear Entire Queue (ear.md R5).

Earshot publishes these three to Siri, which on a phone means "say it and it
happens". The desktop equivalent of saying something is a key, and the desktop's
advantage is that a key works with the app in the background and needs no
microphone.

All three decisions live in ``core/podcasts/quick_plays.py``, wx-free and tested.
What is here is only the wiring, plus the three things a UI has to decide that a
pure module cannot:

* **When to speak.** Play an Unheard Episode announces *where it looked*, because a
  key that chose on the listener's behalf has to say what it chose and why that
  episode -- "from the queue" and "from your podcasts" are different facts about a
  library. Playback announces the title itself, so the source is all this adds.
* **When to ask.** Clearing the queue asks, with the count in the question, because
  "clear the queue" feels very different at three items and at forty.
* **What to do with the cursor.** Shuffling and clearing both change a list the
  listener may be standing in, so the queue window is refreshed if it is open --
  and left alone if it is not, rather than opened to show a change nobody asked
  to see.

Clear Entire Queue is also what the status bar's Queue cell offers, which is why
this module exists rather than three methods scattered across the frame.
"""

from __future__ import annotations

from typing import Any

__all__ = ["CastQuickPlayMixin"]


def _refresh_open_queue_window(host: Any) -> None:
    """Redraw the Play Queue window if it happens to be open. Never opens it.

    Opening it would be the app deciding the listener wanted to look at the queue
    because they shuffled it, which is a different intention from shuffling it.
    """
    window = getattr(host, "_play_queue_dialog", None)
    reload_rows = getattr(window, "_reload", None)
    if callable(reload_rows):
        try:
            reload_rows()
        except Exception:  # noqa: BLE001 - a stale window is not worth a crash
            pass


class CastQuickPlayMixin:
    """The three one-press verbs. Mixed into ``PodcastsAppFrame``."""

    def podcast_play_unheard(self, *, oldest: bool = False) -> None:
        """Play something unheard: the queue first, then the Inbox, then the rest.

        *oldest* is the backlog intention rather than the news intention, and both
        are offered because they are genuinely different: newest is "what is going
        on today", oldest is "let me work through what I have missed".

        Nothing already started is ever picked -- a resume position means the
        listener is in the middle of that episode, and starting it from a
        one-press key would be indistinguishable from losing their place.
        """
        from quill.core.podcasts import quick_plays

        order = quick_plays.OLDEST if oldest else quick_plays.NEWEST
        pick = quick_plays.unheard_pick(self._podcast_library, order=order)
        if pick is None:
            self._announce(quick_plays.nothing_unheard(order))
            return
        # The source, and only the source: starting playback announces the title,
        # so repeating it here would be GATE-13's duplication. Said *before* the
        # play so the two sentences arrive in the order they happened.
        self._announce(f"Playing from {pick.source}")
        self._play_episode_object(pick.show, pick.episode)

    def podcast_play_unheard_oldest(self) -> None:
        """The backlog variant, as its own command so it can carry its own key."""
        self.podcast_play_unheard(oldest=True)

    def podcast_shuffle_queue(self) -> None:
        """Shuffle the whole queue.

        Announced with the count, because a shuffled list is the one change a
        listener cannot verify by listening: the next episode sounds exactly as
        plausible either way, and without a count there is no evidence anything
        happened at all.
        """
        from quill.core.podcasts import quick_plays

        count = quick_plays.shuffle_whole_queue(self._podcast_library)
        if count < 2:
            self._announce(
                "Nothing to shuffle: the queue is empty."
                if not count
                else "The queue has one item, so there is nothing to shuffle."
            )
            return
        self._save_podcast_library()
        _refresh_open_queue_window(self)
        self._announce(f"Queue shuffled, {count} items")

    def podcast_clear_entire_queue(self) -> None:
        """Empty the queue, having asked first and said what survives.

        The question carries the count *and* the reassurance, because "clear the
        queue" reads as a delete -- and somebody who would happily have cleared it
        cancels rather than find out what it costs. Nothing is deleted, nothing is
        marked played, and every episode stays in its podcast.
        """
        from quill.core.podcasts import quick_plays

        question = quick_plays.clear_queue_confirm(self._podcast_library)
        if not question:
            self._announce("The queue is already empty.")
            return
        import wx

        from quill.ui.dialog_contract import show_message_box

        answer = show_message_box(
            question,
            "Clear the Play Queue",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.frame,
            announce=self._announce,
        )
        if answer != wx.YES:
            return
        removed = quick_plays.clear_queue(self._podcast_library)
        self._save_podcast_library()
        _refresh_open_queue_window(self)
        self._announce(f"Play Queue cleared, {removed} item{'' if removed == 1 else 's'} removed")
