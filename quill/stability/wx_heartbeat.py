"""wx main-thread heartbeat watchdog.

Implements: ROADMAP STAB-5 (a ``wx.Timer``-driven heartbeat the main
thread publishes on a tick; if the tick stops, the watchdog logs the
last known state and dumps thread stacks via
:func:`quill.stability.diagnostics.dump_all_thread_stacks` so a
frozen UI leaves a forensic trail in the log).
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from quill.stability.diagnostics import dump_all_thread_stacks

try:  # pragma: no cover - optional dependency in non-UI test environments
    import wx  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    wx = None  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover
    import wx as _wx_types

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HeartbeatState:
    last_ui_tick: float = field(default_factory=time.monotonic)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def tick(self) -> None:
        with self.lock:
            self.last_ui_tick = time.monotonic()

    def age_seconds(self) -> float:
        with self.lock:
            return time.monotonic() - self.last_ui_tick


class WxHeartbeatTimer:
    def __init__(
        self,
        window: _wx_types.Window,
        state: HeartbeatState,
        interval_ms: int = 1000,
    ) -> None:
        if wx is None:
            raise RuntimeError("wxPython is required for WxHeartbeatTimer")
        self.window = window
        self.state = state
        self.timer = wx.Timer(window)
        window.Bind(wx.EVT_TIMER, self._on_timer, self.timer)
        self.timer.Start(interval_ms)

    def _on_timer(self, event: object) -> None:
        self.state.tick()
        skip = getattr(event, "Skip", None)
        if callable(skip):
            skip()

    def stop(self) -> None:
        if hasattr(self.timer, "IsRunning") and self.timer.IsRunning():
            self.timer.Stop()


class WxHeartbeatWatchdog:
    def __init__(
        self,
        state: HeartbeatState,
        dump_callback: Callable[[str], object] = dump_all_thread_stacks,
        warn_after_seconds: float = 5.0,
        dump_after_seconds: float = 15.0,
        poll_seconds: float = 2.0,
        warn_dump_after_seconds: float | None = 5.0,
    ) -> None:
        self.state = state
        self.dump_callback = dump_callback
        self.warn_after_seconds = warn_after_seconds
        self.dump_after_seconds = dump_after_seconds
        self.poll_seconds = poll_seconds
        # A one-shot stack dump per stall *episode* as soon as the stall crosses
        # this shorter threshold. Without it, short-but-real stalls (e.g. the
        # ~7 s startup block reported in review.md) trip the warning but never
        # reach ``dump_after_seconds`` (15 s), so no thread-stack forensic trail
        # is captured and the cause stays invisible. Set to None to disable.
        self.warn_dump_after_seconds = warn_dump_after_seconds
        self._warn_dumped_this_episode = False
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="quill-wx-heartbeat-watchdog",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._thread.join(timeout=timeout)

    def _should_dump(self, age: float, now: float, last_dump_time: float) -> bool:
        """Whether to fire a stack dump now.

        Dump at most once per ``dump_after_seconds``-length recovery window, so a
        brief UI unblock followed by a second block triggers a second dump rather
        than a flood. Pure (no clock/IO) so the re-dump policy is unit-testable
        without wall-clock timing.
        """
        return age >= self.dump_after_seconds and (now - last_dump_time) >= self.dump_after_seconds

    def _should_warn_dump(self, age: float) -> bool:
        """Whether to fire the one-shot per-episode warn-level stack dump.

        Fires once when the stall first crosses ``warn_dump_after_seconds`` and
        not again until the UI recovers (age falls back below the warn
        threshold), so a single short freeze produces exactly one dump. Pure so
        the episode policy is unit-testable.
        """
        if self.warn_dump_after_seconds is None:
            return False
        return age >= self.warn_dump_after_seconds and not self._warn_dumped_this_episode

    def _run(self) -> None:
        last_dump_time = 0.0
        self._warn_dumped_this_episode = False
        while not self._stop.wait(self.poll_seconds):
            age = self.state.age_seconds()
            now = time.monotonic()
            # Episode reset: once the UI is responsive again, re-arm the one-shot
            # warn-level dump so the next distinct stall is captured too.
            if age < self.warn_after_seconds:
                self._warn_dumped_this_episode = False
            if age >= self.warn_after_seconds:
                logger.warning("wx UI heartbeat stale for %.1f seconds", age)
            # Capture the blocking UI-thread stack for short-but-real stalls that
            # never reach the 15 s hard-dump threshold (e.g. a ~7 s startup block).
            if self._should_warn_dump(age):
                logger.warning("wx UI heartbeat: capturing stacks at %.1f s stall", age)
                self.dump_callback(f"wx UI heartbeat stale for {age:.1f} seconds (warn-level)")
                self._warn_dumped_this_episode = True
            if self._should_dump(age, now, last_dump_time):
                logger.error("wx UI appears blocked for %.1f seconds", age)
                self.dump_callback(f"wx UI heartbeat stale for {age:.1f} seconds")
                last_dump_time = now
