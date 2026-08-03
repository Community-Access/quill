"""Watch profiles and the multi-profile watch manager (WATCH-1, WATCH-5).

A :class:`WatchProfile` is a named, independently enabled rule: a folder, a set
of filters, exactly one action (bound by id into the WATCH-2 registry), and
post-action handling. The :class:`WatchManager` runs one poller per enabled
profile concurrently with isolated failure (one bad profile or file never stalls
the others) and feeds every detection into the shared durable queue (WATCH-3),
which de-duplicates so a file is claimed exactly once across overlapping
profiles.

This module is UI-framework-agnostic: no ``wx`` imports.
"""

from __future__ import annotations

import fnmatch
import logging
import threading
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .monitor_policy import MONITOR_WATCH_FOLDER, MonitorPolicy
from .watch_queue import WatchQueue

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

_DEFAULT_POLL_SECONDS = 5
_MIN_POLL_SECONDS = 2
_MAX_POLL_SECONDS = 300
_MIN_FILE_AGE_SECONDS = 2.0
_MINUTES_PER_DAY = 24 * 60

#: Post-action handling for a source file once its action succeeds.
POST_LEAVE = "leave"
POST_MOVE = "move"
POST_DELETE = "delete"
_POST_ACTIONS = frozenset({POST_LEAVE, POST_MOVE, POST_DELETE})

#: Schedule mode controlling *when* a profile's poller is active.
#: ``always`` polls continuously; ``window`` polls only inside a daily
#: time-of-day window (the active interval); ``quiet_hours`` polls
#: continuously except inside the window (the quiet interval).
SCHED_ALWAYS = "always"
SCHED_WINDOW = "window"
SCHED_QUIET = "quiet_hours"
_SCHEDULE_MODES = frozenset({SCHED_ALWAYS, SCHED_WINDOW, SCHED_QUIET})

_DEFAULT_SUFFIXES = (
    ".txt",
    ".md",
    ".html",
    ".htm",
    ".json",
    ".csv",
    ".tsv",
    ".docx",
    ".pptx",
    ".epub",
    ".pdf",
    ".odt",
    ".rtf",
)


def _clean_suffix(suffix: str) -> str:
    suffix = suffix.strip().lower()
    if not suffix:
        return ""
    if not suffix.startswith("."):
        suffix = "." + suffix
    return suffix


def _clean_pattern(pattern: str) -> str:
    return pattern.strip()


def _clamp_minute(value: object) -> int:
    minute = _as_int(value, 0)
    return max(0, min(_MINUTES_PER_DAY - 1, minute))


@dataclass(frozen=True, slots=True)
class WatchProfile:
    """One named watch rule binding a folder to a single action."""

    profile_id: str = ""
    name: str = "Untitled profile"
    enabled: bool = False
    folder_path: str = ""
    include_subfolders: bool = False
    process_existing: bool = False
    suffixes: tuple[str, ...] = _DEFAULT_SUFFIXES
    name_patterns: tuple[str, ...] = ()
    min_size_bytes: int = 1
    min_age_seconds: float = _MIN_FILE_AGE_SECONDS
    poll_interval_seconds: int = _DEFAULT_POLL_SECONDS
    schedule_mode: str = SCHED_ALWAYS
    schedule_start_minute: int = 0
    schedule_end_minute: int = 0
    action_id: str = "open"
    action_options: dict[str, object] = field(default_factory=dict)
    post_action: str = POST_LEAVE
    post_action_destination: str = ""

    def normalized(self) -> WatchProfile:
        interval = int(self.poll_interval_seconds or _DEFAULT_POLL_SECONDS)
        interval = max(_MIN_POLL_SECONDS, min(_MAX_POLL_SECONDS, interval))
        suffixes = tuple(dict.fromkeys(s for s in (_clean_suffix(x) for x in self.suffixes) if s))
        patterns = tuple(
            dict.fromkeys(p for p in (_clean_pattern(x) for x in self.name_patterns) if p)
        )
        post = self.post_action if self.post_action in _POST_ACTIONS else POST_LEAVE
        mode = self.schedule_mode if self.schedule_mode in _SCHEDULE_MODES else SCHED_ALWAYS
        return WatchProfile(
            profile_id=self.profile_id or uuid.uuid4().hex,
            name=str(self.name).strip() or "Untitled profile",
            enabled=bool(self.enabled),
            folder_path=str(self.folder_path).strip(),
            include_subfolders=bool(self.include_subfolders),
            process_existing=bool(self.process_existing),
            suffixes=suffixes or _DEFAULT_SUFFIXES,
            name_patterns=patterns,
            min_size_bytes=max(0, int(self.min_size_bytes)),
            min_age_seconds=max(0.0, float(self.min_age_seconds)),
            poll_interval_seconds=interval,
            schedule_mode=mode,
            schedule_start_minute=_clamp_minute(self.schedule_start_minute),
            schedule_end_minute=_clamp_minute(self.schedule_end_minute),
            action_id=str(self.action_id).strip() or "open",
            action_options=dict(self.action_options),
            post_action=post,
            post_action_destination=str(self.post_action_destination).strip(),
        )

    def validate(self) -> list[str]:
        """Return human-readable configuration problems (empty when valid)."""
        problems: list[str] = []
        normalized = self.normalized()
        if not normalized.folder_path:
            problems.append("Choose a folder to watch.")
        elif not Path(normalized.folder_path).expanduser().is_dir():
            problems.append(f"Watch folder does not exist: {normalized.folder_path}")
        if normalized.post_action == POST_MOVE:
            destination = normalized.post_action_destination
            if not destination:
                problems.append("Choose a destination folder for processed files.")
            elif not Path(destination).expanduser().is_dir():
                problems.append(f"Destination folder does not exist: {destination}")
        if (
            normalized.schedule_mode in {SCHED_WINDOW, SCHED_QUIET}
            and normalized.schedule_start_minute == normalized.schedule_end_minute
        ):
            problems.append("Choose a start and end time that differ for the schedule window.")
        return problems

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "enabled": self.enabled,
            "folder_path": self.folder_path,
            "include_subfolders": self.include_subfolders,
            "process_existing": self.process_existing,
            "suffixes": list(self.suffixes),
            "name_patterns": list(self.name_patterns),
            "min_size_bytes": self.min_size_bytes,
            "min_age_seconds": self.min_age_seconds,
            "poll_interval_seconds": self.poll_interval_seconds,
            "schedule_mode": self.schedule_mode,
            "schedule_start_minute": self.schedule_start_minute,
            "schedule_end_minute": self.schedule_end_minute,
            "action_id": self.action_id,
            "action_options": dict(self.action_options),
            "post_action": self.post_action,
            "post_action_destination": self.post_action_destination,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> WatchProfile:
        suffixes_raw = raw.get("suffixes")
        if isinstance(suffixes_raw, (list, tuple)):
            suffixes = tuple(str(s) for s in suffixes_raw)
        else:
            suffixes = _DEFAULT_SUFFIXES
        patterns_raw = raw.get("name_patterns")
        if isinstance(patterns_raw, (list, tuple)):
            patterns = tuple(str(p) for p in patterns_raw)
        else:
            patterns = ()
        options_raw = raw.get("action_options")
        options = dict(options_raw) if isinstance(options_raw, dict) else {}
        return cls(
            profile_id=str(raw.get("profile_id", "")),
            name=str(raw.get("name", "Untitled profile")),
            enabled=bool(raw.get("enabled", False)),
            folder_path=str(raw.get("folder_path", "")),
            include_subfolders=bool(raw.get("include_subfolders", False)),
            process_existing=bool(raw.get("process_existing", False)),
            suffixes=suffixes,
            name_patterns=patterns,
            min_size_bytes=_as_int(raw.get("min_size_bytes"), 1),
            min_age_seconds=_as_float(raw.get("min_age_seconds"), _MIN_FILE_AGE_SECONDS),
            poll_interval_seconds=_as_int(raw.get("poll_interval_seconds"), _DEFAULT_POLL_SECONDS),
            schedule_mode=str(raw.get("schedule_mode", SCHED_ALWAYS)),
            schedule_start_minute=_as_int(raw.get("schedule_start_minute"), 0),
            schedule_end_minute=_as_int(raw.get("schedule_end_minute"), 0),
            action_id=str(raw.get("action_id", "open")),
            action_options=options,
            post_action=str(raw.get("post_action", POST_LEAVE)),
            post_action_destination=str(raw.get("post_action_destination", "")),
        ).normalized()


def _as_int(value: object, default: int) -> int:
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return default


def _as_float(value: object, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def iter_matching_files(profile: WatchProfile, *, now: float | None = None) -> Iterable[Path]:
    """Yield files in ``profile``'s folder that pass its filters.

    Applies the suffix set, minimum size, and minimum settle age so partially
    written files are skipped until they stop changing. Returns nothing when the
    folder is missing rather than raising, so a transiently unavailable network
    share never crashes the poller.
    """
    folder = Path(profile.folder_path).expanduser()
    if not folder.is_dir():
        return
    moment = time.time() if now is None else now
    suffixes = set(profile.suffixes)
    patterns = profile.name_patterns
    pattern = "**/*" if profile.include_subfolders else "*"
    candidates: list[Path] = []
    for candidate in folder.glob(pattern):
        if not candidate.is_file():
            continue
        if candidate.suffix.lower() not in suffixes:
            continue
        if patterns and not any(
            fnmatch.fnmatch(candidate.name.lower(), pat.lower()) for pat in patterns
        ):
            continue
        try:
            stat = candidate.stat()
        except OSError:
            continue
        if stat.st_size < profile.min_size_bytes:
            continue
        if (moment - stat.st_mtime) < profile.min_age_seconds:
            continue
        candidates.append(candidate)
    candidates.sort(key=lambda path: path.name.lower())
    yield from candidates


def _within_window(minute: int, start: int, end: int) -> bool:
    """Return True when ``minute`` falls in the daily window ``[start, end)``.

    Supports windows that wrap past midnight (``start > end``), e.g. 22:00-07:00.
    A zero-width window (``start == end``) is treated as empty.
    """
    if start == end:
        return False
    if start < end:
        return start <= minute < end
    return minute >= start or minute < end


def profile_is_active(profile: WatchProfile, *, now: datetime | None = None) -> bool:
    """Return whether ``profile``'s schedule permits polling at ``now``.

    ``always`` is always active. ``window`` is active only inside the daily
    time-of-day window. ``quiet_hours`` is active everywhere except inside the
    window. The poller consults this before each scan so a profile stays armed
    but dormant outside its schedule.
    """
    normalized = profile.normalized()
    mode = normalized.schedule_mode
    if mode == SCHED_ALWAYS:
        return True
    moment = datetime.now() if now is None else now
    minute = moment.hour * 60 + moment.minute
    inside = _within_window(
        minute, normalized.schedule_start_minute, normalized.schedule_end_minute
    )
    if mode == SCHED_WINDOW:
        return inside
    return not inside


class WatchManager:
    """Runs one poller thread per enabled profile, feeding the shared queue.

    Each poller catches and logs its own exceptions so a single failing profile
    can never stall the others (isolated failure, WATCH-1). All detections flow
    into the one :class:`WatchQueue`, whose path-based de-duplication enforces
    exactly-once claiming across overlapping profiles.
    """

    def __init__(
        self,
        queue: WatchQueue,
        *,
        policy: MonitorPolicy | None = None,
        on_tick: Callable[[str], None] | None = None,
    ) -> None:
        """``policy`` carries the shared ambient-monitor triple (see
        :mod:`quill.core.monitor_policy`). Its interval is the app-wide default
        cadence: a profile still at the built-in default follows it, while a
        profile the user deliberately tuned keeps its own. ``on_tick`` receives
        the earcon id for one check when the policy asks for an audible tick --
        the shell supplies the player, so this module stays wx-free.
        """
        self._queue = queue
        self._policy = policy or MonitorPolicy(
            monitor=MONITOR_WATCH_FOLDER, poll_interval_seconds=_DEFAULT_POLL_SECONDS
        )
        self._on_tick = on_tick
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}
        self._running = False
        self._last_error: dict[str, str] = {}
        self._consecutive_errors: dict[str, int] = {}

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def policy(self) -> MonitorPolicy:
        """The ambient-monitor policy these pollers run under."""
        return self._policy

    def poll_seconds_for(self, profile: WatchProfile) -> float:
        """The cadence *profile* actually polls at, under the current policy."""
        interval = int(profile.poll_interval_seconds)
        if interval == _DEFAULT_POLL_SECONDS:
            interval = self._policy.poll_interval_seconds
        return float(max(_MIN_POLL_SECONDS, min(_MAX_POLL_SECONDS, interval)))

    def _tick(self) -> None:
        """Post the heartbeat earcon for one check, when the user asked for it."""
        event = self._policy.tick_sound_event
        if not event or self._on_tick is None:
            return
        try:
            self._on_tick(event)
        except Exception:  # noqa: BLE001 - a silent earcon must never stop a poller
            logger.exception("Watch monitor tick failed")

    def active_profile_ids(self) -> set[str]:
        with self._lock:
            return set(self._threads)

    def start(self, profiles: Iterable[WatchProfile]) -> list[str]:
        """Start pollers for every enabled, valid profile; returns started ids."""
        self.stop()
        started: list[str] = []
        with self._lock:
            self._running = True
            for raw_profile in profiles:
                profile = raw_profile.normalized()
                if not profile.enabled:
                    continue
                if profile.validate():
                    logger.warning(
                        "Skipping invalid watch profile %s (%s)",
                        profile.name,
                        profile.profile_id,
                    )
                    continue
                stop_event = threading.Event()
                thread = threading.Thread(
                    target=self._poll_loop,
                    args=(profile, stop_event),
                    name=f"quill-watch-{profile.profile_id[:8]}",
                    daemon=True,
                )
                self._stop_events[profile.profile_id] = stop_event
                self._threads[profile.profile_id] = thread
                started.append(profile.profile_id)
            for profile_id in started:
                self._threads[profile_id].start()
        return started

    def stop(self) -> None:
        with self._lock:
            stop_events = list(self._stop_events.values())
            threads = list(self._threads.items())
            self._stop_events.clear()
            self._threads.clear()
            self._running = False
        for event in stop_events:
            event.set()
        for _profile_id, thread in threads:
            thread.join(timeout=5.0)

    def last_error(self, profile_id: str) -> str | None:
        """Return the most recent error message for ``profile_id``, or ``None``.

        Maps a recurring polling failure to a specific profile_id so the UI can
        surface "Profile X failed N times: <reason>" (M-4). Thread-safe.
        """
        with self._lock:
            return self._last_error.get(profile_id)

    def consecutive_error_count(self, profile_id: str) -> int:
        """Return the running count of consecutive polling errors for ``profile_id``.

        Reset to 0 on the first successful scan after a failure, so a transient
        blip does not make a profile look permanently broken (M-4).
        """
        with self._lock:
            return self._consecutive_errors.get(profile_id, 0)

    def _record_error(self, profile_id: str, exc: BaseException) -> None:
        message = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        with self._lock:
            self._last_error[profile_id] = message
            self._consecutive_errors[profile_id] = self._consecutive_errors.get(profile_id, 0) + 1

    def _clear_error(self, profile_id: str) -> None:
        with self._lock:
            self._last_error.pop(profile_id, None)
            self._consecutive_errors.pop(profile_id, None)

    def _poll_loop(self, profile: WatchProfile, stop_event: threading.Event) -> None:
        if not profile.process_existing:
            # Reserve the de-dup slot for files present at startup so they are
            # ignored until they change, without enqueuing or actioning them.
            try:
                for path in iter_matching_files(profile):
                    self._queue.prime(path)
            except Exception as error:  # never let prescan crash the poller
                logger.exception("Watch prescan failed for profile %s", profile.profile_id)
                self._record_error(profile.profile_id, error)
        while not stop_event.is_set():
            try:
                if profile_is_active(profile):
                    self._tick()
                    for path in iter_matching_files(profile):
                        self._queue.enqueue(path, profile.profile_id, profile.action_id)
                self._clear_error(profile.profile_id)
            except Exception as error:  # isolated failure: log and keep polling
                logger.exception("Watch scan failed for profile %s", profile.profile_id)
                self._record_error(profile.profile_id, error)
            stop_event.wait(self.poll_seconds_for(profile))


__all__ = [
    "POST_DELETE",
    "POST_LEAVE",
    "POST_MOVE",
    "SCHED_ALWAYS",
    "SCHED_QUIET",
    "SCHED_WINDOW",
    "SCHEMA_VERSION",
    "WatchManager",
    "WatchProfile",
    "iter_matching_files",
    "profile_is_active",
]
