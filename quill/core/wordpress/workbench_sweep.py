"""The third sweep: what running a real site also involves, core REST first (PRD 15.11).

Only what the core REST API (or data the Workbench already reads) reaches,
plus the Redirection plugin behind namespace detection
(:mod:`quill.core.wordpress.workbench_redirects`):

- **A redirect when a slug changes** (:func:`redirect_offered`,
  :func:`redirect_body`): offered only where the Redirection plugin's
  ``redirection/v1`` namespace is in the site's index; to verify against a live
  install (the body follows the plugin's documented ``/redirect`` route).
- **Privacy requests** (:func:`privacy_rows`): core keeps export and erase
  requests as a post type with no REST route, so unless a site's index has
  one, the rows point to wp-admin's two Privacy screens -- by their exact
  addresses, which moved in WordPress 5.3 -- and opening one is never called
  doing the request.
- **Content audit** (:func:`content_audit`): pages nobody links to, pages
  not changed in a year, duplicate titles, the same text twice, very long and
  very short pages, hard reading (Document Statistics' Flesch-Kincaid
  measure, :mod:`quill.core.wordpress.readability`) and headings that skip a
  level, from the site scan of 15.12. Page-level accessibility (axe) stays in
  Check This Page (:mod:`quill.core.wordpress.page_audit`), which needs a
  browser.
- **Media housekeeping** (:func:`media_housekeeping`): files used nowhere,
  files that look uploaded twice, very large files, video with no captions
  track where it is used, and audio with no transcript or description.

Every finding row carries where it is used (``raw["places"]``), so Show Where
It Is Used, and the preview before Move to Trash, can name it before anything
is sent. Wx-free and network-free.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any

from quill.core.wordpress.readability import describe, reading_level
from quill.core.wordpress.site import friendly_date, human_size
from quill.core.wordpress.workbench_across import SiteScan
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "HARD_GRADE",
    "LARGE_FILE",
    "REDIRECTION_NAMESPACE",
    "content_audit",
    "media_housekeeping",
    "privacy_rows",
    "privacy_screens",
    "redirect_body",
    "redirect_offered",
    "trash_preview",
]

REDIRECTION_NAMESPACE = "redirection/v1"
LARGE_FILE = 2 * 1024 * 1024
HARD_GRADE = 12.0
"""Above this Flesch-Kincaid grade, a page is listed as hard to read."""

_HEADING = re.compile(r"<h([1-6])\b", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")
_COPY_SUFFIX = re.compile(r"(-\d+|-scaled|-e\d{10,})+$")


def redirect_offered(namespaces: Sequence[str]) -> bool:
    return REDIRECTION_NAMESPACE in {n.strip("/") for n in namespaces}


def redirect_body(old_link: str, new_link: str, group_id: int) -> dict[str, Any]:
    """The Redirection plugin's body for a 301 from the old address to the new one.

    *group_id* is a group the site has (``workbench_redirects.default_group``):
    the plugin refuses a redirect without one ("Invalid group"), and group 1 is
    not every site's first group.
    """
    from urllib.parse import urlparse

    path = urlparse(old_link).path or "/"
    return {
        "url": path,
        "action_type": "url",
        "action_code": 301,
        "action_data": {"url": new_link},
        "match_type": "url",
        "group_id": int(group_id),
        "regex": False,
        "title": "Made by QUILL when the address changed",
    }


def _problem(
    site: str,
    key: str,
    problem: str,
    where: str,
    detail: str,
    link: str = "",
    *,
    kind: str = "problem",
    raw: Mapping[str, Any] | None = None,
) -> WbRow:
    return WbRow(
        kind,
        site,
        key,
        {"problem": problem, "site": site, "status": where, "test": problem, "says": where},
        detail,
        link=link,
        raw=dict(raw or {}),
    )


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", text)[:2]) or (99,)


def privacy_screens(site_url: str, wp_version: str = "") -> tuple[str, str]:
    """wp-admin's Export and Erase Personal Data screens, by their exact addresses.

    WordPress 5.3 moved them from ``tools.php?page=export_personal_data`` and
    ``tools.php?page=remove_personal_data`` to their own files; ``tools.php``
    still redirects the old pair. A site whose version is unknown gets the
    current addresses.
    """
    base = site_url.rstrip("/") + "/wp-admin/"
    if wp_version and _version(wp_version) < (5, 3):
        return (
            base + "tools.php?page=export_personal_data",
            base + "tools.php?page=remove_personal_data",
        )
    return base + "export-personal-data.php", base + "erase-personal-data.php"


def privacy_rows(
    site: str, site_url: str, routes: Sequence[str], wp_version: str = ""
) -> list[WbRow]:
    """Where privacy requests are: a route the site offers, or wp-admin's screens."""
    found = [r for r in routes if "user_request" in r or "privacy-request" in r]
    if found:
        return [
            _problem(site, r, "Privacy requests route", r, f"{site} offers {r} for requests.")
            for r in found
        ]
    export, erase = privacy_screens(site_url, wp_version)
    limit = (
        " WordPress's REST API has no route for these requests, so QUILL cannot list, "
        "confirm or complete them, and cannot tell afterwards whether they were done."
    )
    return [
        _problem(
            site,
            "export",
            "Export Personal Data",
            "in wp-admin",
            "Export requests are kept in wp-admin: Tools > Export Personal Data. Enter opens "
            f"it in your browser, where you add, confirm and send each export.{limit}",
            export,
            kind="privacy",
            raw={"screen": "Tools > Export Personal Data"},
        ),
        _problem(
            site,
            "erase",
            "Erase Personal Data",
            "in wp-admin",
            "Erase requests are kept in wp-admin too: Tools > Erase Personal Data. Enter opens "
            f"it in your browser, where you add, confirm and erase each request.{limit}",
            erase,
            kind="privacy",
            raw={"screen": "Tools > Erase Personal Data"},
        ),
    ]


def _finding(
    rows: list[WbRow],
    site: str,
    key: str,
    where: str,
    link: str,
    raw: Mapping[str, Any],
    suffix: str,
    problem: str,
    detail: str,
) -> None:
    rows.append(
        _problem(site, f"{key}:{suffix}", problem, where, detail, link, kind="finding", raw=raw)
    )


def _words(html: str) -> int:
    return len(_TAG.sub(" ", html or "").split())


def _text(raw: Any) -> str:
    if isinstance(raw, dict):
        return str(raw.get("raw") or raw.get("rendered") or "")
    return str(raw or "")


def _title(item: Mapping[str, Any]) -> str:
    return _text(item.get("title")) or f"#{item.get('id')}"


def _route(item: Mapping[str, Any]) -> str:
    kind = "pages" if item.get("type") == "page" else "posts"
    return f"wp/v2/{kind}/{item.get('id')}"


def _fingerprint(html: str) -> str:
    words = " ".join(_TAG.sub(" ", html or "").casefold().split())
    return hashlib.sha256(words.encode("utf-8")).hexdigest() if words else ""


def content_audit(scan: SiteScan, *, now: datetime | None = None) -> list[WbRow]:
    """The content audit's problems, one row each."""
    today = now or datetime.now(UTC)
    rows: list[WbRow] = []
    items = [i for i in scan.items if i.get("status") == "publish"]
    every_text = "\n".join(_text(i.get("content")) for i in scan.items)
    titles = Counter(_title(i).strip().casefold() for i in items)
    prints = Counter(
        p
        for i in items
        if _words(_text(i.get("content"))) >= 50 and (p := _fingerprint(_text(i.get("content"))))
    )
    for item in items:
        title = _title(item)
        link = str(item.get("link", "") or "")
        content = _text(item.get("content"))
        key = str(item.get("id", ""))
        path = link.rstrip("/").rsplit("/", 1)[-1] if link else ""
        linking = [
            _title(other)
            for other in scan.items
            if other is not item and path and f"/{path}" in _text(other.get("content"))
        ]
        base = {
            "route": _route(item),
            "item_id": item.get("id"),
            "title": title,
            "places": linking,
            "places_are": "links to it",
        }

        add = partial(_finding, rows, scan.site, key, title, link, base)

        if item.get("type") == "page" and path and f"/{path}" not in every_text:
            add("orphan", "Nothing links to it", f"{title}: no other post or page links to it.")
        modified = str(item.get("modified_gmt", "") or "")
        if modified:
            try:
                when = datetime.fromisoformat(modified).replace(tzinfo=UTC)
            except ValueError:
                when = today
            if today - when > timedelta(days=365):
                add(
                    "stale",
                    "Not changed in a year",
                    f"{title}: last changed {friendly_date(modified)}.",
                )
        if titles[title.strip().casefold()] > 1:
            add("twin", "Shares its title", f"{title}: another published item has the same title.")
        words = _words(content)
        fingerprint = _fingerprint(content) if words >= 50 else ""
        if fingerprint and prints[fingerprint] > 1:
            add(
                "copy",
                "Same text as another",
                f"{title}: another published item has the same text.",
            )
        if words > 5000:
            add("long", "Very long", f"{title}: {words} words.")
        elif words < 50:
            add("short", "Very short", f"{title}: {words} words.")
        if words >= 100:
            level = reading_level(content, is_html=True)
            if level.grade > HARD_GRADE:
                add("reading", "Hard to read", f"{title}: {describe(level)}.")
        levels = [int(n) for n in _HEADING.findall(content)]
        for before, after in zip(levels, levels[1:], strict=False):
            if after > before + 1:
                add(
                    "headings",
                    "A heading skips a level",
                    f"{title}: a heading {before} is followed by a heading {after}.",
                )
                break
    return rows


def _stem(url: str) -> str:
    name = url.rsplit("/", 1)[-1]
    stem, _dot, ext = name.rpartition(".")
    return f"{_COPY_SUFFIX.sub('', stem or name).casefold()}.{ext.casefold()}"


def media_housekeeping(scan: SiteScan) -> list[WbRow]:
    """Unused files, copies, very large files, video with no captions, audio with no transcript."""
    rows: list[WbRow] = []
    texts = [(_title(i), _text(i.get("content"))) for i in scan.items]
    featured: dict[int, list[str]] = defaultdict(list)
    for item in scan.items:
        featured[int(item.get("featured_media", 0) or 0)].append(_title(item))
    seen: dict[tuple[str, str], str] = {}
    sizes: dict[tuple[int, str], str] = {}
    for media in scan.media:
        url = str(media.get("source_url", "") or "")
        name = url.rsplit("/", 1)[-1] or f"media {media.get('id')}"
        stem = url.rsplit(".", 1)[0] if url else ""
        ident = int(media.get("id", 0) or 0)
        using = [t for _title_of, t in texts if stem and stem in t]
        places = [title for title, t in texts if stem and stem in t]
        places += [f"{title} (featured image)" for title in featured.get(ident, [])]
        mime = str(media.get("mime_type", "") or "")
        details = media.get("media_details") if isinstance(media.get("media_details"), dict) else {}
        size = int((details or {}).get("filesize", 0) or 0)
        raw = {
            "route": f"wp/v2/media/{ident}",
            "item_id": ident,
            "title": name,
            "places": places,
            "places_are": "uses it",
            "media": True,
        }

        add = partial(_finding, rows, scan.site, str(ident), name, url, raw)

        if not places and not media.get("post"):
            add(
                "unused",
                "Used nowhere",
                f"{name} is not in any post or page, and is no one's featured image.",
            )
        twin = seen.get((_stem(url), mime)) if url else None
        same_size = sizes.get((size, mime)) if size else None
        if twin or same_size:
            other = twin or same_size
            add(
                "copy",
                "Looks uploaded twice",
                f"{name} has the same name or the same size and type as {other}; it may be a "
                "second copy of one file.",
            )
        if url:
            seen.setdefault((_stem(url), mime), name)
        if size:
            sizes.setdefault((size, mime), name)
        if size > LARGE_FILE:
            add(
                "large", "Very large", f"{name} is {human_size(size)}; a smaller copy loads faster."
            )
        if mime.startswith("video/") and using and not any("<track" in t for t in using):
            add(
                "captions",
                "Video without captions",
                f"{name} is shown with no captions track. Tools > WordPress > More "
                "Media > Captions for Video makes one.",
            )
        if mime.startswith("audio/") and not _text(media.get("description")).strip():
            add(
                "transcript",
                "Audio without a transcript",
                f"{name} has no transcript or description. Tools > WordPress > More "
                "Media > Transcript for Audio makes one.",
            )
    return rows


def trash_preview(row: WbRow) -> tuple[str, list[str]]:
    """What Move to Trash will do to a finding's item, with where it is used, before anything."""
    title = str(row.raw.get("title", "") or row.title)
    places = [str(p) for p in row.raw.get("places") or []]
    are = str(row.raw.get("places_are", "uses it"))
    if row.raw.get("media"):
        summary = (
            f"Move {title} on {row.site} to the Trash. WordPress keeps media in a Trash only "
            "where the site turns that on; where it does not, nothing is deleted and QUILL "
            "says so."
        )
    else:
        summary = f"Move {title} on {row.site} to the Trash, where Restore brings it back."
    if places:
        lines = [f"{p} {are}" for p in places]
    else:
        lines = [f"Nothing in the posts and pages read {are}."]
    return summary, lines
