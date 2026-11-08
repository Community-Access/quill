"""Scrobbling from the app's side: hear titles, tick a clock, send off the UI thread.

The rules live in ``quill.core.radio``: what counts as heard
(``scrobble_tracker``), what waits (``scrobble_queue``) and who is signed in
(``scrobbling``). This module only feeds them from the running app:

* :func:`on_title` is called from ``song_history_commands.record_song``, the
  choke point every title change already passes through, so scrobbling and
  Song History can never disagree about what the station sent.
* A timer (:data:`TICK_MS`) runs only while a song is being followed. Each
  tick reads how far behind live playback is, so time-shifted listening counts
  when it is *heard* -- and a paused station adds nothing.
* Sending happens on the task manager, never on the UI thread, one round at a
  time. A sign-in the service no longer accepts is said once per session --
  that is a background result the screen reader cannot know (GATE-13); a song
  sent is said never, because it is not news.

Nothing here runs unless a service is turned on in Preferences, and nothing
runs in Safe Mode. Credit: BlindRadio by serrebidev (MIT) for the idea.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from quill.core.radio import scrobbling
from quill.core.radio.scrobble_queue import SIGN_IN, ScrobbleQueue
from quill.core.radio.scrobble_tracker import HeardTracker, Listen

_log = logging.getLogger(__name__)

#: How often the clock is read while a song is followed.
TICK_MS = 5000


@dataclass(slots=True)
class ScrobbleState:
    tracker: HeardTracker
    queue: ScrobbleQueue
    accounts: scrobbling.Accounts
    timer: Any = None
    sending: bool = False
    #: Songs heard but not yet written to the queue (the worker writes them).
    fresh: list[tuple[str, Listen]] = field(default_factory=list)
    #: Services whose sign-in problem has been said this session.
    warned: set[str] = field(default_factory=set)


def _make_queue() -> ScrobbleQueue:
    from quill.core.paths import app_data_dir

    return ScrobbleQueue(app_data_dir())


def state(host: Any) -> ScrobbleState:
    """The host's scrobbling state, made on first use."""
    found = getattr(host, "_radio_scrobble", None)
    if found is None:
        found = ScrobbleState(
            tracker=HeardTracker(),
            queue=_make_queue(),
            accounts=scrobbling.load_accounts(getattr(host, "_radio_history", None)),
        )
        host._radio_scrobble = found
    return found


def refresh_accounts(host: Any) -> None:
    """Preferences or a sign-in changed something: read the accounts again."""
    found = getattr(host, "_radio_scrobble", None)
    accounts = scrobbling.load_accounts(getattr(host, "_radio_history", None))
    if found is None:
        if accounts.services():
            state(host).accounts = accounts
        return
    found.accounts = accounts
    found.warned.clear()
    for service in accounts.services():
        found.queue.unblock(service)
    if not accounts.services():
        found.tracker.reset()
        _stop_timer(found)


def _wanted(host: Any) -> bool:
    if getattr(host, "_safe_mode", False):
        return False
    history = getattr(host, "_radio_history", None)
    return any(
        bool(getattr(history, name, False))
        for name in ("scrobble_listenbrainz", "scrobble_lastfm", "scrobble_librefm")
    )


def _station(host: Any) -> Any:
    controller = getattr(host, "_radio_controller", None)
    return getattr(getattr(controller, "state", None), "station", None)


def _station_key(station: Any) -> str:
    return str(getattr(station, "station_uuid", "") or getattr(station, "stream_url", "") or "")


def _behind(host: Any) -> float | None:
    controller = getattr(host, "_radio_controller", None)
    probe = getattr(controller, "behind_live_seconds", None)
    if not callable(probe):
        return None
    try:
        value = probe()
    except Exception:  # noqa: BLE001 - an engine that cannot say is "live"
        return None
    return float(value) if isinstance(value, (int, float)) else None


def on_title(host: Any, title: str, *, now: float | None = None) -> None:
    """The station's title changed. Never raises: it runs on the announcement path."""
    try:
        if not _wanted(host):
            return
        station = _station(host)
        if station is None:
            return
        found = state(host)
        if not found.accounts.services():
            return
        found.tracker.note_title(
            _station_key(station),
            title,
            now=time.time() if now is None else now,
            station_name=str(getattr(station, "name", "") or ""),
        )
        _start_timer(host, found)
    except Exception:  # noqa: BLE001 - scrobbling is never worth a lost announcement
        _log.debug("Scrobbling could not note a title", exc_info=True)


def _start_timer(host: Any, found: ScrobbleState) -> None:
    if found.timer is None:
        wx = getattr(host, "_wx", None)
        frame = getattr(host, "frame", None)
        make = getattr(wx, "Timer", None)
        if not callable(make) or frame is None:
            return
        found.timer = make(frame)
        frame.Bind(wx.EVT_TIMER, lambda _e: tick(host), found.timer)
    if not found.timer.IsRunning():
        found.timer.Start(TICK_MS)


def _stop_timer(found: ScrobbleState) -> None:
    timer = found.timer
    if timer is not None and timer.IsRunning():
        timer.Stop()


def tick(host: Any, *, now: float | None = None) -> None:
    """One look at the playhead. Queues what was heard; sends on a worker."""
    found = getattr(host, "_radio_scrobble", None)
    if found is None:
        return
    station = _station(host)
    if station is None or not _wanted(host) or not found.accounts.services():
        found.tracker.reset()
        _stop_timer(found)
        return
    moment = time.time() if now is None else now
    result = found.tracker.tick(_station_key(station), now=moment, behind=_behind(host))
    for listen in result.heard:
        for service in found.accounts.services():
            found.fresh.append((service, listen))
    if result.started is not None:
        _send_now_playing(host, found, result.started)
    _send_due(host, found, now=moment)


def _send_now_playing(host: Any, found: ScrobbleState, listen: Listen) -> None:
    tasks = getattr(host, "_task_manager", None)
    if tasks is None:
        return
    accounts = found.accounts
    safe_mode = bool(getattr(host, "_safe_mode", False))

    def _work(**_kwargs: Any) -> None:
        scrobbling.send_now_playing(accounts, listen, safe_mode=safe_mode)

    tasks.submit(
        "radio-scrobble-now-playing",
        _work,
        on_success=lambda *_a: None,
        on_failure=lambda *_a: None,
    )


def _send_due(host: Any, found: ScrobbleState, *, now: float) -> None:
    if found.sending:
        return
    services = found.accounts.services()
    fresh = list(found.fresh)
    if not fresh and not any(found.queue.has_due(service, now=now) for service in services):
        return
    tasks = getattr(host, "_task_manager", None)
    if tasks is None:
        return
    found.fresh = []
    found.sending = True
    accounts = found.accounts
    safe_mode = bool(getattr(host, "_safe_mode", False))

    def _work(**_kwargs: Any) -> Any:
        # Queued here, on the worker, so the file write never touches the UI thread.
        for service, listen in fresh:
            found.queue.add(service, listen)
        return scrobbling.submit_due(found.queue, accounts, now=now, safe_mode=safe_mode)

    def _done(_op: str, results: Any) -> None:
        host._wx.CallAfter(_after_send, host, found, list(results or []))

    def _failed(*_args: Any) -> None:
        host._wx.CallAfter(_after_send, host, found, [])

    tasks.submit("radio-scrobble-send", _work, on_success=_done, on_failure=_failed)


def _after_send(host: Any, found: ScrobbleState, results: list[Any]) -> None:
    """Back on the UI thread: say a lost sign-in once, and nothing else."""
    found.sending = False
    for service, outcome in results:
        if outcome.kind != SIGN_IN or service in found.warned:
            continue
        found.warned.add(service)
        detail = outcome.detail or (
            f"{scrobbling.service_name(service)} no longer accepts Quill Radio's sign-in."
        )
        host._announce(f"Scrobbling: {detail} The songs wait until then.")


__all__ = ["TICK_MS", "ScrobbleState", "on_title", "refresh_accounts", "state", "tick"]
