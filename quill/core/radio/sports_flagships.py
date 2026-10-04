"""Which station carries which team: the shipped flagship list.

"Where do I hear the Tigers?" is one of the commonest reasons anybody opens a
radio app, and no station directory can answer it: Radio Browser knows WXYT as
"97.1 The Ticket" with the tags "sports, talk", and nothing in that says
*baseball*, let alone *Detroit*. So Quill Radio ships the answer, as
``quill/data/sports_flagships.json``: for each team, its league, its sport, a
few other names people use for it, the flagship station(s) the team itself
names, and the public page that says so.

**Nothing here plays.** The file holds call signs and names, never stream
addresses, because a stream address goes stale and a call sign does not. A
match is turned into a playable row at search time, by looking the call sign up
in the station directory (:mod:`quill.core.radio.station_lookup`). A team whose
station the directory does not list simply finds nothing -- which is honest --
rather than a dead link that looks like an answer.

**Cheap and forgiving.** The file is read once, on the first search that needs
it, and kept. A missing file, a file that is not JSON, or an entry with a field
the wrong shape costs that entry (or the whole list), never a search.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "DATA_PATH",
    "FlagshipStation",
    "Team",
    "clear_cache",
    "load_teams",
    "reason_for",
    "station_matches",
    "teams_matching",
]

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "sports_flagships.json"


@dataclass(frozen=True, slots=True)
class FlagshipStation:
    """One station a team names as its radio home."""

    name: str
    call_sign: str
    city: str = ""
    homepage: str = ""
    notes: str = ""

    @property
    def call_base(self) -> str:
        """``WXYT`` for ``WXYT-FM``: the part a directory's name will contain."""
        return re.split(r"[-\s]", self.call_sign.strip().upper(), maxsplit=1)[0]


@dataclass(frozen=True, slots=True)
class Team:
    """A team, how people say its name, and where it is on the radio."""

    team: str
    league: str
    sport: str
    aliases: tuple[str, ...] = ()
    stations: tuple[FlagshipStation, ...] = ()
    source: str = ""

    @property
    def words(self) -> frozenset[str]:
        """Every word a search can find this team by."""
        parts = [self.team, self.league, self.sport, *self.aliases]
        for station in self.stations:
            parts += [station.name, station.call_sign, station.call_base]
            parts.append(station.city.split(",")[0])
        return frozenset(word for part in parts for word in _words(part))


_cache: dict[Path, tuple[Team, ...]] = {}
_lock = threading.Lock()


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").casefold())


def _text(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _station(raw: Any) -> FlagshipStation | None:
    if not isinstance(raw, dict):
        return None
    name, call_sign = _text(raw.get("name")), _text(raw.get("call_sign"))
    if not (name or call_sign):
        return None
    return FlagshipStation(
        name=name,
        call_sign=call_sign,
        city=_text(raw.get("city")),
        homepage=_text(raw.get("homepage")),
        notes=_text(raw.get("notes")),
    )


def _team(raw: Any) -> Team | None:
    if not isinstance(raw, dict) or not _text(raw.get("team")):
        return None
    aliases = raw.get("aliases")
    stations = raw.get("stations")
    parsed = tuple(
        station
        for station in (_station(s) for s in (stations if isinstance(stations, list) else []))
        if station is not None
    )
    if not parsed:
        return None
    return Team(
        team=_text(raw["team"]),
        league=_text(raw.get("league")),
        sport=_text(raw.get("sport")),
        aliases=tuple(_text(a) for a in (aliases if isinstance(aliases, list) else []) if _text(a)),
        stations=parsed,
        source=_text(raw.get("source")),
    )


def parse(raw: Any) -> tuple[Team, ...]:
    """Teams from the file's decoded JSON; anything malformed is skipped."""
    entries = raw.get("teams") if isinstance(raw, dict) else None
    teams = (_team(entry) for entry in (entries if isinstance(entries, list) else []))
    return tuple(team for team in teams if team is not None)


def load_teams(path: Path | None = None) -> tuple[Team, ...]:
    """The flagship list, read once per path and kept. ``()`` when unreadable."""
    where = path or DATA_PATH
    with _lock:
        cached = _cache.get(where)
        if cached is not None:
            return cached
        try:
            teams = parse(json.loads(where.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            teams = ()
        _cache[where] = teams
        return teams


def clear_cache() -> None:
    """Forget what was read (tests, and a file replaced while running)."""
    with _lock:
        _cache.clear()


#: Words that say nothing about *which* team: "Tigers radio station" means
#: "Tigers". "sports" is here too -- every team is a sports team, so on its own
#: it would list them all and make every sports search wait on a hundred lookups.
_FILLER = frozenset(
    "a an and the of in on at for radio station stations fm am flagship sports "
    "team teams game games broadcast broadcasts live network play by".split()
)


def _known(word: str, words: frozenset[str]) -> bool:
    """*word* is one of *words*, allowing for one plural: tiger finds Tigers."""
    if word in words or f"{word}s" in words:
        return True
    return word.endswith("s") and word[:-1] in words


def teams_matching(query: str, teams: tuple[Team, ...] | None = None) -> list[Team]:
    """Teams every meaningful word of *query* describes, in list order.

    "Tigers", "Detroit baseball", "MLB" and "WXYT" all find the Detroit Tigers;
    "Detroit" finds every Detroit team. Whole words only, so "rock" does not
    find the Rockies and "classic rock" finds nothing at all.
    """
    wanted = [word for word in _words(query) if word not in _FILLER]
    if not wanted:
        return []
    pool = load_teams() if teams is None else teams
    return [team for team in pool if all(_known(word, team.words) for word in wanted)]


def reason_for(teams: list[Team]) -> str:
    """The short row note: "carries the Detroit Tigers"."""
    names = [f"the {team.team}" for team in teams]
    if not names:
        return ""
    if len(names) > 3:
        names = [*names[:2], f"{len(names) - 2} more teams"]
    said = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
    return f"carries {said}"


def _address(url: str) -> str:
    text = url.strip().casefold()
    text = re.sub(r"^[a-z]+://", "", text)
    return text.removeprefix("www.").rstrip("/")


def station_matches(station: Any, flagship: FlagshipStation) -> bool:
    """Is this directory row the flagship station?

    By call sign (``WXYT`` as a word of the name), by the station's own
    homepage, or by a name distinctive enough to be safe -- one with a
    frequency in it, so "The Fan" alone never claims every Fan in the country.
    """
    name = str(getattr(station, "name", "") or "")
    homepage = str(getattr(station, "homepage", "") or "")
    words = _words(name)
    base = flagship.call_base.casefold()
    if base and len(base) >= 3 and base in words:
        return True
    if flagship.homepage and homepage and _address(flagship.homepage) == _address(homepage):
        return True
    wanted = _words(flagship.name)
    if len(wanted) < 2 or not any(word.isdigit() for word in wanted):
        return False
    size = len(wanted)
    return any(words[i : i + size] == wanted for i in range(len(words) - size + 1))
