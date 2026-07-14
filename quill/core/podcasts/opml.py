"""OPML import/export for the podcast library.

Exports the library only (subscribed, non-local shows, nested inside
``<outline>`` elements that mirror the library's folder tree exactly) --
local/imported podcasts have no feed URL to export, and the planned Inbox
and its folder tree (`docs/planning/podcasts.md`) are pure local curation
with no OPML equivalent. Import reconstructs that same folder tree from the
nesting and merges into existing subscriptions (``PodcastLibrary.add_show``
already refuses a duplicate feed URL).

Parsing untrusted OPML files goes through :mod:`quill.core.safe_xml`
(entity-expansion attacks disabled), never the bare stdlib parser. Building
the exported XML uses plain :mod:`xml.etree.ElementTree` construction, which
is not a parsing-of-untrusted-input operation and needs no hardening.
wx-free, strict-typed.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.safe_xml import ParseError, UnsafeXMLError
from quill.core.safe_xml import fromstring as safe_fromstring


class OpmlError(CodedError):
    """An OPML file could not be parsed, or was empty of usable feeds."""

    code = "QUILL-PODCASTS-OPML"


def export_opml(library: PodcastLibrary) -> str:
    """Serialize the library (folders + subscribed non-local shows) to OPML."""
    root = ET.Element("opml", version="2.0")
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = "QUILL Podcast Subscriptions"
    body = ET.SubElement(root, "body")

    def _emit_folder(parent_xml: ET.Element, folder_id: str | None) -> None:
        child_folders = [f for f in library.folders if f.parent_folder_id == folder_id]
        for folder in child_folders:
            folder_xml = ET.SubElement(parent_xml, "outline", text=folder.name)
            _emit_folder(folder_xml, folder.id)
            _emit_shows(folder_xml, folder.id)

    def _emit_shows(parent_xml: ET.Element, folder_id: str | None) -> None:
        for show in library.shows:
            if show.is_local or not show.feed_url:
                continue
            if show.folder_id != folder_id:
                continue
            ET.SubElement(
                parent_xml,
                "outline",
                type="rss",
                text=show.title,
                title=show.title,
                xmlUrl=show.feed_url,
                htmlUrl=show.homepage,
            )

    _emit_folder(body, None)
    _emit_shows(body, None)
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


@dataclass(slots=True)
class ImportedShow:
    title: str
    feed_url: str
    homepage: str
    folder_path: list[str]


def _walk_outline(element: ET.Element, path: list[str]) -> list[ImportedShow]:
    results: list[ImportedShow] = []
    for child in element.findall("outline"):
        xml_url = child.get("xmlUrl", "").strip()
        if xml_url:
            title = child.get("title") or child.get("text") or xml_url
            results.append(
                ImportedShow(
                    title=title.strip(),
                    feed_url=xml_url,
                    homepage=child.get("htmlUrl", "").strip(),
                    folder_path=list(path),
                )
            )
            continue
        # No xmlUrl: a folder grouping outline. Recurse with an extended path.
        folder_name = (child.get("text") or child.get("title") or "").strip()
        if folder_name:
            results.extend(_walk_outline(child, [*path, folder_name]))
        else:
            results.extend(_walk_outline(child, path))
    return results


def parse_opml(text: str) -> list[ImportedShow]:
    """Parse OPML text into a flat list of shows, each carrying the folder
    path (by name) it was nested under."""
    try:
        root = safe_fromstring(text)
    except (ParseError, UnsafeXMLError) as error:
        raise OpmlError(f"That file could not be read as OPML: {error}") from error
    body = root.find("body")
    if body is None:
        return []
    return _walk_outline(body, [])


@dataclass(frozen=True, slots=True)
class OpmlValidationResult:
    """One feed's reachability check for the OPML import report (§import UX).

    ``ok`` is whether the feed answered; ``error`` carries the human-readable
    reason when it did not ("404 Not Found", "timeout", ...).
    """

    title: str
    feed_url: str
    ok: bool
    error: str = ""
    #: When the checker found the feed at a corrected address (e.g. a
    #: permanent redirect), the address the subscription was updated to.
    corrected_url: str = ""


@dataclass(slots=True)
class OpmlImportOutcome:
    """What an OPML import did: the shows added and the duplicates skipped.

    Iterable as ``(added_shows, skipped_duplicates)`` so existing callers
    that tuple-unpack the old return shape keep working unchanged.
    """

    added_shows: list[PodcastShow]
    skipped_duplicates: int

    def __iter__(self) -> Iterator[object]:
        yield self.added_shows
        yield self.skipped_duplicates


def decode_opml_bytes(data: bytes) -> str:
    """Decode a fetched OPML document defensively.

    UTF-8 with an optional BOM is the overwhelming real-world case; a
    latin-1 fallback means one stray byte can never fail a whole directory
    import (worst case: one mangled character in one show title).
    """
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def import_opml(
    library: PodcastLibrary,
    text: str,
    *,
    stream_only: bool = False,
    into_folder: str | None = None,
) -> OpmlImportOutcome:
    """Parse *text* and add every new show to *library* in place.

    Shows land in their reconstructed OPML folder path (created as needed);
    ``into_folder`` names a root folder to nest everything under instead
    (used by directory imports like ACB Media, so a bulk subscribe stays in
    its own folder). ``stream_only=True`` marks every added show
    ``playback_mode="stream"`` so a bulk import never queues dozens of
    downloads. The outcome tuple-unpacks as ``(added, skipped)`` for
    backward compatibility.
    """
    from quill.core.podcasts.subscriptions import new_id

    imported = parse_opml(text)
    added: list[PodcastShow] = []
    skipped = 0
    for entry in imported:
        path = list(entry.folder_path)
        if into_folder:
            path = [into_folder, *path]
        folder_id = library.find_or_create_folder_path(path) if path else None
        show = PodcastShow(
            id=new_id(),
            title=entry.title,
            feed_url=entry.feed_url,
            homepage=entry.homepage,
            folder_id=folder_id,
        )
        if stream_only:
            from quill.core.podcasts.models import PodcastSettings

            show.settings = PodcastSettings(playback_mode="stream")
        if library.add_show(show):
            added.append(show)
        else:
            skipped += 1
    return OpmlImportOutcome(added_shows=added, skipped_duplicates=skipped)
