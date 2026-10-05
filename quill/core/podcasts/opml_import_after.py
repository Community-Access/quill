"""After the import check: act on what it found.

Split from :mod:`quill.core.podcasts.opml_import` under GATE-11 when the
2026-10-04 Downcast import test added the second half of this: the sweep there
answers "which feeds are dead, which have moved for good", and this module is
what Cast does with the answer -- point a moved feed at its new address where
the podcast's own setting allows (check.md bug 5), and write the listener's
OPML file back without the dead ones.

wx-free, strict-typed. No network.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable

from quill.core.podcasts.opml import OpmlValidationResult
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.safe_xml import ParseError, UnsafeXMLError
from quill.core.safe_xml import fromstring as safe_fromstring

__all__ = ["apply_permanent_moves", "prune_opml"]


def apply_permanent_moves(
    library: PodcastLibrary, results: list[OpmlValidationResult]
) -> list[OpmlValidationResult]:
    """Point newly imported shows at their feeds' permanent new addresses.

    Only where the podcast's own "Follow permanent feed redirects" setting
    allows it -- the same rule a refresh follows -- and never for a show with
    a saved sign-in. Returns the results with ``applied`` set on each move
    that was made, so the report can say which were updated and which were
    left alone, rather than claiming corrections nobody made (check.md bug 5).
    """
    from quill.core.podcasts.show_policy import follows_redirects

    updated: list[OpmlValidationResult] = []
    for result in results:
        if not result.corrected_url:
            updated.append(result)
            continue
        show = library.find_show_by_feed_url(result.feed_url)
        applied = bool(
            show is not None and not show.feed_username and follows_redirects(library, show)
        )
        if applied and show is not None:
            show.feed_url = result.corrected_url
        updated.append(
            OpmlValidationResult(
                result.title,
                result.feed_url,
                result.ok,
                result.error,
                result.corrected_url,
                applied=applied,
            )
        )
    return updated


def prune_opml(text: str, dead_urls: Iterable[str]) -> str:
    """The same OPML with every unreachable feed's outline removed.

    Structure, attributes, folder nesting, and anything the original file
    carried that QUILL does not model are all preserved -- this edits the
    document rather than re-exporting the library, so the pruned file is
    still recognisably the listener's own file and can go straight back to
    wherever it came from. A folder outline left with no feeds in it is
    dropped too, since an empty folder is not a subscription list.
    """
    # Imported here: opml_import re-exports this module, so a top-level import
    # either way round would be circular.
    from quill.core.podcasts.opml_import import normalize_feed_url

    dead = {normalize_feed_url(url) for url in dead_urls if url}
    if not dead:
        return text
    try:
        root = safe_fromstring(text)
    except (ParseError, UnsafeXMLError):
        return text

    def prune_element(element: ET.Element) -> None:
        for child in list(element.findall("outline")):
            xml_url = (child.get("xmlUrl") or "").strip()
            if xml_url:
                if normalize_feed_url(xml_url) in dead:
                    element.remove(child)
                continue
            prune_element(child)
            if not child.findall("outline"):
                element.remove(child)

    body = root.find("body")
    if body is not None:
        prune_element(body)
    return ET.tostring(root, encoding="unicode", xml_declaration=False)
