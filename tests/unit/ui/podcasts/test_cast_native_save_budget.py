"""Measure the real Windows save-snapshot turns at the large-library target."""

from __future__ import annotations

import gc
import os
import sys
from cProfile import Profile
from io import StringIO
from pstats import Stats
from time import monotonic, perf_counter, sleep, thread_time
from types import SimpleNamespace

import pytest

from quill.core.podcasts.library_payload import LibraryPayload
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.main_frame_podcast_save import PodcastLibrarySaveMixin
from quill.ui.podcasts.save_snapshot import save_show
from tests.wx_session import shared_wx_app

pytestmark = [
    pytest.mark.perf,
    pytest.mark.skipif(
        sys.platform != "win32" or os.environ.get("RUN_PERF") != "1",
        reason="Requires opt-in native Windows performance verification",
    ),
]


def test_1300_show_snapshot_has_no_ui_turn_over_16ms() -> None:
    import wx

    library = PodcastLibrary(
        shows=[
            PodcastShow(
                id=f"show-{show_index}",
                title=f"Synthetic show {show_index}",
                episodes=[
                    PodcastEpisode(
                        guid=f"episode-{episode_index}",
                        title=f"Synthetic episode {episode_index}",
                        audio_url="https://example.invalid/synthetic.mp3",
                        duration_seconds=600,
                    )
                    for episode_index in range(150)
                ],
            )
            for show_index in range(1300)
        ]
    )
    app = wx.GetApp() or shared_wx_app()
    previous_loop = wx.EventLoop.GetActive()
    loop = wx.GUIEventLoop()
    wx.EventLoop.SetActive(loop)
    frame = wx.Frame(None)
    turns: list[float] = []
    cpu_turns: list[float] = []
    timers: list[object] = []
    snapshots: list[LibraryPayload] = []
    expected_positions: list[int] = []
    announcements: list[str] = []
    heartbeats: list[float] = []
    collections: list[tuple[int, float]] = []
    collection_started: dict[int, float] = {}

    def collection_timing(phase, info):
        generation = info["generation"]
        if phase == "start":
            collection_started[generation] = perf_counter()
        elif generation in collection_started:
            collections.append((generation, perf_counter() - collection_started.pop(generation)))

    def call_later(delay, callback):
        def timed():
            profiler = Profile() if os.environ.get("CAST_SNAPSHOT_PROFILE") == "1" else None
            if profiler is not None:
                profiler.enable()
            cpu_started = thread_time()
            started = perf_counter()
            callback()
            duration = perf_counter() - started
            cpu_duration = thread_time() - cpu_started
            if profiler is not None:
                profiler.disable()
            turns.append(duration)
            cpu_turns.append(cpu_duration)
            if duration > 0.016:
                print(
                    f"Slow {callback.__name__}: {duration * 1000:.2f} ms elapsed, "
                    f"{cpu_duration * 1000:.2f} ms UI-thread CPU"
                )
            if profiler is not None and duration > 0.016:
                details = StringIO()
                Stats(profiler, stream=details).sort_stats("cumulative").print_stats(10)
                print(f"Slow {callback.__name__}: {duration * 1000:.2f} ms\n{details.getvalue()}")

        timer = wx.CallLater(delay, timed)
        timers.append(timer)
        return timer

    class Host(PodcastLibrarySaveMixin):
        def _queue_podcast_library_snapshot(self, generation, snapshot, *, revision=None):
            expected_positions.append(library.shows[0].episodes[-1].position_ms)
            snapshots.append(snapshot)
            self._podcast_library_dirty = False

        def _announce(self, message):
            announcements.append(message)

    host = Host()
    host.frame = frame
    host._wx = SimpleNamespace(CallLater=call_later, Timer=wx.Timer, EVT_TIMER=wx.EVT_TIMER)
    host._podcast_library = library
    host._podcast_library_dirty = True
    host._podcast_library_revision = 0
    host._podcast_unscoped_revision = 0
    host._podcast_download_queue = SimpleNamespace(set_reconnect_settings=lambda **_kwargs: None)
    episode = library.shows[0].episodes[-1]
    heartbeat = wx.Timer(frame)

    def tick(_event):
        heartbeats.append(perf_counter())
        episode.position_ms += 1000
        save_show(host, library.shows[0].id, episode_guid=episode.guid)

    frame.Bind(wx.EVT_TIMER, tick, heartbeat)
    heartbeat.Start(25)
    started = monotonic()
    gc.callbacks.append(collection_timing)
    try:
        call_later(1, host._flush_podcast_library)
        deadline = monotonic() + 45
        while not snapshots and monotonic() < deadline:
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            loop.ProcessIdle()
            sleep(0.001)
        heartbeat.Stop()
        assert snapshots, (announcements, len(turns))
        snapshot = snapshots[0]
        assert isinstance(snapshot, LibraryPayload)
        shows = snapshot.data["shows"]
        assert len(shows) == 1300
        assert sum(len(show["episodes"]) for show in shows) == 195_000
        assert shows[0]["episodes"][-1]["position_ms"] == expected_positions[0]
        assert shows[0]["episodes"][-1] is not episode
        assert len(heartbeats) > 10
        maximum = max(turns)
        print(
            f"Native save snapshot: 1300 shows, 195000 episodes; "
            f"{len(turns)} UI turns; maximum {maximum * 1000:.2f} ms; "
            f"maximum UI-thread CPU {max(cpu_turns) * 1000:.2f} ms; "
            f"{len(heartbeats)} listener checkpoints; {monotonic() - started:.2f} s total; "
            f"maximum listener gap "
            f"{max(b - a for a, b in zip(heartbeats, heartbeats[1:], strict=False)) * 1000:.2f} ms"
        )
        if collections:
            generation, duration = max(collections, key=lambda item: item[1])
            print(
                f"Longest garbage collection: generation {generation}, "
                f"{duration * 1000:.2f} ms; {len(collections)} collections"
            )
        assert maximum <= 0.016, f"UI turn took {maximum * 1000:.2f} ms"
    finally:
        gc.callbacks.remove(collection_timing)
        heartbeat.Stop()
        for timer in timers:
            timer.Stop()
        save_timer = getattr(host, "_podcast_save_timer", None)
        if save_timer is not None:
            save_timer.Stop()
        frame.Destroy()
        app.ProcessPendingEvents()
        wx.EventLoop.SetActive(previous_loop)
