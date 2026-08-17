"""Which browse branches a listener actually wants to see.

Quill Radio 3.0 took Browse Stations from thirteen branches to twenty-five. That
is a good problem and it is still a problem: someone who only ever opens their
local NPR affiliate and ACB Media now arrows past Audius, Mixcloud, ccMixter and
Project Gutenberg every time they open the window. For a screen-reader user that
is not clutter, it is distance.

So every branch can be hidden, and the same rule that governs search applies
here: **a source that is off is not in the tree at all, and is never contacted.**
This is not a display filter over a list that was fetched anyway -- turning off
Internet Archive means Internet Archive's requests do not happen.

The shape deliberately mirrors :mod:`quill.core.radio.search_sources`, down to
the ``normalize``/``is_enabled``/``toggle`` trio, because a listener who has
learned how one of these settings behaves should not have to learn the other.
The two lists are separate on purpose, though: what you want to *search* and what
you want to *browse* are different questions -- searching ten directories at once
costs you nothing but a moment, while browsing ten you never open costs you every
time you open the window.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrowseSourceInfo:
    """One browsable branch, as the settings list describes it."""

    id: str
    label: str
    description: str
    #: Whether it appears by default. The broad station directories and the
    #: accessibility services are on; the specialist libraries are on too,
    #: because a listener cannot choose to keep something they never saw.
    default_on: bool = True
    #: True when opening it reaches the network. Favorites, ACB Media, NFB Radio
    #: and the Networks catalogue are local, so they survive Safe Mode.
    network: bool = True
    #: Grouping for the settings list, so twenty-five checkboxes read as five
    #: short lists rather than one long one.
    group: str = "Stations"


#: Every branch, in tree order, grouped as the settings list shows them.
BROWSE_SOURCES: tuple[BrowseSourceInfo, ...] = (
    BrowseSourceInfo(
        "favorites",
        "Favorites",
        "Your own saved stations and folders.",
        network=False,
        group="Yours",
    ),
    BrowseSourceInfo("popular", "Popular Stations", "Radio Browser's most-voted stations."),
    BrowseSourceInfo("trending", "Trending Now", "What people are listening to today."),
    BrowseSourceInfo("recent", "Recently Added or Changed", "New and just-repaired stations."),
    BrowseSourceInfo("rbcountry", "By Country", "Country, then state or region."),
    BrowseSourceInfo("rblang", "By Language", "Stations by broadcast language."),
    BrowseSourceInfo("rbgenre", "By Genre", "Radio Browser's most-used tags."),
    BrowseSourceInfo("rbcodec", "By Quality", "Stations by codec, highest bitrate first."),
    BrowseSourceInfo(
        "wx", "Weather / NOAA", "NOAA Weather Radio transmitters with an internet feed."
    ),
    BrowseSourceInfo(
        "acb",
        "ACB Media",
        "The American Council of the Blind's ten streams.",
        network=False,
        group="Accessibility",
    ),
    BrowseSourceInfo(
        "nfb",
        "NFB Radio",
        "The National Federation of the Blind's stream.",
        network=False,
        group="Accessibility",
    ),
    BrowseSourceInfo(
        "reading",
        "Radio Reading Services",
        "Services for blind and print-disabled listeners.",
        group="Accessibility",
    ),
    BrowseSourceInfo("soma", "SomaFM", "Curated, commercial-free channels."),
    BrowseSourceInfo("tunein", "TuneIn", "TuneIn's own category tree."),
    BrowseSourceInfo("iheart", "iHeart", "iHeart by city and by genre."),
    BrowseSourceInfo(
        "networks", "Networks", "Well-known broadcasters as one-click nodes.", network=False
    ),
    BrowseSourceInfo("m3u", "Community M3U (Music Genres)", "A community per-genre catalog."),
    BrowseSourceInfo(
        "xiph",
        "Xiph / Icecast Directory",
        "The Icecast yellow pages.",
        # Off by default since 2026-08-15: the directory's beta backend is
        # flapping -- it served ~500 genres on Aug 13-14 and serves nothing
        # today, to every client, on every path (yp.xml included). Hidden for
        # new profiles rather than removed: anyone who turns it on keeps it,
        # and the branch's own empty-state stays honest while the source is
        # down. Flip back to default-on when the backend holds steady;
        # remove outright only after sixty dead days.
        default_on=False,
    ),
    BrowseSourceInfo(
        "myservers",
        "My Servers",
        "Icecast and SHOUTcast servers you add yourself.",
        group="Yours",
    ),
    BrowseSourceInfo(
        "youtube", "YouTube Channels", "Channels you add yourself, as folders.", group="Yours"
    ),
    BrowseSourceInfo(
        "apple",
        "Podcasts (Apple)",
        "Apple's podcast charts and genre tree, keylessly.",
        group="Spoken word",
    ),
    BrowseSourceInfo(
        "archive", "Internet Archive", "Old Time Radio, concerts, lectures.", group="Spoken word"
    ),
    BrowseSourceInfo(
        "librivox",
        "LibriVox Audiobooks",
        "Public-domain audiobooks, by chapter.",
        group="Spoken word",
    ),
    BrowseSourceInfo(
        "gutenberg",
        "Project Gutenberg Audiobooks",
        "Human-read public-domain books.",
        group="Spoken word",
    ),
    BrowseSourceInfo(
        "audiopub",
        "AudioPub",
        "Community audio people made and shared; a Discover shelf of fifty.",
        group="Music",
    ),
    BrowseSourceInfo("audius", "Audius", "Independent music, trending by genre.", group="Music"),
    BrowseSourceInfo(
        "mixcloud", "Mixcloud", "DJ sets and shows; opens in your browser.", group="Music"
    ),
    BrowseSourceInfo(
        "ccmixter", "ccMixter", "Creative Commons music, licence shown per track.", group="Music"
    ),
    BrowseSourceInfo(
        "wikidata",
        "Explore (Wikidata)",
        "By city, format or dial position.",
        default_on=False,
        group="Explore",
    ),
)

_BY_ID = {s.id: s for s in BROWSE_SOURCES}

#: Settings-list group order.
GROUPS: tuple[str, ...] = ("Yours", "Stations", "Accessibility", "Spoken word", "Music", "Explore")


def source(source_id: str) -> BrowseSourceInfo | None:
    """The branch with this id, or ``None``."""
    return _BY_ID.get(source_id)


def label(source_id: str) -> str:
    """The display label for a branch id, falling back to the id itself."""
    info = _BY_ID.get(source_id)
    return info.label if info is not None else source_id


def default_enabled() -> tuple[str, ...]:
    """The branches shown to someone who has never changed the setting."""
    return tuple(s.id for s in BROWSE_SOURCES if s.default_on)


def normalize(values: object) -> tuple[str, ...]:
    """Coerce a stored setting into a valid, ordered set of branch ids (pure).

    ``None`` means "never set" and yields the defaults. Unknown ids are dropped
    so a branch removed in a later release cannot resurrect itself, and the
    result is returned in tree order so the settings list and the tree agree.
    """
    if values is None:
        return default_enabled()
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set, frozenset)):
        return default_enabled()
    wanted = {str(v).strip() for v in values if str(v).strip()}
    return tuple(s.id for s in BROWSE_SOURCES if s.id in wanted)


def is_enabled(enabled: object, source_id: str) -> bool:
    """Whether *source_id* should appear in the tree."""
    return source_id in normalize(enabled)


def toggle(enabled: object, source_id: str) -> tuple[str, ...]:
    """Turn *source_id* on if it is off, or off if it is on (pure)."""
    current = set(normalize(enabled))
    if source_id in current:
        current.discard(source_id)
    else:
        current.add(source_id)
    return normalize(current)


def enable_all() -> tuple[str, ...]:
    """Every branch, for a "Show all" button."""
    return tuple(s.id for s in BROWSE_SOURCES)


def describe_selection(enabled: object) -> str:
    """What the setting currently amounts to, in words (pure).

    Spoken to confirm a change, so it names the count and the extremes plainly
    rather than reading twenty-five labels aloud.
    """
    chosen = normalize(enabled)
    total = len(BROWSE_SOURCES)
    if not chosen:
        return "No browse sources are shown. Browse Stations will be empty."
    if len(chosen) == total:
        return f"All {total} browse sources are shown."
    hidden = total - len(chosen)
    return f"{len(chosen)} of {total} browse sources shown, {hidden} hidden."


def in_groups(enabled: object) -> list[tuple[str, list[tuple[BrowseSourceInfo, bool]]]]:
    """The full list as ``(group, [(source, is_on), ...])`` for the settings UI.

    Grouped so twenty-five checkboxes read as six short lists; a screen-reader
    user navigating by heading gets somewhere useful instead of a wall.
    """
    chosen = set(normalize(enabled))
    grouped: list[tuple[str, list[tuple[BrowseSourceInfo, bool]]]] = []
    for group in GROUPS:
        rows = [(s, s.id in chosen) for s in BROWSE_SOURCES if s.group == group]
        if rows:
            grouped.append((group, rows))
    return grouped
