"""Play Random Station and Play Random Favorite: the commands behind the pick.

The choosing is :mod:`quill.core.radio.play_random`; this module gathers the
list and plays the result through the one player. Two commands, because a
button you press without looking must not guess which list you meant:

* **Play Random Favorite** always picks from your Favorites. Places that live in
  the browse tree (a podcast show, a book) are not stations and are never picked.
* **Play Random Station** picks from the list in front of you: the most recently
  opened Search Stations or Find Streams window that is still open and has rows.
  With none open it picks from Favorites, and the sentence says which list it
  used, so the fallback is never a surprise.

Nothing is announced that the screen reader already says: only what was picked
and where from.
"""

from __future__ import annotations

import weakref
from typing import Any

from quill.core.radio import play_random as pr

__all__ = [
    "register_source",
    "play_random_favorite",
    "play_random_station",
    "favorite_stations",
]

# Windows that can offer their list, newest last. Each has ``random_pool()``
# returning ``(pool_name, stations)``; a closed window drops out on its own.
_sources: list[weakref.ReferenceType[Any]] = []


def register_source(window: Any) -> None:
    """A window with a list of stations offers it to Play Random Station."""
    _sources[:] = [ref for ref in _sources if ref() is not None and ref() is not window]
    _sources.append(weakref.ref(window))


def _state(host: Any) -> pr.PlayRandom:
    state = getattr(host, "_radio_play_random", None)
    if state is None:
        state = pr.PlayRandom()
        host._radio_play_random = state
    return state


def favorite_stations(host: Any) -> list[Any]:
    """Favorites that are stations, in the order they are shown."""
    from quill.core.radio.favorites import is_place

    history = host._radio_history
    ordered = host._radio_favorites.favorites_in_display_order(
        history.favorites_sort, history.folder_sort_orders
    )
    return [fav.station for fav in ordered if not is_place(fav.station)]


def _open_pool() -> tuple[str, list[Any]] | None:
    for ref in reversed(_sources):
        window = ref()
        if window is None:
            continue
        try:
            pool, stations = window.random_pool()
        except RuntimeError:  # the window was destroyed meanwhile
            continue
        if stations:
            return pool, list(stations)
    return None


def _label(host: Any, station: Any) -> str:
    """The name the listener already knows: a favorite's own name when it is one."""
    favorites = getattr(host, "_radio_favorites", None)
    key = pr.station_identity(station)
    if favorites is not None:
        for fav in favorites.favorites_in_display_order("manual", {}):
            if pr.station_identity(fav.station) == key:
                return str(fav.display_label)
    return str(getattr(station, "display_name", "") or getattr(station, "name", ""))


def _play(host: Any, stations: list[Any], pool: str) -> bool:
    chosen = _state(host).choose(stations)
    if chosen is None:
        host._announce(pr.empty_sentence(pool))
        return False
    host._radio_controller.play_station(chosen)
    host._announce(pr.chosen_sentence(_label(host, chosen), pool, len(stations)))
    return True


def play_random_favorite(host: Any) -> bool:
    """Play a random favorite; says what it did either way."""
    return _play(host, favorite_stations(host), pr.POOL_FAVORITES)


def play_random_station(host: Any) -> bool:
    """Play a random station from the open list, else from Favorites."""
    pool = _open_pool()
    if pool is None:
        return play_random_favorite(host)
    name, stations = pool
    return _play(host, stations, name)


def streams_pool(
    candidates: Any, shown: Any, page_title: str, favicon: str = ""
) -> tuple[str, list[Any]]:
    """The streams a Find Streams window shows, as stations, in shown order."""
    from quill.ui.radio import find_streams_actions as actions

    stations = [actions.station_for(candidates[i], page_title, favicon) for i in shown]
    return pr.POOL_STREAMS, stations


def play_random_stream(window: Any) -> bool:
    """Ctrl+Alt+M inside Find Streams: a random stream from this window's list."""
    pool, stations = window.random_pool()
    return _play(window._host, stations, pool)
