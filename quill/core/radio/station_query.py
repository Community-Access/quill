"""What a listener typed, taken apart so every directory can be asked properly.

A station search is not a string. "Sunny 105.7 Gulf Shores Alabama" is a brand,
a frequency, a city and a state, and the directories index only two of those --
so sending the whole sentence to a name search is asking a question the database
cannot answer. Two ACB members reported five stations on 2026-09-14; three of
the five were unreachable, and every failure was a shape this module knows:

* **A brand the directory does not use.** Radio Browser lists Sunny 105.7 as
  "WCSN 105.7 FM Orange Beach". No amount of typing "Sunny" reaches it. But
  ``105.7`` *narrowed to Alabama* has exactly one answer, which is why
  :func:`narrowed_searches` exists: the place is the second axis a name search
  is missing.
* **A frequency written the way a person says it.** "14.90 AM" is 1490, "1009"
  is 100.9, "105-9" is 105.9 and "105,7" is 105.7. A directory stores one
  spelling and a listener types another.
* **A city in the middle of a name query.** "Sunny 105.7 Gulf Shores" matches
  nothing anywhere, because no station has the city in its name.
* **A trailing band word.** "rock 105 fm" loses the station that "rock 105"
  finds -- TuneIn matches the extra word against every "105 FM" on earth.

So: parse it, and ask several **narrower** questions instead of one wide one.

Three rules the aggression obeys. **What the user typed is always asked first**
(:func:`variants`), so nothing that worked before stops working -- the extra
queries only add rows. **The merged list is ranked locally** (:func:`rank`),
because a directory ranks against the query it was sent and we sent it four;
only this side of the wire knows what the person actually asked. And **a fact
never has to be typed the one right way**: every spelling this module has seen
in the wild resolves to the spelling the directories use.

Matching is on **tokens, never substrings**: "wdan" is inside "NewDanceRadio",
and a substring match would have put a Latvian dance stream above the Danville
talk station it was meant to find.

Pure and wx-free: no network, no wx, no I/O. The fan-out that spends these
queries lives in :mod:`quill.core.radio.directory_search`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

__all__ = [
    "StationQuery",
    "narrowed_searches",
    "parse",
    "rank",
    "score",
    "tokens",
    "variants",
]

#: US states and DC, by lower-case name and by abbreviation. Radio Browser's
#: ``state`` field carries the full name, so that is what this resolves to.
_STATES: dict[str, str] = {}
for _abbr, _name in (
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"),
    ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"),
    ("DC", "District of Columbia"), ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"),
    ("ID", "Idaho"), ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"),
    ("KS", "Kansas"), ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"),
    ("MD", "Maryland"), ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"),
    ("MS", "Mississippi"), ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"),
    ("NV", "Nevada"), ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"),
    ("NY", "New York"), ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"),
    ("OK", "Oklahoma"), ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"),
    ("SC", "South Carolina"), ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"),
    ("UT", "Utah"), ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"),
    ("WV", "West Virginia"), ("WI", "Wisconsin"), ("WY", "Wyoming"),
):  # fmt: skip
    _STATES[_abbr] = _name
    _STATES[_name.lower()] = _name

#: Two-letter state abbreviations that are also ordinary words. These count as a
#: state only when they were **shouted** ("Champaign, IL"), never in a
#: lower-case sentence -- "rock in the mix" is not a search in Indiana.
_WORDLIKE_ABBREVIATIONS = frozenset({
    "IN",
    "OR",
    "ME",
    "HI",
    "OK",
    "OH",
    "LA",
    "DE",
    "ID",
    "MA",
    "PA",
    "MD",
    "MS",
    "MT",
    "NE",
    "SC",
    "VA",
    "AL",
    "AR",
    "CA",
    "CO",
    "MI",
    "MN",
    "MO",
    "NV",
    "SD",
    "WA",
    "WI",
})

#: Countries whose name in a query means "narrow to this country" for a
#: directory that can filter by one. Radio Browser's own spelling on the right.
_COUNTRIES: dict[str, str] = {
    "usa": "The United States Of America",
    "us": "The United States Of America",
    "u.s.": "The United States Of America",
    "united states": "The United States Of America",
    "america": "The United States Of America",
    "canada": "Canada",
    "uk": "The United Kingdom Of Great Britain And Northern Ireland",
    "england": "The United Kingdom Of Great Britain And Northern Ireland",
    "scotland": "The United Kingdom Of Great Britain And Northern Ireland",
    "wales": "The United Kingdom Of Great Britain And Northern Ireland",
    "britain": "The United Kingdom Of Great Britain And Northern Ireland",
    "ireland": "Ireland",
    "australia": "Australia",
    "new zealand": "New Zealand",
    "mexico": "Mexico",
    "germany": "Germany",
    "france": "France",
    "spain": "Spain",
    "italy": "Italy",
    "netherlands": "The Netherlands",
    "brazil": "Brazil",
    "india": "India",
    "japan": "Japan",
}

#: Four-letter English words that begin with K or W and are not callsigns. A
#: false callsign only costs one extra query, but "west" and "wind" turn up in
#: station names often enough to be worth not asking about.
_NOT_CALLSIGNS = frozenset({
    "week",
    "well",
    "went",
    "were",
    "west",
    "what",
    "when",
    "whom",
    "wide",
    "wife",
    "wild",
    "will",
    "wind",
    "wine",
    "wing",
    "wise",
    "wish",
    "with",
    "word",
    "work",
    "worn",
    "wave",
    "warm",
    "walk",
    "wall",
    "want",
    "keep",
    "kept",
    "kick",
    "kids",
    "kind",
    "king",
    "kiss",
    "knew",
    "know",
    "was",
    "way",
    "who",
    "why",
    "win",
    "key",
})

#: The medium, not the station. Dropped from the brand, and from the query sent
#: to a directory that matches every word.
_BAND_WORDS = frozenset({"am", "fm"})

#: Openers people type that are addressed to the app rather than to the
#: directory: "play wbgl", "listen to rock 105", "find sunny 105.7".
_LEAD_FILLER = (
    "listen to the",
    "listen to",
    "listen",
    "please play",
    "play the",
    "play",
    "tune in to",
    "tune into",
    "tune to",
    "search for",
    "search",
    "find me",
    "find the",
    "find",
    "look for",
    "open",
    "station",
    "radio station",
)

#: Ignored when counting how much of a brand a station name matched: every
#: second station is "The" something, so matching "the" is worth nothing.
_BRAND_STOPWORDS = frozenset({"the", "a", "an", "of", "and", "on", "at", "to", "for"})

_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
_NUMBER = re.compile(r"^\d{2,4}(?:\.\d{1,2})?$")
_DIGIT_SEPARATOR = re.compile(r"(?<=\d)\s*[,\-–/]\s*(?=\d{1,2}\b)")
_LETTER_DIGIT = re.compile(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])")


def _prepared(text: str) -> str:
    """*text*, lower-cased and spelled the way the tokeniser expects.

    Four repairs, each one a shape somebody actually types: a European decimal
    comma and a branding hyphen both become a decimal point ("105,7" and
    "105-9"), a run-together letter/digit pair is separated ("Sunny105.7",
    "1490AM", "Q107"), and an opener addressed to the app is dropped.
    """
    lowered = text.strip().lower()
    for filler in _LEAD_FILLER:
        if lowered.startswith(filler + " "):
            lowered = lowered[len(filler) + 1 :].strip()
            break
    lowered = _DIGIT_SEPARATOR.sub(".", lowered)
    return _LETTER_DIGIT.sub(" ", lowered)


def tokens(text: str) -> set[str]:
    """The words and numbers in *text*, normalised. Token, never substring.

    Public because both sides of a match must agree on what a word is: the
    query is tokenised here and so is every station name it is scored against.
    """
    return set(_TOKEN.findall(_prepared(text)))


@dataclass(frozen=True, slots=True)
class StationQuery:
    """One typed search, taken apart. Every field is normalised and may be
    empty; :attr:`raw` is always exactly what the user typed."""

    raw: str
    callsign: str = ""
    #: "105.7" or "1490" -- the spelling the directories use.
    frequency: str = ""
    #: "FM", "AM", or empty when nothing said.
    band: str = ""
    #: The words that look like the station's own name, lower-case.
    brand: str = ""
    #: The words that look like where it is, lower-case.
    place: str = ""
    #: The full state name, resolved from a name or a shouted abbreviation.
    state: str = ""
    #: The country, in the directory's own spelling.
    country: str = ""

    @property
    def alt_frequency(self) -> str:
        """The other spelling of :attr:`frequency` (``100.9`` <-> ``1009``)."""
        if not self.frequency:
            return ""
        return self.frequency.replace(".", "") if "." in self.frequency else ""

    @property
    def frequencies(self) -> tuple[str, ...]:
        """Every spelling of the frequency a station name might carry."""
        return tuple(f for f in (self.frequency, self.alt_frequency) if f)


def _is_callsign(word: str) -> bool:
    if len(word) not in (3, 4) or not word.isalpha():
        return False
    if word[0] not in "kwKW":
        return False
    return word.lower() not in _NOT_CALLSIGNS


def _normalise_frequency(token: str, band: str) -> str:
    """One number token, as a directory would spell it.

    AM is whole kilohertz, so a decimal point in an AM number is somebody
    reading "fourteen ninety" off the dial. FM is one decimal, so a four-digit
    number in the FM band is the point left out.
    """
    if "." in token:
        if band == "AM":
            return token.replace(".", "")
        value = float(token)
        return f"{value:g}" if 87.0 <= value <= 108.5 else token.replace(".", "")
    if band != "AM" and len(token) == 4 and 875 <= int(token) <= 1080:
        return f"{int(token) / 10:g}"
    return token


def _state_of(word: str, original: str, *, last: bool) -> str:
    """The state *word* names, or "".

    An abbreviation that is also a word ("IN", "ME", "OR") counts only when it
    was shouted or when it is the last thing typed -- "rock in the mix" is not
    a search in Indiana, and "sunny 105.7 gulf shores al" is a search in
    Alabama.
    """
    upper = word.upper()
    if len(word) == 2 and upper in _STATES:
        if original.isupper() or upper not in _WORDLIKE_ABBREVIATIONS:
            return _STATES[upper]
        return _STATES[upper] if last else ""
    return _STATES.get(word, "")


def parse(text: str) -> StationQuery:
    """Take *text* apart into a :class:`StationQuery`. Pure; never raises.

    The split between brand and place is positional, because that is how people
    write a station: whatever sits **before** the frequency is its name
    ("Sunny 105.7", "Rock 105") and whatever follows is where it is ("105.7 Gulf
    Shores"). When the frequency leads, the name is what follows it instead
    ("100.9 The Mix").
    """
    raw = text.strip()
    prepared = _prepared(raw)
    words = _TOKEN.findall(prepared)
    if not words:
        return StationQuery(raw=raw)
    # The user's own capitalisation, aligned to the normalised words, so a
    # shouted state abbreviation can still be told from the word it spells.
    originals = re.findall(r"[A-Za-z0-9]+(?:\.[0-9]+)?", _DIGIT_SEPARATOR.sub(".", raw.strip()))

    country = ""
    for phrase, resolved in _COUNTRIES.items():
        if re.search(rf"\b{re.escape(phrase)}\b", prepared):
            country = resolved
            break

    band = ""
    for word in words:
        if word in _BAND_WORDS:
            band = word.upper()
            break

    callsign = ""
    state = ""
    frequency = ""
    frequency_at = -1
    rest: list[tuple[int, str]] = []
    for index, word in enumerate(words):
        original = originals[index] if index < len(originals) else word
        if word in _BAND_WORDS:
            continue
        if not state:
            found = _state_of(word, original, last=index == len(words) - 1)
            if found:
                state = found
                continue
        if not frequency and _NUMBER.match(word):
            frequency = _normalise_frequency(word, band)
            frequency_at = index
            continue
        if not callsign and _is_callsign(word):
            callsign = word.upper()
            continue
        rest.append((index, word))

    # Nobody types the band when the number already says it: a decimal is FM,
    # and four digits in the broadcast range are AM.
    if not band and frequency:
        band = "AM" if "." not in frequency and 530 <= int(frequency) <= 1700 else "FM"

    if frequency_at < 0:
        brand_words = [w for _i, w in rest]
        place_words: list[str] = []
    else:
        head = [w for i, w in rest if i < frequency_at]
        tail = [w for i, w in rest if i > frequency_at]
        brand_words, place_words = (head, tail) if head else (tail, [])

    # A multi-word state or country consumed as prose leaves its own words in
    # the place list ("new york", "united states"); they are not brand words.
    if state or country:
        spoken = {w for token in (state.lower(), country.lower()) for w in token.split()}
        brand_words = [w for w in brand_words if w not in spoken] or brand_words
        place_words = [w for w in place_words if w not in spoken]

    return StationQuery(
        raw=raw,
        callsign=callsign,
        frequency=frequency,
        band=band,
        brand=" ".join(brand_words),
        place=" ".join(place_words),
        state=state,
        country=country,
    )


def _ordered(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(v for v in (x.strip() for x in values) if v))


def variants(query: StationQuery) -> tuple[str, ...]:
    """Name searches to send, best first, de-duplicated.

    The first is always :attr:`StationQuery.raw`. A caller with a round-trip
    budget takes the first N and loses only breadth, never what was asked.
    """
    brand, frequency = query.brand, query.frequency
    leads = bool(frequency) and _TOKEN.findall(_prepared(query.raw))[:1] == [
        frequency if "." in frequency else frequency
    ]
    pairs: list[str] = []
    if brand and frequency:
        pairs.append(f"{frequency} {brand}" if leads else f"{brand} {frequency}")
        if query.alt_frequency:
            alt = query.alt_frequency
            pairs.append(f"{alt} {brand}" if leads else f"{brand} {alt}")
    # The brand plus the callsign is what a directory that files a station
    # under both ("WGFM ROCK 105") answers to.
    both = f"{query.callsign} {brand}".strip() if query.callsign and brand else ""
    return _ordered([
        query.raw,
        query.callsign,
        *pairs,
        both,
        brand,
        frequency,
        query.alt_frequency,
    ])


def narrowed_searches(query: StationQuery) -> tuple[tuple[str, str, str], ...]:
    """``(name, state, country)`` triples for a directory that can filter.

    This is the one that finds a station whose brand name the directory never
    recorded: a frequency is ambiguous across a country and unique inside a
    state.
    """
    if not (query.state or query.country):
        return ()
    state, country = query.state, query.country
    triples = [
        (query.frequency, state, country),
        (query.alt_frequency, state, country),
        (query.brand, state, country),
        (query.callsign, state, country),
    ]
    return tuple(dict.fromkeys((a.strip(), b, c) for a, b, c in triples if a.strip()))


def score(name: str, query: StationQuery, *, country: str = "", tags: tuple[str, ...] = ()) -> int:
    """How well a station answers *query*. Higher is better; pure.

    The weights are an ordering, not a measurement: an exact name beats a
    callsign, a callsign beats a frequency, a frequency beats a brand word, and
    a place word is a tie-breaker between stations that matched the same facts.
    """
    if not query.raw:
        return 0
    name_tokens = tokens(name)
    if name_tokens and name_tokens == tokens(query.raw):
        return 1000
    total = 0
    if query.callsign and query.callsign.lower() in name_tokens:
        total += 200
    if query.frequencies and name_tokens.intersection(query.frequencies):
        total += 120
    brand_words = [w for w in query.brand.split() if w not in _BRAND_STOPWORDS]
    matched = [w for w in brand_words if w in name_tokens]
    total += 40 * len(matched)
    if brand_words and len(matched) == len(brand_words):
        total += 60
    # The place is a tie-breaker, and it is worth having twice: a station's own
    # name often carries its city, and its tags often carry its state.
    place_words = [w for w in query.place.split() if w not in _BRAND_STOPWORDS]
    total += 20 * len([w for w in place_words if w in name_tokens])
    if query.state:
        state_words = set(query.state.lower().split())
        haystack = name_tokens.union(*(tokens(t) for t in tags)) if tags else name_tokens
        total += 25 * len(state_words & haystack)
    if query.country and country and query.country.lower() == country.lower():
        total += 15
    if total:
        # Everything else being equal, the shorter name is the station and the
        # longer one is a programme about it. "WDAN-AM" and "7-14-26 Bloomdaddy,
        # Sam & Otis - Bloomdaddy wDan Veroni" both contain the callsign, and
        # only one of them is a radio station. Capped, and never applied to a
        # row that matched nothing, so the unmatched tail keeps its own order.
        total -= min(40, 4 * len(name_tokens - tokens(query.raw)))
    return total


def _row_score(row: Any, query: StationQuery) -> tuple[int, int, int]:
    """The full sort key for one row: relevance, then whether it plays, then how
    many people voted for it.

    Relevance decides the order; the other two only break a tie. A station the
    directory's own checker could not play is pushed below an equally relevant
    one that it could -- the most likely thing the listener wants is the station
    that both matches *and* works.
    """
    relevance = score(
        getattr(row, "name", "") or "",
        query,
        country=getattr(row, "country", "") or "",
        tags=tuple(getattr(row, "tags", ()) or ()),
    )
    # A row the directory returned from a search narrowed to the place the
    # listener named is in that place as a matter of record, not of wording --
    # worth more than any word its name happens to share, because the station
    # this rescues ("WCSN 105.7 FM Orange Beach" for "Sunny 105.7 Gulf Shores")
    # shares none.
    if relevance and getattr(row, "place_confirmed", False):
        relevance += 150
    checked = getattr(row, "last_check_ok", None)
    health = 0 if checked is None else (1 if checked else -1)
    votes = int(getattr(row, "votes", 0) or 0)
    return (relevance, health, votes)


def rank[T](stations: list[T], text: str) -> list[T]:
    """Sort *stations* by how likely each is to be the one asked for. Stable.

    Relevance first, then a working stream ahead of a known-dead one, then the
    community's own vote count -- so equally good matches arrive most-listened
    first rather than in whatever order four directories happened to answer.
    An empty query returns the list unchanged, so "browse this category" is
    never re-ordered by accident.
    """
    query = parse(text)
    if not query.raw:
        return stations
    keyed = [(_row_score(row, query), index, row) for index, row in enumerate(stations)]
    keyed.sort(key=lambda item: (-item[0][0], -item[0][1], -item[0][2], item[1]))
    return [row for _key, _index, row in keyed]
