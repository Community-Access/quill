"""Auto-advance says when the next queued episode cannot start (Chris Nova, 2026-11-17)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.podcasts import queue_steps
from quill.ui import main_frame_podcasts as mfp
from quill.ui.podcasts import show_actions


def _host(said: list[str]) -> Any:
    settings = SimpleNamespace(run_end_action="queue")
    library = SimpleNamespace(settings=settings, effective_settings=lambda _show: settings)
    return SimpleNamespace(
        _podcast_library=library,
        _podcast_controller=object(),
        _save_podcast_library=lambda: None,
        _announce=said.append,
    )


def _run(monkeypatch: Any, started: bool) -> list[str]:
    nxt = SimpleNamespace(title="Episode Two")
    step = queue_steps.Step(kind="play", show=SimpleNamespace(), episode=nxt)
    monkeypatch.setattr(queue_steps, "step_after_finishing", lambda *_a: (step, 0))
    monkeypatch.setattr(show_actions, "start_episode_playback", lambda *_a, **_k: started)
    said: list[str] = []
    mfp.PodcastsMixin._podcast_play_next_from_queue(
        _host(said), finished_show=SimpleNamespace(id="s"), finished_guid="g1"
    )
    return said


def test_the_next_queued_episode_is_announced_when_it_starts(monkeypatch: Any) -> None:
    assert _run(monkeypatch, True) == ["Up next from the queue: Episode Two"]


def test_a_next_episode_that_cannot_start_says_so(monkeypatch: Any) -> None:
    said = _run(monkeypatch, False)
    assert said and said[0].startswith("Could not start the next episode, Episode Two.")


def test_an_episode_that_cannot_start_is_passed_over_for_the_next(monkeypatch: Any) -> None:
    """With three queued, the second has nothing to play: the third starts."""
    from quill.ui.podcasts.queue_advance import start_next

    two = SimpleNamespace(title="Two", guid="g2")
    three = SimpleNamespace(title="Three", guid="g3")
    show = SimpleNamespace(id="s")
    started: list[str] = []

    def fake_start(_c: Any, _l: Any, _s: Any, episode: Any, **_k: Any) -> bool:
        if episode is two:
            return False
        started.append(episode.title)
        return True

    monkeypatch.setattr(show_actions, "start_episode_playback", fake_start)
    monkeypatch.setattr(
        queue_steps,
        "step_next",
        lambda *_a: queue_steps.Step(kind="play", show=show, episode=three),
    )
    said: list[str] = []
    host = _host(said)
    host._podcast_library.queue = [object(), object()]
    assert start_next(host, show, two, "Up next: Two", from_queue=True)
    assert started == ["Three"]
    assert said == ["Could not start Two: nothing to play yet. Playing Three instead."]
