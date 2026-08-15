"""The Podcasting 2.0 tags Cast was not reading, and what each is actually for.

Cast has read ``podcast:chapters`` and ``podcast:transcript`` for a while and
nothing else from the namespace. The six below were each published by real shows,
sitting in feeds Cast was already downloading and parsing, and being discarded.

None of them is speculative. Each answers a question a listener asks out loud:

* **``podcast:person``** -- *who is on this?* Hosts, co-hosts and guests, with
  their role and a link. A People view is the obvious surface and the cheapest of
  the six.
* **``podcast:soundbite``** -- *what is the good bit?* A publisher-marked
  highlight with a start and a length. This is a **chapter marker in all but
  name**, written by a person, and it is the one that changes the chapter work:
  a feed with soundbites has authored marks even when it publishes no chapter
  document at all.
* **``podcast:liveItem``** -- *is this on right now?* A live audio stream
  delivered inside a podcast feed, which is a radio station wearing a different
  hat. It is the tag that usefully blurs the line between Cast and Quill Radio.
* **``podcast:podroll``** -- *what else does this show recommend?* Feeds the host
  vouches for, which is a far better recommendation than any algorithm here could
  produce.
* **``podcast:funding``** -- *how do I support this?* A link the publisher chose.
  Cast opens it and processes nothing: listening stays free, and QUILL is not
  buying anything, so this does not touch the cost rule.
* **``podcast:location``** -- *where is this about?* Text only. No map is needed
  and none is offered.

**Alternate enclosures** come with them: a second audio source for the same
episode, which is what a low-bandwidth or a lossless option looks like in a feed.

Read with regular expressions over the raw item fragment, deliberately, matching
how ``chapters`` and ``transcript`` are already read here: the feed parser in use
does not surface unknown namespaces, a second full XML parse of every feed on
every refresh is real cost for a large library, and each of these is a shallow
attribute grab. Every parser below is tolerant -- a malformed tag yields nothing
rather than raising, because one bad tag must never cost somebody their feed.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass, field
from dataclasses import fields as dataclass_fields

_ATTR = r'{name}\s*=\s*"([^"]*)"'


def _attr(fragment: str, name: str) -> str:
    match = re.search(_ATTR.format(name=re.escape(name)), fragment, re.IGNORECASE)
    return html.unescape(match.group(1).strip()) if match else ""


def _text(fragment: str) -> str:
    """The text inside one tag, with markup and entities resolved."""
    body = re.sub(r"<[^>]+>", "", fragment)
    return html.unescape(body).strip()


@dataclass(frozen=True, slots=True)
class Person:
    """Somebody who worked on the show or the episode."""

    name: str
    role: str = ""
    group: str = ""
    image_url: str = ""
    link_url: str = ""

    @property
    def display(self) -> str:
        """One row, as a sentence: "Jane Smith, guest"."""
        return f"{self.name}, {self.role.lower()}" if self.role else self.name


@dataclass(frozen=True, slots=True)
class Soundbite:
    """A publisher-marked highlight: a start, a length, and usually a title.

    **The one that matters for chapters.** A soundbite is an authored mark with
    a real title, so a feed carrying them has authored structure even when it
    publishes no chapter document -- which is exactly what the chapter cascade
    wants and could not previously see.
    """

    start_ms: int
    duration_ms: int
    title: str = ""

    @property
    def end_ms(self) -> int:
        return self.start_ms + max(0, self.duration_ms)


@dataclass(frozen=True, slots=True)
class LiveItem:
    """A live stream carried in a podcast feed."""

    title: str
    status: str = ""
    start: str = ""
    end: str = ""
    stream_url: str = ""

    @property
    def is_live(self) -> bool:
        return self.status.strip().lower() == "live"


@dataclass(frozen=True, slots=True)
class Funding:
    """A support link the publisher chose. QUILL opens it and nothing else."""

    url: str
    label: str = ""

    @property
    def display(self) -> str:
        return self.label or "Support this podcast"


@dataclass(frozen=True, slots=True)
class AlternateEnclosure:
    """A second audio source for the same episode."""

    url: str
    mime_type: str = ""
    bitrate: int = 0
    title: str = ""

    @property
    def display(self) -> str:
        parts = [self.title or self.mime_type or "Alternate audio"]
        if self.bitrate:
            parts.append(f"{self.bitrate // 1000} kbps")
        return ", ".join(parts)


@dataclass(slots=True)
class NamespaceTags:
    """Everything read from the Podcasting 2.0 namespace for one item or feed."""

    people: list[Person] = field(default_factory=list)
    soundbites: list[Soundbite] = field(default_factory=list)
    live_items: list[LiveItem] = field(default_factory=list)
    podroll: list[str] = field(default_factory=list)
    funding: list[Funding] = field(default_factory=list)
    location: str = ""
    alternates: list[AlternateEnclosure] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not any((
            self.people,
            self.soundbites,
            self.live_items,
            self.podroll,
            self.funding,
            self.location,
            self.alternates,
        ))

    def to_dict(self) -> dict[str, object]:
        """The on-disk shape. Absent keys mean absent tags, not defaults.

        Written only when something was found, so a library of feeds that
        publish none of this pays nothing for the feature existing.
        """
        data: dict[str, object] = {}
        if self.people:
            data["people"] = [asdict(person) for person in self.people]
        if self.soundbites:
            data["soundbites"] = [asdict(bite) for bite in self.soundbites]
        if self.live_items:
            data["live_items"] = [asdict(item) for item in self.live_items]
        if self.podroll:
            data["podroll"] = list(self.podroll)
        if self.funding:
            data["funding"] = [asdict(link) for link in self.funding]
        if self.location:
            data["location"] = self.location
        if self.alternates:
            data["alternates"] = [asdict(alt) for alt in self.alternates]
        return data

    @classmethod
    def from_dict(cls, data: object) -> NamespaceTags:
        """Read back, tolerantly. A damaged record is an absent one."""
        if not isinstance(data, dict):
            return cls()
        return cls(
            people=_rows(data.get("people"), Person),
            soundbites=_rows(data.get("soundbites"), Soundbite),
            live_items=_rows(data.get("live_items"), LiveItem),
            podroll=[str(url) for url in data.get("podroll", []) or [] if str(url)],
            funding=_rows(data.get("funding"), Funding),
            location=str(data.get("location", "")),
            alternates=_rows(data.get("alternates"), AlternateEnclosure),
        )


def _rows[T](raw: object, kind: type[T]) -> list[T]:
    """Rebuild a list of frozen records, dropping any that will not build."""
    if not isinstance(raw, list):
        return []
    fields = {f.name for f in dataclass_fields(kind)}  # type: ignore[arg-type]
    rows: list[T] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            rows.append(kind(**{k: v for k, v in item.items() if k in fields}))
        except (TypeError, ValueError):
            continue
    return rows


def _seconds_to_ms(value: str) -> int:
    try:
        return max(0, int(float(value) * 1000))
    except (TypeError, ValueError):
        return 0


_PERSON = re.compile(r"<podcast:person\b([^>]*)>(.*?)</podcast:person>", re.IGNORECASE | re.DOTALL)
_PERSON_EMPTY = re.compile(r"<podcast:person\b([^>]*)/>", re.IGNORECASE)
_SOUNDBITE = re.compile(
    r"<podcast:soundbite\b([^>]*)>(.*?)</podcast:soundbite>", re.IGNORECASE | re.DOTALL
)
_SOUNDBITE_EMPTY = re.compile(r"<podcast:soundbite\b([^>]*)/>", re.IGNORECASE)
_LIVE_ITEM = re.compile(
    r"<podcast:liveItem\b([^>]*)>(.*?)</podcast:liveItem>", re.IGNORECASE | re.DOTALL
)
_PODROLL = re.compile(r"<podcast:podroll\b[^>]*>(.*?)</podcast:podroll>", re.IGNORECASE | re.DOTALL)
_REMOTE_ITEM = re.compile(r"<podcast:remoteItem\b([^>]*)/?>", re.IGNORECASE)
_FUNDING = re.compile(
    r"<podcast:funding\b([^>]*)>(.*?)</podcast:funding>", re.IGNORECASE | re.DOTALL
)
_LOCATION = re.compile(
    r"<podcast:location\b[^>]*>(.*?)</podcast:location>", re.IGNORECASE | re.DOTALL
)
_ALTERNATE = re.compile(
    r"<podcast:alternateEnclosure\b([^>]*)>(.*?)</podcast:alternateEnclosure>",
    re.IGNORECASE | re.DOTALL,
)
_SOURCE = re.compile(r"<podcast:source\b([^>]*)/?>", re.IGNORECASE)
_TITLE_TAG = re.compile(r"<title\b[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def parse_people(fragment: str) -> list[Person]:
    """Every ``podcast:person`` in *fragment*, in the order published."""
    people: list[Person] = []
    for attributes, body in _PERSON.findall(fragment):
        name = _text(body) or _attr(attributes, "name")
        if not name:
            continue
        people.append(
            Person(
                name=name,
                role=_attr(attributes, "role"),
                group=_attr(attributes, "group"),
                image_url=_attr(attributes, "img"),
                link_url=_attr(attributes, "href"),
            )
        )
    for attributes in _PERSON_EMPTY.findall(fragment):
        name = _attr(attributes, "name")
        if name:
            people.append(
                Person(
                    name=name,
                    role=_attr(attributes, "role"),
                    group=_attr(attributes, "group"),
                    image_url=_attr(attributes, "img"),
                    link_url=_attr(attributes, "href"),
                )
            )
    return people


def parse_soundbites(fragment: str) -> list[Soundbite]:
    """Every ``podcast:soundbite``, earliest first.

    Sorted by start because these are positions in one episode and a listener
    reading them expects the order they occur in, not the order the publisher
    happened to write them.
    """
    bites: list[Soundbite] = []
    for attributes, body in _SOUNDBITE.findall(fragment):
        start = _seconds_to_ms(_attr(attributes, "startTime"))
        duration = _seconds_to_ms(_attr(attributes, "duration"))
        if duration <= 0:
            continue
        bites.append(Soundbite(start_ms=start, duration_ms=duration, title=_text(body)))
    for attributes in _SOUNDBITE_EMPTY.findall(fragment):
        duration = _seconds_to_ms(_attr(attributes, "duration"))
        if duration <= 0:
            continue
        bites.append(
            Soundbite(start_ms=_seconds_to_ms(_attr(attributes, "startTime")), duration_ms=duration)
        )
    return sorted(bites, key=lambda bite: bite.start_ms)


def parse_live_items(fragment: str) -> list[LiveItem]:
    """Every ``podcast:liveItem`` and the stream inside it."""
    items: list[LiveItem] = []
    for attributes, body in _LIVE_ITEM.findall(fragment):
        title_match = _TITLE_TAG.search(body)
        enclosure = re.search(r'<enclosure\b[^>]*\burl\s*=\s*"([^"]+)"', body, re.IGNORECASE)
        items.append(
            LiveItem(
                title=_text(title_match.group(1)) if title_match else "Live",
                status=_attr(attributes, "status"),
                start=_attr(attributes, "start"),
                end=_attr(attributes, "end"),
                stream_url=html.unescape(enclosure.group(1)) if enclosure else "",
            )
        )
    return items


def parse_podroll(fragment: str) -> list[str]:
    """Feed URLs the show recommends, from ``podcast:podroll``.

    Returns feed addresses rather than resolved shows: resolving is a network
    act, and this module never performs one.
    """
    feeds: list[str] = []
    for body in _PODROLL.findall(fragment):
        for attributes in _REMOTE_ITEM.findall(body):
            url = _attr(attributes, "feedUrl") or _attr(attributes, "feedGuid")
            if url:
                feeds.append(url)
    return feeds


def parse_funding(fragment: str) -> list[Funding]:
    """Support links, if the publisher offered any."""
    links: list[Funding] = []
    for attributes, body in _FUNDING.findall(fragment):
        url = _attr(attributes, "url")
        if url:
            links.append(Funding(url=url, label=_text(body)))
    return links


def parse_location(fragment: str) -> str:
    """The location as text. No map, and none is wanted."""
    match = _LOCATION.search(fragment)
    return _text(match.group(1)) if match else ""


def parse_alternates(fragment: str) -> list[AlternateEnclosure]:
    """Alternate audio sources for the same episode."""
    alternates: list[AlternateEnclosure] = []
    for attributes, body in _ALTERNATE.findall(fragment):
        source = _SOURCE.search(body)
        url = _attr(source.group(1), "uri") if source else ""
        if not url:
            continue
        try:
            bitrate = int(float(_attr(attributes, "bitrate") or 0))
        except (TypeError, ValueError):
            bitrate = 0
        alternates.append(
            AlternateEnclosure(
                url=url,
                mime_type=_attr(attributes, "type"),
                bitrate=bitrate,
                title=_attr(attributes, "title"),
            )
        )
    return alternates


def parse(fragment: str) -> NamespaceTags:
    """Everything above, from one item (or channel) fragment.

    Tolerant throughout: a malformed tag contributes nothing rather than raising.
    One bad tag in one episode must never cost somebody their whole feed.
    """
    if not fragment or "podcast:" not in fragment:
        return NamespaceTags()
    try:
        return NamespaceTags(
            people=parse_people(fragment),
            soundbites=parse_soundbites(fragment),
            live_items=parse_live_items(fragment),
            podroll=parse_podroll(fragment),
            funding=parse_funding(fragment),
            location=parse_location(fragment),
            alternates=parse_alternates(fragment),
        )
    except Exception:  # noqa: BLE001 - a feed must survive its own bad markup
        return NamespaceTags()
