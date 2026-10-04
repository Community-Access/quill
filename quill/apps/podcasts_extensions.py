"""QUILL Cast's listening extensions (qc.md section 18, Phase 7).

The small keys a listener reaches for by hand, each removing one wonder:

* **Ctrl+Shift+T** -- how much is left, at this speed, and when the sleep timer
  ends (item 3).
* **Ctrl+Home** -- back to the launch place, first row, from anywhere in the
  window except a text field, where Ctrl+Home keeps meaning "top of the text"
  (item 5).
* **Shift+Space** -- Play This Next, on any episode row (item 9).
* **Up next**, said about ten seconds before an episode ends when something
  will follow it, unless Quiet Hours hold it back or the listener switched it
  off (item 4).
* **Ctrl+N with an address on the clipboard** fills it in (item 8) -- see
  :meth:`_podcast_open_add_dialog`.

Keys a text field also answers are caught in the frame's char hook, never as
menu accelerators, because an accelerator is translated before the focused
control sees the key.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import listening_words
from quill.core.sound_events import SoundEvent
from quill.ui.podcasts.cast_ai_features import CastDomainAiMixin

__all__ = ["CastExtensionsMixin"]


class CastExtensionsMixin(CastDomainAiMixin):  # with Cast's AI verbs (ear.md A2-A9)
    """Mixed into ``PodcastsAppFrame`` ahead of the shared podcast mixins."""

    # -- Ctrl+Shift+T ---------------------------------------------------------- #

    def say_time_remaining(self) -> None:
        """Ctrl+Shift+T: where you are, how much is left, and the sleep timer."""
        controller = getattr(self, "_podcast_controller", None)
        state = getattr(controller, "state", None)
        if controller is None or not getattr(state, "episode_guid", ""):
            self._announce("Nothing is playing.", force=True)  # type: ignore[attr-defined]
            return
        timer = getattr(self, "_sleep_timer_controller", None)
        at_end = bool(getattr(timer, "is_end_of_episode", False))
        active = bool(getattr(timer, "is_active", False))
        seconds = int(getattr(timer, "remaining_seconds", 0) or 0) if active else 0
        sentence = listening_words.time_left(
            controller.position_ms(),
            controller.length_ms(),
            speed=float(getattr(controller, "rate", 1.0) or 1.0),
            sleep_seconds=seconds,
            sleep_at_end=at_end,
        )
        self._announce(sentence, force=True)  # type: ignore[attr-defined]

    # -- Ctrl+Home and Shift+Space, caught in the char hook -------------------------- #

    def _cast_extension_key(self, event: Any) -> bool:
        """True when the key was one of these and has been handled."""
        import wx

        code = event.GetKeyCode()
        if code not in (wx.WXK_HOME, wx.WXK_SPACE):
            return False  # asked only about the two keys, so every other key is free
        focus = wx.Window.FindFocus()
        in_text = isinstance(focus, wx.TextCtrl | wx.SearchCtrl | wx.ComboBox)
        if (
            code == wx.WXK_HOME
            and event.ControlDown()
            and not event.ShiftDown()
            and not event.AltDown()
            and not in_text
        ):
            self.go_home()
            return True
        if (
            code == wx.WXK_SPACE
            and event.ShiftDown()
            and not event.ControlDown()
            and not event.AltDown()
            and not in_text
            and self._selected_episode() is not None  # type: ignore[attr-defined]
        ):
            self.play_this_next()
            return True
        return False

    def go_home(self) -> None:
        """Ctrl+Home: the launch place, focus on its first row."""
        self._select_default_launch_view()  # type: ignore[attr-defined]

    def play_this_next(self) -> None:
        """Shift+Space: the selected episode plays straight after this one."""
        pair = self._selected_episode()  # type: ignore[attr-defined]
        if pair is None:
            self._announce("Choose an episode first.")  # type: ignore[attr-defined]
            return
        show, episode = pair
        state = getattr(getattr(self, "_podcast_controller", None), "state", None)
        playing = None
        if getattr(state, "show_id", None) and getattr(state, "episode_guid", None):
            playing = (state.show_id, state.episode_guid)
        if playing == (show.id, episode.guid):
            self._announce(f"{episode.title} is the one playing.")  # type: ignore[attr-defined]
            return
        listening_words.play_this_next(
            self._podcast_library,  # type: ignore[attr-defined]
            show.id,
            episode.guid,
            playing=playing,
        )
        self._save_podcast_library()  # type: ignore[attr-defined]
        counts = getattr(self, "_refresh_place_counts", None)
        if callable(counts):
            counts()
        if getattr(self, "_current_place", "") == "queue":
            self._refresh_place()  # type: ignore[attr-defined]
        after = "after this one" if playing else "first in the Play Queue"
        from quill.ui.podcasts.outcome_feedback import say_outcome

        say_outcome(
            self, f"{episode.title} plays next, {after}.", sound=SoundEvent.CAST_QUEUE_ADDED
        )

    # -- up next -------------------------------------------------------------------- #

    def _podcast_second_tick(self) -> None:
        super()._podcast_second_tick()  # type: ignore[misc]
        try:
            self._maybe_say_up_next()
        except Exception:  # noqa: BLE001 - a courtesy must never disturb playback
            return

    def _maybe_say_up_next(self) -> None:
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        history = getattr(self, "_podcast_history", None)
        if history is None or not getattr(history, "announce_up_next", True):
            return
        controller = getattr(self, "_podcast_controller", None)
        state = getattr(controller, "state", None)
        if state is None or state.state is not PodcastPlayerState.PLAYING:
            return
        key = (state.show_id, state.episode_guid)
        if getattr(self, "_up_next_said", None) == key:
            return
        speed = float(getattr(controller, "rate", 1.0) or 1.0)
        if not listening_words.up_next_due(
            controller.position_ms(), controller.length_ms(), speed=speed
        ):
            return
        self._up_next_said = key
        if getattr(self, "_podcast_stop_after_episode", False):
            return
        timer = getattr(self, "_sleep_timer_controller", None)
        if bool(getattr(timer, "is_end_of_episode", False)):
            return
        following = self._what_follows(state.show_id or "", state.episode_guid or "")
        if following is None:
            return
        show, episode = following
        sentence = listening_words.up_next_sentence(
            show, episode, same_show=show is not None and show.id == state.show_id
        )
        from quill.ui.quiet_hours_ui import speak_background

        speak_background(self, sentence)

    def _what_follows(self, show_id: str, guid: str) -> tuple[Any, Any] | None:
        """What the run-end choice will play when this episode ends, or None."""
        from quill.core.podcasts import run_end
        from quill.core.podcasts.queue_steps import step_next
        from quill.core.podcasts.sorting import sort_episodes

        library = self._podcast_library  # type: ignore[attr-defined]
        show = library.find_show(show_id)
        settings = library.effective_settings(show) if show is not None else library.settings
        choice = run_end.from_settings(settings)
        if choice == "queue":
            step = step_next(library, show_id, guid)
            if step.kind == "play":
                return step.show, step.episode
        if choice == "folder" and show is not None:
            for episode in sort_episodes(show.episodes, "unplayed_first"):
                if not episode.played and episode.guid != guid:
                    return show, episode
        return None

    # -- Ctrl+N with an address on the clipboard ------------------------------------------ #

    def _clipboard_feed_address(self) -> str:
        """A web address on the clipboard, or "" -- read quietly, never a modal."""
        import wx

        from quill.ui.clipboard_retry import read_clipboard_text

        try:
            text = read_clipboard_text(wx, surface_errors=False).strip()
        except Exception:  # noqa: BLE001
            return ""
        if not text or "\n" in text or len(text) > 2000 or " " in text:
            return ""
        lowered = text.lower()
        return text if lowered.startswith(("https://", "http://")) else ""

    # -- bookmarks (item 1) ------------------------------------------------------------- #

    def _bookmark_episode(self) -> tuple[Any, Any] | None:
        """The playing episode, else the selected one: what bookmarks are about."""
        state = getattr(getattr(self, "_podcast_controller", None), "state", None)
        library = self._podcast_library  # type: ignore[attr-defined]
        if getattr(state, "show_id", None) and getattr(state, "episode_guid", None):
            show = library.find_show(state.show_id)
            episode = show.find_episode(state.episode_guid) if show is not None else None
            if show is not None and episode is not None:
                return show, episode
        return self._selected_episode()  # type: ignore[attr-defined,no-any-return]

    def bookmark_with_note(self) -> None:
        """Ctrl+Shift+D: Bookmark This Moment, with a line about why."""
        import wx

        from quill.core import bookmark_ops

        anchor, position_ms, title = self._bookmark_target()  # type: ignore[attr-defined]
        if not anchor:
            self._announce(bookmark_ops.NOTHING_PLAYING)  # type: ignore[attr-defined]
            return
        when = bookmark_ops.spoken_position(position_ms)
        with wx.TextEntryDialog(  # dialog_button_contract: exempt
            self.frame,  # type: ignore[attr-defined]
            f"A note for the bookmark at {when} (optional):",
            "Bookmark with a Note",
        ) as entry:
            if entry.ShowModal() != wx.ID_OK:
                return
            note = entry.GetValue().strip()
        mark, said = bookmark_ops.add(
            self._bookmark_store(),  # type: ignore[attr-defined]
            anchor,
            position_ms,
            title=title,
            note=note,
        )
        self._announce(said)  # type: ignore[attr-defined]

    def open_episode_bookmarks(self) -> None:
        """Ctrl+Shift+J: this episode's bookmarks, in the shared Bookmarks window."""
        from quill.core import bookmark_anchors
        from quill.ui.bookmarks_dialog import show_bookmarks

        pair = self._bookmark_episode()
        if pair is None:
            self._announce("Play or choose an episode first.")  # type: ignore[attr-defined]
            return
        show, episode = pair
        anchor = bookmark_anchors.for_episode(str(show.id), str(episode.guid))
        store = self._bookmark_store()  # type: ignore[attr-defined]
        if not store.list(anchor):
            self._announce(  # type: ignore[attr-defined]
                f"No bookmarks in {episode.title} yet. Ctrl+Alt+A marks the moment."
            )
            return
        show_bookmarks(self, store=store, anchor=anchor)
