"""Play Random: pick one station from a list, never the one just played.

Pure and wx-free. The command (``quill/ui/radio/play_random_ui.py``) gathers a
list -- the stations in the open Search Stations or Find Streams window, or your
Favorites -- and asks this module which row to play. Two rules live here, and
both are about trust in a button you press without looking:

* **Never the same station twice in a row when there is a choice.** The last
  pick is remembered for the session (``PlayRandom.last_key``); with two or more
  distinct stations the next pick excludes it. With exactly one station there is
  no choice, so it plays again.
* **One plain sentence.** What it picked and where from: "Playing KEXP, picked
  at random from 12 favorites." Every outcome has a sentence, including an empty
  list, so the key is never silent.

The idea comes from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift,
MIT), re-implemented in QUILL's own code.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "PlayRandom",
    "chosen_sentence",
    "empty_sentence",
    "pick_index",
    "pool_phrase",
    "station_identity",
]

#: The three places a pick can come from, as the sentence says them.
POOL_FAVORITES = "favorites"
POOL_STATIONS = "stations"
POOL_STREAMS = "streams"

_POOL_NOUNS: dict[str, tuple[str, str]] = {
    POOL_FAVORITES: ("favorite", "favorites"),
    POOL_STATIONS: ("station in the list", "stations in the list"),
    POOL_STREAMS: ("stream found", "streams found"),
}


def station_identity(station: Any) -> str:
    """What makes two rows the same station: the directory id, else the stream."""
    uuid = str(getattr(station, "station_uuid", "") or "").strip()
    if uuid:
        return f"id:{uuid}"
    url = str(getattr(station, "stream_url", "") or "").strip().casefold()
    return f"url:{url}"


def pick_index(
    keys: Sequence[str],
    last_key: str = "",
    *,
    rng: Callable[[int], int] | None = None,
) -> int:
    """The index of the row to play, or -1 when there are no rows.

    *keys* is one identity per row. Rows that share the last pick's identity are
    set aside when anything else is left, so a list that holds one station twice
    still never repeats it while another station exists. *rng* maps ``n`` to a
    number in ``range(n)``; tests pass a fake, the app passes nothing.
    """
    if not keys:
        return -1
    choose = rng or (lambda n: random.randrange(n))
    allowed = [i for i, key in enumerate(keys) if not (last_key and key == last_key)]
    if not allowed:  # every row is the station we just played: no choice
        allowed = list(range(len(keys)))
    return allowed[choose(len(allowed))]


def pool_phrase(pool: str, count: int) -> str:
    """ "12 favorites" / "1 favorite", counted and singular-correct."""
    one, many = _POOL_NOUNS.get(pool, _POOL_NOUNS[POOL_STATIONS])
    return f"{count:,} {one if count == 1 else many}"


def chosen_sentence(label: str, pool: str, count: int) -> str:
    """The one sentence after a pick."""
    name = (label or "").strip() or "a station"
    if count <= 1:
        one = _POOL_NOUNS.get(pool, _POOL_NOUNS[POOL_STATIONS])[0]
        return f"Playing {name}, the only {one} there is."
    return f"Playing {name}, picked at random from {pool_phrase(pool, count)}."


def empty_sentence(pool: str) -> str:
    """The sentence when there is nothing to pick from."""
    if pool == POOL_FAVORITES:
        return "You have no favorites to pick from yet. Add a station to your favorites first."
    if pool == POOL_STREAMS:
        return "There are no streams found to pick from. Find some with Find Streams first."
    return "There are no stations in the list to pick from."


@dataclass(slots=True)
class PlayRandom:
    """Remembers the last pick, so the next one differs.

    One lives on the app for the session. It is not saved: a fresh launch may
    start with any station, and nothing about a random pick is worth keeping.
    """

    last_key: str = ""

    def choose(
        self,
        stations: Sequence[Any],
        *,
        rng: Callable[[int], int] | None = None,
    ) -> Any | None:
        """The station to play, or ``None`` for an empty list. Remembers it."""
        index = pick_index([station_identity(s) for s in stations], self.last_key, rng=rng)
        if index < 0:
            return None
        chosen = stations[index]
        self.last_key = station_identity(chosen)
        return chosen
