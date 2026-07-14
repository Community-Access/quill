"""Podcast RSS 2.0 + iTunes / Podcasting 2.0 feed generation (local, offline).

Ported from ChapterForge (``s:\\code99\\forum``, MIT) onto QUILL's book model.
Generates a self-contained ``.rss`` document for a built audiobook/podcast
master so self-hosting podcasters can manage the whole pipeline from QUILL.
Pure XML generation — writing the file is the only IO, and no network is
involved (uploading the feed is the SFTP destination's job).
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from quill.core.speech.ffmpeg import AudioMetadata

_ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
_PODCAST_NS = "https://podcastindex.org/namespace/1.0"

ET.register_namespace("itunes", _ITUNES_NS)
ET.register_namespace("podcast", _PODCAST_NS)


@dataclass(slots=True)
class FeedItem:
    """One episode: a built master and where it will be hosted."""

    path: Path
    media_url: str
    title: str
    description: str = ""
    duration_s: int = 0
    has_chapters: bool = False
    #: RFC 2822 publication date; empty = the feed's generation time.
    pub_date: str = ""


def rfc2822(when: datetime) -> str:
    """The RSS pubDate form of *when* (always rendered as UTC)."""
    return when.astimezone(UTC).strftime("%a, %d %b %Y %H:%M:%S +0000")


def _sub(parent: ET.Element, tag: str, text: str = "") -> ET.Element:
    element = ET.SubElement(parent, tag)
    if text:
        element.text = text
    return element


def _itunes(tag: str) -> str:
    return f"{{{_ITUNES_NS}}}{tag}"


def _podcast(tag: str) -> str:
    return f"{{{_PODCAST_NS}}}{tag}"


def _mime_for(path: Path) -> str:
    return "audio/x-m4b" if path.suffix.lower() in {".m4b", ".m4a"} else "audio/mpeg"


def generate_rss(
    items: list[FeedItem],
    tags: AudioMetadata,
    *,
    feed_url: str = "",
    description: str = "",
    cover_url: str = "",
) -> str:
    """An RSS 2.0 + iTunes + Podcasting 2.0 XML document for *items*.

    Each item's enclosure carries its public ``media_url``; when the item has
    chapters, a ``podcast:chapters`` link points at the ``….chapters.json``
    sidecar QUILL already writes next to every book.
    """
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")

    show_title = tags.album or tags.title or "Untitled"
    _sub(channel, "title", show_title)
    _sub(channel, "description", description or tags.comment or show_title)
    if feed_url:
        _sub(channel, "link", feed_url)
    if tags.genre:
        # iTunes carries the category in a "text" attribute, not element text.
        ET.SubElement(channel, _itunes("category"), {"text": tags.genre})
    if tags.artist:
        _sub(channel, _itunes("author"), tags.artist)
    if tags.album_artist and tags.album_artist != tags.artist:
        _sub(channel, _itunes("author"), tags.album_artist)
    _sub(channel, _itunes("explicit"), "false")
    if cover_url:
        image = ET.SubElement(channel, "image")
        _sub(image, "url", cover_url)
        _sub(image, "title", show_title)
        _sub(image, "link", feed_url or "")
        ET.SubElement(channel, _itunes("image"), {"href": cover_url})

    pub_date = rfc2822(datetime.now(UTC))
    for index, item in enumerate(items, start=1):
        element = ET.SubElement(channel, "item")
        _sub(element, "title", item.title or f"Episode {index}")
        _sub(element, "description", item.description or item.title)
        _sub(element, "pubDate", item.pub_date or pub_date)
        guid = _sub(element, "guid", item.media_url)
        guid.set("isPermaLink", "false")
        if item.duration_s > 0:
            _sub(element, _itunes("duration"), str(item.duration_s))
        _sub(element, _itunes("episode"), str(index))
        size = str(item.path.stat().st_size) if item.path.is_file() else "0"
        ET.SubElement(
            element,
            "enclosure",
            {"url": item.media_url, "type": _mime_for(item.path), "length": size},
        )
        if item.has_chapters and "." in item.media_url.rsplit("/", 1)[-1]:
            chapters_url = item.media_url.rsplit(".", 1)[0] + ".chapters.json"
            ET.SubElement(
                element,
                _podcast("chapters"),
                {"url": chapters_url, "type": "application/json+chapters"},
            )

    ET.indent(rss, space="  ")
    buf = io.StringIO()
    buf.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    ET.ElementTree(rss).write(buf, encoding="unicode", xml_declaration=False)
    return buf.getvalue()


def write_rss(
    items: list[FeedItem],
    tags: AudioMetadata,
    out_path: Path,
    *,
    feed_url: str = "",
    description: str = "",
    cover_url: str = "",
) -> Path:
    """Write the feed to *out_path* (``.rss`` enforced); returns the path."""
    if out_path.suffix.lower() != ".rss":
        out_path = out_path.with_suffix(".rss")
    xml = generate_rss(items, tags, feed_url=feed_url, description=description, cover_url=cover_url)
    out_path.write_text(xml, encoding="utf-8")
    return out_path
