"""Warm the cached directories in the background, once, when browsing starts.

WHY THIS EXISTS
---------------
Three sources answer a search from data already on this machine -- Live365's
station list (cached a day), Radio Paradise's channels (six hours), SHOUTcast's
genre index (a week) -- but only *after* the first fetch, and the first fetch
used to happen inside the first search or the first branch expand. So the very
search that most needed to feel instant was the one that paid for a 900 KB
sitemap, and "search is slow" was partly "the cache is cold" (asked for
directly, 2026-08-26: *"do it async in the background somehow to collect it
while the user is doing things"*).

Opening Browse Stations now warms those caches on the task manager, once per
run of the app. By the time anybody has arrowed to a branch or typed a query,
the fast pass of Search All Sources answers from memory.

THE RULES IT KEEPS
------------------
* **Once.** A module flag, not a timer: the caches have their own lifetimes and
  re-warming them is their business, not this module's.
* **Only sources that are switched on.** "A source that is off is never
  contacted" is the browse-visibility contract, and a background fetch is
  exactly the kind of contact it exists to prevent.
* **Never in Safe Mode**, which refuses each fetch anyway -- checked here too so
  Safe Mode does not even spawn the task.
* **Failure is silence.** A cold cache is the state the app has always handled;
  a warm-up that failed simply leaves it cold, and the ordinary paths report
  any real outage in their ordinary way (``source_health`` counts it if the
  listener then browses there).

The network calls are the sources' own reviewed egress sites, and their audit
entries name this warm-up as a trigger -- see
``quill/tools/network_egress_entries_radio.py``.
"""

from __future__ import annotations

from typing import Any

#: The sources this warms, by browse-visibility id. Only ones whose whole
#: answer is cached locally belong here: warming a live listing (SHOUTcast's
#: station pages, the rankings) would fetch data that is stale by the time it
#: is read, which is traffic for nothing.
WARMABLE: tuple[str, ...] = ("live365", "radioparadise", "shoutcast", "tv")

_warmed = False


def warm(host: Any) -> bool:
    """Start the one-shot warm-up for *host*'s enabled sources.

    Returns True when a task was submitted -- for tests, and for nothing else.
    Safe to call every time the browse window opens; every call after the first
    is a no-op.
    """
    global _warmed
    if _warmed or getattr(host, "_safe_mode", False):
        return False
    task_manager = getattr(host, "_task_manager", None)
    if task_manager is None:
        return False
    from quill.core.radio import browse_visibility

    enabled = set(browse_visibility.normalize(getattr(host, "_visible_sources", None)))
    wanted = tuple(source_id for source_id in WARMABLE if source_id in enabled)
    if not wanted:
        return False
    _warmed = True

    def _work(**_kwargs: Any) -> tuple[str, ...]:
        from quill.core.radio import iptv, live365, radio_paradise, shoutcast

        fetchers = {
            "live365": live365.fetch_stations,
            "radioparadise": radio_paradise.fetch_stations,
            # The genre index only: SHOUTcast's station lists carry live
            # audience figures and are deliberately never cached.
            "shoutcast": shoutcast.fetch_genres,
            "tv": iptv.fetch_rows,
        }
        warmed: list[str] = []
        for source_id in wanted:
            try:
                fetchers[source_id](safe_mode=False)
                warmed.append(source_id)
            except Exception:  # noqa: BLE001 - a cold cache is the normal, handled state
                continue
        return tuple(warmed)

    task_manager.submit(
        "radio-directory-warmup", _work, on_success=lambda _op, _r: None, on_failure=None
    )
    return True


def reset_for_tests() -> None:
    """Forget that a warm-up ran, so each test starts from a cold app."""
    global _warmed
    _warmed = False
