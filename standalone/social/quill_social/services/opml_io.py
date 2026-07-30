"""Nested OPML import/export for feed subscriptions (plan xxx.md 3.8).

Round-trips a folders-of-folders subscription tree in the OPML outline format
every reader speaks (Feedly, Inoreader, NetNewsWire all export it). Pure standard
library:

- import rejects DOCTYPE/ENTITY declarations before parsing (billion-laughs / XXE
  defense) and treats any ``<outline>`` without an ``xmlUrl`` as a folder,
  carrying a ``folder_path`` down the tree so arbitrary nesting survives;
- export emits a recursive ``<outline>`` tree from flat ``(feed, folder_path)``
  entries, escaping every attribute.

The module is decoupled from the store: it speaks in plain dataclasses/dicts so
it stays trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET


class OpmlError(ValueError):
    """Malformed or unsafe OPML."""


def _split_categories(value: str) -> list[str]:
    """Parse an OPML ``category`` attribute (comma-separated) into tags."""
    return [c.strip() for c in (value or "").split(",") if c.strip()]


@dataclass
class ImportedFeed:
    """One feed discovered in an OPML file, with its folder path."""

    title: str = ""
    feed_url: str = ""
    site_url: str = ""
    folder_path: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass
class OpmlFeedEntry:
    """A feed to export, with the folder path it should nest under."""

    title: str = ""
    feed_url: str = ""
    site_url: str = ""
    folder_path: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


def _reject_dtd(text: str) -> None:
    head = text[:4096].lower()
    if "<!doctype" in head or "<!entity" in head:
        raise OpmlError("OPML declares a DTD/entity; refused")


def _walk(node: ET.Element, path: list[str], out: list[ImportedFeed]) -> None:
    for outline in node:
        if outline.tag != "outline":
            continue
        xml_url = outline.attrib.get("xmlUrl", "").strip()
        text = (
            outline.attrib.get("text")
            or outline.attrib.get("title")
            or ""
        ).strip()
        if xml_url:
            out.append(
                ImportedFeed(
                    title=text or xml_url,
                    feed_url=xml_url,
                    site_url=outline.attrib.get("htmlUrl", "").strip(),
                    folder_path=list(path),
                    categories=_split_categories(outline.attrib.get("category", "")),
                )
            )
            # A feed outline may still nest children in some exports.
            _walk(outline, path, out)
        else:
            # A folder: descend with this name appended to the path.
            _walk(outline, [*path, text] if text else path, out)


def parse_opml(text: str) -> list[ImportedFeed]:
    """Parse OPML text into a flat list of feeds with their folder paths."""
    if not text or not text.strip():
        return []
    _reject_dtd(text)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise OpmlError(f"OPML is not well-formed XML: {exc}") from exc
    body = root.find("body")
    if body is None:
        return []
    out: list[ImportedFeed] = []
    _walk(body, [], out)
    return out


def export_opml(entries: list[OpmlFeedEntry], *, title: str = "QUILL Social feeds") -> str:
    """Render feed entries (with folder paths) as a nested OPML document."""
    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = title
    body = ET.SubElement(opml, "body")

    # Build the folder tree once, so sibling feeds share the same folder element.
    folder_els: dict[tuple[str, ...], ET.Element] = {(): body}

    def folder_element(path: list[str]) -> ET.Element:
        key: tuple[str, ...] = ()
        parent = body
        for name in path:
            key = (*key, name)
            existing = folder_els.get(key)
            if existing is None:
                existing = ET.SubElement(parent, "outline", text=name, title=name)
                folder_els[key] = existing
            parent = existing
        return parent

    for entry in entries:
        parent = folder_element(entry.folder_path)
        attrs = {
            "type": "rss",
            "text": entry.title or entry.feed_url,
            "title": entry.title or entry.feed_url,
            "xmlUrl": entry.feed_url,
        }
        if entry.site_url:
            attrs["htmlUrl"] = entry.site_url
        if entry.categories:
            attrs["category"] = ",".join(entry.categories)
        ET.SubElement(parent, "outline", **attrs)

    ET.indent(opml, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        opml, encoding="unicode"
    )
