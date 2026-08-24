"""What the Podcast Index knows about a show, beyond which show you meant.

:mod:`quill.core.podcasts.podcast_index` answers *"which show did you mean"* --
a search, returning the same ``PodcastSearchResult`` iTunes returns, so no
consumer can tell which directory replied. This module answers the three
questions a search cannot, and they are the reason the index is worth asking at
all:

* **What IS this show?** Categories, language, episode count, when it last
  published, the publisher's own support link, and whether the index can still
  read the feed. A details panel had nothing to show for a show but its address.
* **What has it published -- without subscribing to it?** The gap the
  podcast-directory review named: seeing a show's episodes meant committing to
  it first. :func:`episodes_for_feed` answers for any feed, with durations,
  dates, episode and season numbers, and the Podcasting 2.0 transcript and
  chapters links per episode.
* **What is there at all?** :func:`trending` and :func:`categories` make the
  index browsable rather than only searchable -- a hundred and twelve
  categories, and a trending list that changes hourly.

Split from ``podcast_index`` under GATE-11 (extract, never rebaseline) and it
reads better apart anyway: that module is *the client* -- credentials, the
signature, the one egress site, the search -- and this is *the catalogue built
on it*. Every request here goes through that module's :func:`_http_json`, so
there is still exactly one reviewed egress site, one credential resolution and
one Safe Mode refusal.

Answers are cached through :mod:`quill.core.radio.directory_cache`: a
directory's facts about a show change on the order of days, and a browse tree
must not spend a request per keypress. wx-free, strict-typed, pure except for
the fetch.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

from quill.core.podcasts.podcast_index import (
    API_ROOT,
    SIGNUP_URL,
    PodcastIndexError,
    _http_json,
    auth_headers,
    credentials,
    refuse_in_safe_mode,
)
from quill.core.radio import directory_cache

#: How long a catalogue answer stays fresh.
SHOW_MAX_AGE = 24 * 3600
EPISODES_MAX_AGE = 3 * 3600
TRENDING_MAX_AGE = 3600
CATEGORIES_MAX_AGE = 7 * 24 * 3600

#: Rows per catalogue request. The API serves more; a list nobody can arrow
#: through is not a better answer.
CATALOG_LIMIT = 60
_MAX_LIMIT = 200


# Search answers "which show did you mean". These answer "what IS this show",
# "what has it published", and "what is there at all" -- the three questions a
# directory can answer and a bare feed address cannot.


@dataclass(frozen=True, slots=True)
class IndexShow:
    """A show as the catalogue describes it, rather than as a feed address."""

    feed_id: int = 0
    title: str = ""
    author: str = ""
    description: str = ""
    feed_url: str = ""
    homepage: str = ""
    artwork_url: str = ""
    language: str = ""
    categories: tuple[str, ...] = ()
    episode_count: int = 0
    #: Unix seconds of the newest episode the index has seen. 0 = unknown.
    last_published: int = 0
    explicit: bool = False
    #: The index's own verdict on whether it can still read the feed. True is
    #: worth saying out loud: a show that stopped being readable is not a show
    #: somebody should subscribe to without knowing.
    dead: bool = False
    #: The publisher's own support link (Podcasting 2.0 ``<podcast:funding>``).
    funding_url: str = ""
    funding_label: str = ""

    @property
    def display_name(self) -> str:
        return self.title or self.feed_url

    @property
    def summary(self) -> str:
        """The one line a browse row speaks after the title.

        Facts only, in the order somebody choosing a show wants them: who makes
        it, how much there is, what it is about, and -- only when it matters --
        that the index can no longer read it.
        """
        parts: list[str] = []
        if self.author:
            parts.append(self.author)
        if self.episode_count:
            parts.append(f"{self.episode_count} episode{'' if self.episode_count == 1 else 's'}")
        if self.categories:
            parts.append(", ".join(self.categories[:3]))
        if self.dead:
            parts.append("the index can no longer read this feed")
        return ", ".join(parts)


@dataclass(frozen=True, slots=True)
class IndexEpisode:
    """One episode of a show you have not subscribed to."""

    episode_id: int = 0
    title: str = ""
    description: str = ""
    audio_url: str = ""
    #: Unix seconds. 0 = the feed published no date.
    published: int = 0
    duration_seconds: int = 0
    episode_number: int = 0
    season: int = 0
    #: "full", "trailer" or "bonus", as the feed declared it.
    episode_type: str = ""
    explicit: bool = False
    artwork_url: str = ""
    homepage: str = ""
    #: Podcasting 2.0, and the reason this directory is worth asking: a
    #: transcript and a chapters document, per episode, without a subscription.
    transcript_url: str = ""
    transcript_type: str = ""
    chapters_url: str = ""

    @property
    def display_name(self) -> str:
        return self.title or "Untitled episode"


@dataclass(frozen=True, slots=True)
class IndexCategory:
    """One category in the index's own taxonomy."""

    category_id: int = 0
    name: str = ""


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return 0
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return 0


def _as_text(value: object) -> str:
    return str(value).strip() if isinstance(value, (str, int, float)) else ""


def show_from_json(row: object) -> IndexShow:
    """One ``feed`` object as an :class:`IndexShow` (pure, total)."""
    if not isinstance(row, dict):
        return IndexShow()
    raw_categories = row.get("categories")
    if isinstance(raw_categories, dict):
        names = tuple(_as_text(name) for name in raw_categories.values() if _as_text(name))
    elif isinstance(raw_categories, list):
        names = tuple(_as_text(name) for name in raw_categories if _as_text(name))
    else:
        names = ()
    funding = row.get("funding")
    funding = funding if isinstance(funding, dict) else {}
    return IndexShow(
        feed_id=_as_int(row.get("id")),
        title=_as_text(row.get("title")),
        author=_as_text(row.get("author")) or _as_text(row.get("ownerName")),
        description=_as_text(row.get("description")),
        feed_url=_as_text(row.get("url")),
        homepage=_as_text(row.get("link")),
        artwork_url=_as_text(row.get("artwork")) or _as_text(row.get("image")),
        language=_as_text(row.get("language")),
        categories=names,
        episode_count=_as_int(row.get("episodeCount")),
        last_published=_as_int(row.get("newestItemPubdate")) or _as_int(row.get("lastUpdateTime")),
        explicit=bool(row.get("explicit")),
        dead=bool(_as_int(row.get("dead"))),
        funding_url=_as_text(funding.get("url")),
        funding_label=_as_text(funding.get("message")),
    )


def episode_from_json(row: object) -> IndexEpisode:
    """One ``item`` object as an :class:`IndexEpisode` (pure, total)."""
    if not isinstance(row, dict):
        return IndexEpisode()
    transcript_url = _as_text(row.get("transcriptUrl"))
    transcript_type = ""
    transcripts = row.get("transcripts")
    if isinstance(transcripts, list) and transcripts:
        first = transcripts[0]
        if isinstance(first, dict):
            transcript_url = _as_text(first.get("url")) or transcript_url
            transcript_type = _as_text(first.get("type"))
    return IndexEpisode(
        episode_id=_as_int(row.get("id")),
        title=_as_text(row.get("title")),
        description=_as_text(row.get("description")),
        audio_url=_as_text(row.get("enclosureUrl")),
        published=_as_int(row.get("datePublished")),
        duration_seconds=_as_int(row.get("duration")),
        episode_number=_as_int(row.get("episode")),
        season=_as_int(row.get("season")),
        episode_type=_as_text(row.get("episodeType")),
        explicit=bool(_as_int(row.get("explicit"))),
        artwork_url=_as_text(row.get("image")) or _as_text(row.get("feedImage")),
        homepage=_as_text(row.get("link")),
        transcript_url=transcript_url,
        transcript_type=transcript_type,
        chapters_url=_as_text(row.get("chaptersUrl")),
    )


def shows_from_json(payload: object) -> list[IndexShow]:
    """Every show in a ``feeds``/``feed`` response (pure, total).

    Both shapes, because the API uses ``feeds`` for a list and ``feed`` for a
    single lookup, and a parser that knows only one of them silently answers
    nothing for the other.
    """
    if not isinstance(payload, dict):
        return []
    rows: object = payload.get("feeds")
    if rows is None:
        rows = payload.get("feed")
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return []
    shows = [show_from_json(row) for row in rows]
    return [show for show in shows if show.feed_url or show.title]


def episodes_from_json(payload: object) -> list[IndexEpisode]:
    """Every episode in an ``items`` response (pure, total)."""
    if not isinstance(payload, dict):
        return []
    rows = payload.get("items")
    if not isinstance(rows, list):
        return []
    episodes = [episode_from_json(row) for row in rows]
    return [episode for episode in episodes if episode.audio_url or episode.title]


def categories_from_json(payload: object) -> list[IndexCategory]:
    """The taxonomy from ``/categories/list`` (pure, total), sorted by name."""
    if not isinstance(payload, dict):
        return []
    rows = payload.get("feeds")
    if not isinstance(rows, list):
        return []
    found = [
        IndexCategory(category_id=_as_int(row.get("id")), name=_as_text(row.get("name")))
        for row in rows
        if isinstance(row, dict) and _as_text(row.get("name"))
    ]
    return sorted(found, key=lambda category: category.name.lower())


def _catalog_json(path: str, params: dict[str, object]) -> object:
    """One signed catalogue GET. Same egress site, same rules as the search."""
    key, secret = credentials()
    if not (key and secret):
        raise PodcastIndexError(
            "This build has no Podcast Index credential. A free developer key from "
            f"{SIGNUP_URL} can be added in Podcast Settings."
        )
    url = f"{API_ROOT}{path}?{urllib.parse.urlencode(params)}"
    return _http_json(url, auth_headers(key, secret))


def _limit(limit: int) -> int:
    return max(1, min(_MAX_LIMIT, int(limit or CATALOG_LIMIT)))


def show_facts(
    feed_url: str, *, safe_mode: bool = False, refresh: bool = False
) -> IndexShow | None:
    """What the catalogue knows about one feed, or ``None``.

    The answer a details panel wants and a feed address cannot give: who makes
    it, what it is about, how many episodes there are, what language it is in,
    where to support it, and whether the index can still read it.
    """
    refuse_in_safe_mode(safe_mode)
    url = (feed_url or "").strip()
    if not url:
        return None
    rows, _age = directory_cache.resolve(
        f"podcastindex:feed:{url}",
        lambda: [
            _show_dict(show)
            for show in shows_from_json(_catalog_json("/podcasts/byfeedurl", {"url": url}))
        ],
        max_age_seconds=SHOW_MAX_AGE,
        refresh=refresh,
        empty=[],
    )
    shows = [show_from_json(row) for row in rows or []]
    return shows[0] if shows else None


def episodes_for_feed(
    feed_url: str,
    *,
    limit: int = CATALOG_LIMIT,
    safe_mode: bool = False,
    refresh: bool = False,
) -> list[IndexEpisode]:
    """What a show has published -- **without subscribing to it**.

    The gap the podcast-directory review named: the only way to see a show's
    episodes was to subscribe first, which is a commitment made in order to ask
    a question.
    """
    refuse_in_safe_mode(safe_mode)
    url = (feed_url or "").strip()
    if not url:
        return []
    rows, _age = directory_cache.resolve(
        f"podcastindex:episodes:{url}:{_limit(limit)}",
        lambda: [
            _episode_dict(episode)
            for episode in episodes_from_json(
                _catalog_json("/episodes/byfeedurl", {"url": url, "max": _limit(limit)})
            )
        ],
        max_age_seconds=EPISODES_MAX_AGE,
        refresh=refresh,
        empty=[],
    )
    return [episode_from_json(row) for row in rows or []]


def trending(
    *,
    limit: int = CATALOG_LIMIT,
    category: str = "",
    language: str = "",
    safe_mode: bool = False,
    refresh: bool = False,
) -> list[IndexShow]:
    """What is being talked about now, optionally narrowed to one category."""
    refuse_in_safe_mode(safe_mode)
    params: dict[str, object] = {"max": _limit(limit)}
    if category.strip():
        params["cat"] = category.strip()
    if language.strip():
        params["lang"] = language.strip()
    rows, _age = directory_cache.resolve(
        f"podcastindex:trending:{category.strip().lower()}:{language.strip().lower()}",
        lambda: [
            _show_dict(show)
            for show in shows_from_json(_catalog_json("/podcasts/trending", params))
        ],
        max_age_seconds=TRENDING_MAX_AGE,
        refresh=refresh,
        empty=[],
    )
    return [show_from_json(row) for row in rows or []]


def categories(*, safe_mode: bool = False, refresh: bool = False) -> list[IndexCategory]:
    """The index's own taxonomy -- a hundred and twelve of them, cached weekly."""
    refuse_in_safe_mode(safe_mode)
    rows, _age = directory_cache.resolve(
        "podcastindex:categories",
        lambda: [
            {"id": found.category_id, "name": found.name}
            for found in categories_from_json(_catalog_json("/categories/list", {}))
        ],
        max_age_seconds=CATEGORIES_MAX_AGE,
        refresh=refresh,
        empty=[],
    )
    return [
        IndexCategory(category_id=_as_int(row.get("id")), name=_as_text(row.get("name")))
        for row in rows or []
        if isinstance(row, dict) and _as_text(row.get("name"))
    ]


# A cache entry has been through JSON, so a dataclass comes back a dict. These
# two write the shape the parsers above read, which keeps one description of
# the wire format instead of two (the boundary note directory_cache carries).


def _show_dict(show: IndexShow) -> dict[str, object]:
    return {
        "id": show.feed_id,
        "title": show.title,
        "author": show.author,
        "description": show.description,
        "url": show.feed_url,
        "link": show.homepage,
        "artwork": show.artwork_url,
        "language": show.language,
        "categories": list(show.categories),
        "episodeCount": show.episode_count,
        "newestItemPubdate": show.last_published,
        "explicit": show.explicit,
        "dead": int(show.dead),
        "funding": {"url": show.funding_url, "message": show.funding_label},
    }


def _episode_dict(episode: IndexEpisode) -> dict[str, object]:
    return {
        "id": episode.episode_id,
        "title": episode.title,
        "description": episode.description,
        "enclosureUrl": episode.audio_url,
        "datePublished": episode.published,
        "duration": episode.duration_seconds,
        "episode": episode.episode_number,
        "season": episode.season,
        "episodeType": episode.episode_type,
        "explicit": int(episode.explicit),
        "image": episode.artwork_url,
        "link": episode.homepage,
        "transcripts": [{"url": episode.transcript_url, "type": episode.transcript_type}]
        if episode.transcript_url
        else [],
        "chaptersUrl": episode.chapters_url,
    }
