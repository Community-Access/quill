"""XSPF playlists, including the ones real devices write (#1691).

XSPF 1.0 (https://xspf.org/spec) is a small, namespaced XML format: a
``<playlist>`` holding a ``<trackList>`` of ``<track>`` elements, each with a
``<location>`` (the stream), a ``<title>``, and optional ``<creator>``,
``<annotation>``, ``<info>`` (a page about the track) and ``<image>``.

The files listeners actually have in hand are less tidy than the spec, and the
one that prompted this module is the reason it exists. HumanWare's Victor
Stream and Victor Trek export their radio lists as XSPF, and a list that has
been passed around and edited by hand can carry a tag whose name was lost --
``< >Station name</ >`` -- which no XML parser will read. Before this module a
single such line turned a 28-station list into "No radio stations were found",
because one malformed element sank the whole document. So:

- The document is parsed safely first (``quill.core.safe_xml``: no DTDs, no
  entity expansion). Hostile XML is still refused loudly, by the caller.
- When it is merely malformed, a per-track regex sweep takes over, so one bad
  track costs at most that track's name, never the other 27 stations.
- The Victor shape is read as written: ``<info>`` there holds keywords rather
  than a URL, and ``<creator>`` holds the service's web address. A URL in
  ``<info>`` becomes the station's home page, as the spec intends; otherwise a
  web-address-shaped ``<creator>`` does. A non-URL ``<location>`` (Victor
  writes ``ootunes`` for a station it can only reach through its own
  directory) is not a stream and is skipped.

Pure: text in, stations out. No files, no network, no wx.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from quill.core.radio.models import RadioStation
from quill.core.radio.playlist_formats import _local, _name_from_url, _parse_xml, _playable

__all__ = ["XspfEntry", "parse_xspf_entries", "stations_from_entries"]

#: One ``<track>...</track>`` block, for the malformed-document fallback.
_TRACK_RE = re.compile(r"<(?:\w+:)?track\b[^>]*>(.*?)</(?:\w+:)?track\s*>", re.S | re.I)

#: An element whose name has been lost: ``< >text</ >``. Seen in the wild in a
#: hand-edited Victor Stream export, always where ``<title>`` belonged.
_NAMELESS_RE = re.compile(r"<\s+>(.*?)</\s*>", re.S)

#: Something a person would recognise as a web address with no scheme:
#: ``www.wkar.org/radioreadingservice/`` or ``audiojournal.org``.
_BARE_WEB_ADDRESS_RE = re.compile(r"^(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/\S*)?$", re.I)

_FIELDS = ("location", "title", "creator", "annotation", "info", "image")


@dataclass(frozen=True, slots=True)
class XspfEntry:
    """One ``<track>``, with every field the spec gives it that a station can use."""

    location: str
    title: str = ""
    creator: str = ""
    annotation: str = ""
    info: str = ""
    image: str = ""


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _child_text(element: object, name: str) -> str:
    """The first direct child named *name* (namespace ignored), stripped."""
    for child in element:  # type: ignore[attr-defined]
        if _local(child.tag) == name and child.text:
            return _clean(child.text)
    return ""


def _entries_from_tree(text: str) -> list[XspfEntry] | None:
    """Entries from a well-formed document, or None when it will not parse.

    Raises ``PlaylistFormatError`` (via ``_parse_xml``) for hostile XML.
    """
    root = _parse_xml(text)
    if root is None:
        return None
    entries: list[XspfEntry] = []
    for element in root.iter():
        if _local(element.tag) != "track":
            continue
        values = {name: _child_text(element, name) for name in _FIELDS}
        entries.append(XspfEntry(**values))
    return entries


def _regex_field(block: str, name: str) -> str:
    match = re.search(rf"<(?:\w+:)?{name}\b[^>]*>(.*?)</(?:\w+:)?{name}\s*>", block, re.S | re.I)
    return _clean(html.unescape(match.group(1))) if match else ""


def _entries_from_regex(text: str) -> list[XspfEntry]:
    """Entries from a document the XML parser refused, one track at a time.

    Only nested ``<extension>`` content is removed first, so a vendor element
    that happens to be called ``title`` cannot stand in for the track's own.
    """
    entries: list[XspfEntry] = []
    for block in _TRACK_RE.findall(text):
        block = re.sub(r"<(?:\w+:)?extension\b.*?</(?:\w+:)?extension\s*>", "", block, flags=re.S)
        values = {name: _regex_field(block, name) for name in _FIELDS}
        if not values["title"]:
            nameless = _NAMELESS_RE.search(block)
            if nameless:
                values["title"] = _clean(html.unescape(nameless.group(1)))
        entries.append(XspfEntry(**values))
    return entries


def parse_xspf_entries(text: str) -> list[XspfEntry]:
    """Every ``<track>`` in *text*, well-formed or not (pure).

    Raises ``playlist_formats.PlaylistFormatError`` for hostile XML (a DTD or
    entity payload) -- the regex fallback is for broken documents, never a way
    around that refusal.
    """
    if not (text or "").strip():
        return []
    entries = _entries_from_tree(text)
    if entries is None:
        entries = _entries_from_regex(text)
    return entries


def _home_page(entry: XspfEntry) -> str:
    if _playable(entry.info):
        return entry.info
    creator = entry.creator.strip()
    if _playable(creator):
        return creator
    if creator and " " not in creator and _BARE_WEB_ADDRESS_RE.match(creator):
        return f"https://{creator}"
    return ""


def stations_from_entries(entries: list[XspfEntry]) -> list[RadioStation]:
    """Stations from *entries*: playable locations only, first of each URL wins.

    The name is the title, else the annotation, else the creator, else the
    stream's host -- the same last resort every other importer uses.
    """
    stations: list[RadioStation] = []
    seen: set[str] = set()
    for entry in entries:
        url = entry.location.strip()
        if not _playable(url) or url in seen:
            continue
        seen.add(url)
        name = entry.title or entry.annotation or entry.creator or _name_from_url(url)
        stations.append(
            RadioStation(
                name=name,
                stream_url=url,
                homepage=_home_page(entry),
                favicon=entry.image if _playable(entry.image) else "",
            )
        )
    return stations
