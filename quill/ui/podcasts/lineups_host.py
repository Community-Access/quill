"""Quill Cast's side of the Lineups window.

Cast plays podcast episodes, through its own Play Queue: playing a Lineup from
an episode puts that episode and the Lineup's episodes after it at the front of
the queue (the same rule Apply Lineup has always had) and starts the first, so
Cast's queue carries on by itself. A podcast plays its next episode.

Stations, YouTube, Local Media and recordings are Quill Radio's to play. Cast
hands those rows to Radio (``quill.core.lineups.handoff``), opening Radio if it
is not running, and says so -- a row that did nothing on Enter would be worse.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.model import Lineup
from quill.core.lineups.refs import KIND_EPISODE, KIND_SHOW, ItemRef, split_key
from quill.ui.lineups.host import LineupsHost


class CastLineupsHost(LineupsHost):
    app_key = "cast"
    app_name = "Quill Cast"

    def announce(self, text: str) -> None:
        speak = getattr(self.app, "_announce", None)
        if callable(speak) and text:
            speak(text)

    def say_outcome(self, text: str) -> None:
        try:
            from quill.ui.podcasts.outcome_feedback import say_outcome

            say_outcome(self.app, text, sound="")
        except Exception:  # noqa: BLE001 - feedback never fails an action
            self.announce(text)

    def play(
        self, lineup: Lineup, refs: Sequence[ItemRef], start: int, facts: Sequence[ItemFacts | None]
    ) -> str:
        if not (0 <= start < len(refs)):
            return f"{lineup.name} has nothing to play."
        first = refs[start]
        if first.kind == KIND_SHOW:
            player = getattr(self.app, "_play_show_next_episode", None)
            if callable(player):
                player(first.key)
                return ""
            return "This podcast cannot be played here."
        if first.kind != KIND_EPISODE:
            return self._hand_to_radio(lineup, list(refs[start:]))
        rest = list(refs[start:])
        episodes = [ref for ref in rest if ref.kind == KIND_EPISODE]
        others = len(rest) - len(episodes)
        self._queue_front(episodes)
        show_id, guid = split_key(first)
        player = getattr(self.app, "_play_specific_episode", None)
        if callable(player):
            player(show_id, guid)
        if others:
            return (
                f"The lineup's episodes are at the front of the queue. Its other "
                f"{others} item{'s' if others != 1 else ''} play in Quill Radio: "
                "Enter on one of them sends it there."
            )
        return ""

    def _queue_front(self, episodes: Sequence[ItemRef]) -> None:
        from quill.core.podcasts.models import QueueItem
        from quill.core.podcasts.models_playlists import Playlist
        from quill.core.podcasts.queue_lineups import apply_lineup

        library = getattr(self.app, "_podcast_library", None)
        if library is None or not episodes:
            return
        items = [QueueItem(*split_key(ref)) for ref in episodes]
        apply_lineup(
            library, Playlist(id="lineup-play", name="this lineup", kind="manual", items=items)
        )
        save = getattr(self.app, "_save_podcast_library", None)
        if callable(save):
            save()

    def _hand_to_radio(self, lineup: Lineup, refs: list[ItemRef]) -> str:
        from quill.core.ipc import enqueue_open_request
        from quill.core.lineups.handoff import ACTION, write_request

        try:
            path = write_request(self.data_dir, lineup.id, [ref.token for ref in refs])
            enqueue_open_request(path, action=ACTION, slot="radio")
        except OSError as exc:
            return f"Quill Radio could not be asked to play it: {exc}."
        launch = getattr(self.app, "_launch_sibling", None)
        if callable(launch):
            launch("radio")
        from quill.core.lineups.describe import count_text

        if len(refs) == 1:
            return "Sent to Quill Radio to play."
        return f"Sent {count_text(len(refs), 'item')} to Quill Radio to play."

    def play_next(
        self, refs: Sequence[ItemRef], facts: Sequence[ItemFacts | None], *, at_end: bool
    ) -> str:
        from quill.core.podcasts import queue

        library = getattr(self.app, "_podcast_library", None)
        episodes = [ref for ref in refs if ref.kind == KIND_EPISODE]
        if library is None or not episodes:
            return "Play Next and Up Next work on episodes in Quill Cast."
        for ref in reversed(episodes) if not at_end else episodes:
            show_id, guid = split_key(ref)
            if at_end:
                queue.add_to_queue(library, show_id, guid, reason="a lineup")
            else:
                queue.play_next(library, show_id, guid)
        save = getattr(self.app, "_save_podcast_library", None)
        if callable(save):
            save()
        count = len(episodes)
        where = "at the end of the queue" if at_end else "next in the queue"
        return f"{count} episode{'s' if count != 1 else ''} {where}."

    def step(self, delta: int) -> str:
        name = "podcast_next_in_queue" if delta > 0 else "podcast_previous_in_queue"
        command = getattr(self.app, name, None)
        if callable(command):
            command()
            return ""
        return "The queue cannot be stepped here."

    def pause(self) -> None:
        toggle = getattr(self.app, "podcast_toggle_play_pause", None)
        if callable(toggle):
            toggle()

    def stop_after_current(self) -> str:
        return "In Quill Cast, the sleep timer's End of Episode stops after this one."

    def start_lineup_id(self) -> str:
        history = getattr(self.app, "_podcast_history", None)
        return str(getattr(history, "start_lineup_id", "") or "")

    def set_start_lineup_id(self, lineup_id: str) -> None:
        history = getattr(self.app, "_podcast_history", None)
        if history is None:
            return
        history.start_lineup_id = lineup_id
        save = getattr(self.app, "_save_podcast_history", None)
        if callable(save):
            save()


def host_for(app: Any) -> CastLineupsHost:
    return CastLineupsHost(app)


__all__ = ["CastLineupsHost", "host_for"]
