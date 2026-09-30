"""Next, Previous and Mark as Played and Next (ear.md R2, R3).

Every test calls the handler in its own source, never through
``getattr(host, name)()`` over a parametrized string -- that shape is what let
QUILL Lite's F8 bug through with a green suite, and R1 is a fresh reminder that a
Cast command module can be dead on arrival. So the first test here imports it.

What each command *says* is tested as carefully as what it does: the app speaks
only what the reader cannot, so Next says nothing of its own (playback announces
the title) and the ends of the run speak because nothing changed anywhere.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary


def test_the_module_imports() -> None:
    import quill.ui.podcasts.queue_commands as commands

    assert commands.next_in_queue and commands.previous_in_queue
    assert commands.mark_played_and_next


class _State:
    def __init__(self, show_id: str, guid: str) -> None:
        self.show_id = show_id or None
        self.episode_guid = guid or None


class _Controller:
    def __init__(self, show_id: str = "", guid: str = "", position: int = 0) -> None:
        self.state = _State(show_id, guid)
        self._position = position
        self.seeks: list[int] = []
        self.stopped = False

    def position_ms(self) -> int:
        return self._position

    def seek(self, ms: int) -> None:
        self.seeks.append(ms)

    def stop(self) -> None:
        self.stopped = True


class _Host:
    """Only what the queue commands ask for."""

    def __init__(self, *guids: str, playing: str = "", position: int = 0) -> None:
        show = PodcastShow(
            id="s1",
            title="Main Menu",
            feed_url="https://e/f.xml",
            episodes=[
                PodcastEpisode(
                    guid=guid,
                    title=f"Episode {guid}",
                    audio_url=f"https://e/{guid}.mp3",
                    published="2026-07-01T00:00:00",
                )
                for guid in guids
            ],
        )
        self._podcast_library = PodcastLibrary(shows=[show])
        self._podcast_library.queue = [QueueItem(show_id="s1", episode_guid=guid) for guid in guids]
        self._podcast_controller = _Controller("s1" if playing else "", playing, position)
        self._podcast_current_episode = show.find_episode(playing) if playing else None
        self.said: list[str] = []
        self.sounds: list[Any] = []
        self.saves = 0
        self.played: list[str] = []

    # what the commands call
    def _save_podcast_library(self) -> None:
        self.saves += 1

    def _announce(self, text: str, sound: Any = None) -> None:
        self.said.append(text)
        if sound is not None:
            self.sounds.append(sound)

    @property
    def queue(self) -> list[str]:
        return [item.episode_guid for item in self._podcast_library.queue]


def _patch_playback(monkeypatch) -> list[str]:
    """Record what would have been played, without a real player."""
    started: list[str] = []

    def fake_start(_controller, _library, _show, episode) -> None:
        started.append(episode.guid)

    monkeypatch.setattr(
        "quill.ui.podcasts.show_actions.start_episode_playback", fake_start, raising=True
    )
    return started


# -- R2: Next ------------------------------------------------------------- #


def test_next_plays_the_following_slot_and_leaves_the_queue_intact(monkeypatch) -> None:
    from quill.ui.podcasts.queue_commands import next_in_queue

    started = _patch_playback(monkeypatch)
    host = _Host("a", "b", "c", playing="a")

    next_in_queue(host)

    assert started == ["b"]
    assert host.queue == ["a", "b", "c"]


def test_next_says_nothing_of_its_own(monkeypatch) -> None:
    """Playback already announces the title; "Next" would be a word in the way."""
    from quill.ui.podcasts.queue_commands import next_in_queue

    _patch_playback(monkeypatch)
    host = _Host("a", "b", playing="a")

    next_in_queue(host)

    assert host.said == []


def test_next_at_the_end_says_so_with_an_earcon(monkeypatch) -> None:
    from quill.core.sound_events import SoundEvent
    from quill.ui.podcasts.queue_commands import next_in_queue

    started = _patch_playback(monkeypatch)
    host = _Host("a", "b", playing="b")

    next_in_queue(host)

    assert started == []
    assert host.said == ["End of queue"]
    assert host.sounds == [SoundEvent.DOCUMENT_BOTTOM]


# -- R2: Previous and the five-second rule -------------------------------- #


def test_previous_restarts_when_you_are_into_the_episode(monkeypatch) -> None:
    from quill.ui.podcasts.queue_commands import previous_in_queue

    started = _patch_playback(monkeypatch)
    host = _Host("a", "b", playing="b", position=30_000)

    previous_in_queue(host)

    assert started == []
    assert host._podcast_controller.seeks == [0]
    assert host.said == ["Restarted Episode b"]


def test_previous_steps_back_when_you_have_only_just_started(monkeypatch) -> None:
    from quill.ui.podcasts.queue_commands import previous_in_queue

    started = _patch_playback(monkeypatch)
    host = _Host("a", "b", playing="b", position=1_000)

    previous_in_queue(host)

    assert started == ["a"]
    assert host._podcast_controller.seeks == []


def test_previous_at_the_start_says_so_with_an_earcon(monkeypatch) -> None:
    from quill.core.sound_events import SoundEvent
    from quill.ui.podcasts.queue_commands import previous_in_queue

    _patch_playback(monkeypatch)
    host = _Host("a", "b", playing="a", position=0)

    previous_in_queue(host)

    assert host.said == ["Start of queue"]
    assert host.sounds == [SoundEvent.DOCUMENT_TOP]


# -- R3: Mark as Played and Next ------------------------------------------ #


def test_mark_played_and_next_marks_removes_and_advances(monkeypatch) -> None:
    from quill.ui.podcasts.queue_commands import mark_played_and_next

    started = _patch_playback(monkeypatch)
    host = _Host("a", "b", "c", playing="b")

    mark_played_and_next(host)

    episode = host._podcast_library.shows[0].find_episode("b")
    assert episode.played is True
    assert episode.position_ms == 0
    assert host.queue == ["a", "c"]
    assert started == ["c"]


def test_mark_played_and_next_does_not_say_marked_as_played(monkeypatch) -> None:
    """Two facts in one breath is one too many on a key pressed in runs.

    The next episode's title proves the command fired, and the mark is
    verifiable in the row just left.
    """
    from quill.ui.podcasts.queue_commands import mark_played_and_next

    _patch_playback(monkeypatch)
    host = _Host("a", "b", playing="a")

    mark_played_and_next(host)

    assert host.said == []


def test_mark_played_and_next_at_the_end_stops_and_says_so(monkeypatch) -> None:
    from quill.ui.podcasts.queue_commands import mark_played_and_next

    started = _patch_playback(monkeypatch)
    host = _Host("a", "b", playing="b")

    mark_played_and_next(host)

    assert host.queue == ["a"]
    assert started == []
    assert host._podcast_controller.stopped is True
    assert host.said == ["End of queue"]


def test_mark_played_and_next_with_nothing_playing_says_so(monkeypatch) -> None:
    from quill.ui.podcasts.queue_commands import mark_played_and_next

    _patch_playback(monkeypatch)
    host = _Host("a", "b")

    mark_played_and_next(host)

    assert host.said == ["Nothing is playing."]
    assert host.queue == ["a", "b"]
