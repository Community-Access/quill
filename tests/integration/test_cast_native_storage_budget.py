"""Measure shared podcast storage callbacks and QUILL's Downloads dialog.

Cast routes its Downloads command to a main-window place, exercised by the
separate native test in test_cast_one_window.py, not this shared dialog.
"""

from __future__ import annotations

import gc
import os
import sys
from cProfile import Profile
from datetime import UTC, datetime
from io import StringIO
from pstats import Stats
from time import monotonic, perf_counter, sleep
from types import SimpleNamespace

import pytest

pytestmark = [
    pytest.mark.perf,
    pytest.mark.machine_global,
    pytest.mark.skipif(
        sys.platform != "win32" or os.environ.get("RUN_PERF") != "1",
        reason="Requires opt-in native Windows performance verification",
    ),
]


@pytest.mark.timeout(240)
def test_storage_and_downloads_have_no_ui_turn_over_16ms(tmp_path, monkeypatch):
    import wx

    from quill.core.podcasts.models import PodcastEpisode, PodcastShow
    from quill.core.podcasts.subscriptions import PodcastLibrary
    from quill.stability.task_manager import TaskManager, UiLifetimeToken
    from quill.ui.main_frame_podcast_session import PodcastSessionMixin
    from quill.ui.podcasts.downloads_dialog import DownloadsDialog
    from quill.ui.podcasts.storage_tasks import for_host
    from quill.ui.undo_file_jobs import FileJobs

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    library = PodcastLibrary()
    for index in range(1300):
        path = tmp_path / f"synthetic-{index}.mp3"
        path.write_bytes(b"isolated synthetic download")
        episodes = [
            PodcastEpisode(
                guid=f"episode-{episode}",
                title=f"Synthetic episode {episode}",
                audio_url="https://example.invalid/synthetic.mp3",
                published=datetime.now(UTC).isoformat(),
                duration_seconds=600,
            )
            for episode in range(150)
        ]
        episodes[0].downloaded_path = str(path)
        episodes[0].played = index % 2 == 0
        library.shows.append(PodcastShow(id=str(index), title=f"Show {index}", episodes=episodes))
    app = wx.GetApp() or wx.App()
    previous_loop = wx.EventLoop.GetActive()
    loop = wx.GUIEventLoop()
    wx.EventLoop.SetActive(loop)
    frame = wx.Frame(None, title="Isolated Cast storage performance")
    manager = TaskManager(max_workers=2)
    ui_lifetime = UiLifetimeToken()
    frame._quill_ui_lifetime = ui_lifetime
    phase = "setup"
    timings = {}
    heartbeat_times = []
    collections = []
    started_collections = {}
    native_later, native_after = wx.CallLater, wx.CallAfter
    timers = []
    dialog = None

    def timed(callback, args, kwargs):
        def invoke():
            profiler = Profile() if os.environ.get("CAST_STORAGE_PROFILE") == "1" else None
            previous_trace = sys.gettrace()
            line_timings = {}
            previous_line = None
            previous_time = perf_counter()

            def trace(frame, event, _argument):
                nonlocal previous_line, previous_time
                if frame.f_code.co_name != "__init__" or not frame.f_code.co_filename.endswith(
                    "downloads_dialog.py"
                ):
                    return None
                current = perf_counter()
                if previous_line is not None:
                    line_timings[previous_line] = (
                        line_timings.get(previous_line, 0) + current - previous_time
                    )
                previous_line = frame.f_lineno if event != "return" else None
                previous_time = current
                return trace

            tracing = profiler is not None and getattr(callback, "__name__", "") == "open_downloads"
            if tracing:
                sys.settrace(trace)
            if profiler is not None:
                profiler.enable()
            started = perf_counter()
            try:
                callback(*args, **kwargs)
            finally:
                duration = perf_counter() - started
                if profiler is not None:
                    profiler.disable()
                if tracing:
                    sys.settrace(previous_trace)
                    print(
                        "Downloads construction lines (ms):",
                        sorted(
                            [
                                (line, round(value * 1000, 2))
                                for line, value in line_timings.items()
                            ],
                            key=lambda item: item[1],
                            reverse=True,
                        )[:10],
                    )
                timings.setdefault(phase, []).append(duration)
                if duration > 0.016:
                    print(
                        f"Slow {phase} {getattr(callback, '__name__', type(callback).__name__)}: "
                        f"{duration * 1000:.2f} ms"
                    )
                    if profiler is not None:
                        details = StringIO()
                        Stats(profiler, stream=details).sort_stats("cumulative").print_stats(8)
                        print(details.getvalue())

        return invoke

    def later(delay, callback, *args, **kwargs):
        timer = native_later(delay, timed(callback, args, kwargs))
        timers.append(timer)
        return timer

    def after(callback, *args, **kwargs):
        return native_after(timed(callback, args, kwargs))

    def collect(when, info):
        generation = info["generation"]
        if when == "start":
            started_collections[generation] = perf_counter()
        elif generation in started_collections:
            collections.append((generation, perf_counter() - started_collections.pop(generation)))

    monkeypatch.setattr(wx, "CallLater", later)
    monkeypatch.setattr(wx, "CallAfter", after)

    class Host(PodcastSessionMixin):
        def _announce(self, message):
            self.spoken.append(message)

        def _save_podcast_library(self):
            self._podcast_library_revision += 1

    host = Host()
    host.frame = frame
    host._wx = wx
    host._task_manager = manager
    host._cast_ui_lifetime = ui_lifetime
    host._cast_closing = host._cast_closed = False
    host._podcast_library_revision = 0
    host._podcast_library = library
    host._podcast_download_queue = None
    host._podcast_controller = SimpleNamespace(
        state=SimpleNamespace(show_id=None, episode_guid=None)
    )
    host._undo_file_jobs = FileJobs(manager, host, tmp_path)
    host.spoken = []
    heartbeat = wx.Timer(frame)
    frame.Bind(wx.EVT_TIMER, lambda _event: heartbeat_times.append(perf_counter()), heartbeat)
    heartbeat.Start(25)

    def pump_until(predicate):
        deadline = monotonic() + 60
        while not predicate() and monotonic() < deadline:
            app.ProcessPendingEvents()
            wx.YieldIfNeeded()
            loop.ProcessIdle()
            sleep(0.001)
        assert predicate(), host.spoken

    def measure(name, action, complete):
        nonlocal phase
        phase = name
        started = monotonic()
        later(1, action)
        pump_until(complete)
        values = timings[name]
        print(
            f"Native storage {name}: {len(values)} UI callbacks; "
            f"maximum {max(values) * 1000:.2f} ms; {monotonic() - started:.2f} s total"
        )

    gc.callbacks.append(collect)
    try:
        maintenance = []
        measure(
            "maintenance",
            lambda: host.podcast_run_maintenance(completed=maintenance.append),
            lambda: bool(maintenance),
        )

        def open_downloads():
            nonlocal dialog
            dialog = DownloadsDialog(
                frame,
                library=library,
                storage_jobs=for_host(host),
                announce_cb=host._announce,
                on_free_space=host.podcast_free_up_space,
            )

        measure(
            "downloads-all",
            open_downloads,
            lambda: (
                dialog is not None
                and dialog._list.GetItemCount() == 1300
                and "1300 downloaded" in dialog._summary.GetLabel()
            ),
        )
        assert len(dialog._rows) == 1300

        def unheard():
            dialog._filter.SetSelection(1)
            dialog._refresh(announce=True)

        measure(
            "downloads-unheard",
            unheard,
            lambda: (
                dialog._list.GetItemCount() == 650
                and "650 already-played" in dialog._summary.GetLabel()
            ),
        )
        freed = []
        measure(
            "free-space",
            lambda: host.podcast_free_up_space(completed=freed.append),
            lambda: bool(freed),
        )
        assert freed == [0]
        assert len(heartbeat_times) > 100
        listener_gap = max(
            b - a for a, b in zip(heartbeat_times, heartbeat_times[1:], strict=False)
        )
        print(f"Maximum listener gap: {listener_gap * 1000:.2f} ms")
        if collections:
            generation, duration = max(collections, key=lambda item: item[1])
            print(f"Longest GC: generation {generation}, {duration * 1000:.2f} ms")
        maxima = {name: max(values) for name, values in timings.items() if name != "setup"}
        assert all(value <= 0.016 for value in maxima.values()), {
            name: round(value * 1000, 2) for name, value in maxima.items()
        }
    finally:
        gc.callbacks.remove(collect)
        heartbeat.Stop()
        if dialog is not None:
            dialog._cancel_ui()
            dialog.dialog.Destroy()
        for timer in timers:
            timer.Stop()
        ui_lifetime.invalidate()
        manager.shutdown(wait=True, cancel_pending=True)
        frame.Destroy()
        app.ProcessPendingEvents()
        wx.EventLoop.SetActive(previous_loop)
