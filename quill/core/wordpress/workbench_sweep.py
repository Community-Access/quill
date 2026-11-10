"""The third sweep: what running a real site also involves, core REST first (PRD 15.11).

Only what the core REST API (or data the Workbench already reads) reaches,
plus one plugin row behind namespace detection:

- **A redirect when a slug changes** (:func:`redirect_offered`,
  :func:`redirect_body`): offered only where the Redirection plugin's
  ``redirection/v1`` namespace is in the site's index; to verify against a live
  install (the body follows the plugin's documented ``/redirect`` route).
- **Privacy requests** (:func:`privacy_rows`): core keeps export and erase
  requests as a post type with no REST route, so unless a site's index has
  one, the rows point to wp-admin's two Privacy screens.
- **Content audit** (:func:`content_audit`): pages nobody links to, pages
  not changed in a year, duplicate titles, very long and very short pages,
  and headings that skip a level, from the site scan of 15.12.
- **Media housekeeping** (:func:`media_housekeeping`): files used nowhere,
  very large files, video with no captions track where it is used, and audio
  with no transcript or description.

Every other 15.11 area stays listed as planned in the coverage gate
(redirects, backups, security, caching and the rest each need a plugin's API
checked against a live install first). Wx-free and network-free.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from quill.core.wordpress.site import friendly_date, human_size
from quill.core.wordpress.workbench_across import SiteScan
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "LARGE_FILE",
    "REDIRECTION_NAMESPACE",
    "content_audit",
    "media_housekeeping",
    "privacy_rows",
    "redirect_body",
    "redirect_offered",
]

REDIRECTION_NAMESPACE = "redirection/v1"
LARGE_FILE = 2 * 1024 * 1024
_HEADING = re.compile(r"<h([1-6])\b", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


def redirect_offered(namespaces: Sequence[str]) -> bool:
    return REDIRECTION_NAMESPACE in {n.strip("/") for n in namespaces}


def redirect_body(old_link: str, new_link: str) -> dict[str, Any]:
    """The Redirection plugin's body for a 301 from the old address to the new one."""
    from urllib.parse import urlparse

    path = urlparse(old_link).path or "/"
    return {
        "url": path,
        "action_type": "url",
        "action_code": 301,
        "action_data": {"url": new_link},
        "match_type": "url",
        "group_id": 1,
        "regex": False,
        "title": "Made by QUILL when the address changed",
    }


def _problem(site: str, key: str, problem: str, where: str, detail: str, link: str = "") -> WbRow:
    return WbRow(
        "problem",
        site,
        key,
        {"problem": problem, "site": site, "status": where, "test": problem, "says": where},
        detail,
        link=link,
    )


def privacy_rows(site: str, site_url: str, routes: Sequence[str]) -> list[WbRow]:
    """Where privacy requests are: a route the site offers, or wp-admin's screens."""
    found = [r for r in routes if "user_request" in r or "privacy-request" in r]
    if found:
        return [
            _problem(site, r, "Privacy requests route", r, f"{site} offers {r} for requests.")
            for r in found
        ]
    base = site_url.rstrip("/")
    return [
        _problem(
            site,
            "export",
            "Export Personal Data",
            "in wp-admin",
            "WordPress keeps export requests away from its REST API, so they are in "
            "wp-admin: Tools > Export Personal Data. Shift+Enter opens it.",
            f"{base}/wp-admin/export-personal-data.php",
        ),
        _problem(
            site,
            "erase",
            "Erase Personal Data",
            "in wp-admin",
            "Erase requests are in wp-admin too: Tools > Erase Personal Data. Shift+Enter "
            "opens it.",
            f"{base}/wp-admin/erase-personal-data.php",
        ),
    ]


def _words(html: str) -> int:
    return len(_TAG.sub(" ", html or "").split())


def _text(raw: Any) -> str:
    if isinstance(raw, dict):
        return str(raw.get("raw") or raw.get("rendered") or "")
    return str(raw or "")


def content_audit(scan: SiteScan, *, now: datetime | None = None) -> list[WbRow]:
    """The content audit's problems, one row each."""
    today = now or datetime.now(UTC)
    rows: list[WbRow] = []
    items = [i for i in scan.items if i.get("status") == "publish"]
    every_text = "\n".join(_text(i.get("content")) for i in scan.items)
    titles = Counter(_text(i.get("title")).strip().casefold() for i in items)
    for item in items:
        title = _text(item.get("title")) or f"#{item.get('id')}"
        link = str(item.get("link", "") or "")
        content = _text(item.get("content"))
        key = str(item.get("id", ""))
        path = link.rstrip("/").rsplit("/", 1)[-1] if link else ""
        if item.get("type") == "page" and path and f"/{path}" not in every_text:
            rows.append(
                _problem(
                    scan.site,
                    f"{key}:orphan",
                    "Nothing links to it",
                    title,
                    f"{title}: no other post or page links to it.",
                    link,
                )
            )
        modified = str(item.get("modified_gmt", "") or "")
        if modified:
            try:
                when = datetime.fromisoformat(modified).replace(tzinfo=UTC)
            except ValueError:
                when = today
            if today - when > timedelta(days=365):
                rows.append(
                    _problem(
                        scan.site,
                        f"{key}:stale",
                        "Not changed in a year",
                        title,
                        f"{title}: last changed {friendly_date(modified)}.",
                        link,
                    )
                )
        if titles[title.strip().casefold()] > 1:
            rows.append(
                _problem(
                    scan.site,
                    f"{key}:twin",
                    "Shares its title",
                    title,
                    f"{title}: another published item has the same title.",
                    link,
                )
            )
        words = _words(content)
        if words > 5000:
            rows.append(
                _problem(
                    scan.site, f"{key}:long", "Very long", title, f"{title}: {words} words.", link
                )
            )
        elif words < 50:
            rows.append(
                _problem(
                    scan.site, f"{key}:short", "Very short", title, f"{title}: {words} words.", link
                )
            )
        levels = [int(n) for n in _HEADING.findall(content)]
        for before, after in zip(levels, levels[1:], strict=False):
            if after > before + 1:
                rows.append(
                    _problem(
                        scan.site,
                        f"{key}:headings",
                        "A heading skips a level",
                        title,
                        f"{title}: a heading {before} is followed by a heading {after}.",
                        link,
                    )
                )
                break
    return rows


def media_housekeeping(scan: SiteScan) -> list[WbRow]:
    """Files used nowhere, very large files, video with no captions, audio with no transcript."""
    rows: list[WbRow] = []
    texts = [_text(i.get("content")) for i in scan.items]
    featured = {int(i.get("featured_media", 0) or 0) for i in scan.items}
    for media in scan.media:
        url = str(media.get("source_url", "") or "")
        name = url.rsplit("/", 1)[-1] or f"media {media.get('id')}"
        stem = url.rsplit(".", 1)[0] if url else ""
        ident = int(media.get("id", 0) or 0)
        using = [t for t in texts if stem and stem in t]
        mime = str(media.get("mime_type", "") or "")
        details = media.get("media_details") if isinstance(media.get("media_details"), dict) else {}
        size = int((details or {}).get("filesize", 0) or 0)
        if not using and ident not in featured and not media.get("post"):
            rows.append(
                _problem(
                    scan.site,
                    f"{ident}:unused",
                    "Used nowhere",
                    name,
                    f"{name} is not in any post or page, and is no one's featured image.",
                    url,
                )
            )
        if size > LARGE_FILE:
            rows.append(
                _problem(
                    scan.site,
                    f"{ident}:large",
                    "Very large",
                    name,
                    f"{name} is {human_size(size)}; a smaller copy loads faster.",
                    url,
                )
            )
        if mime.startswith("video/") and using and not any("<track" in t for t in using):
            rows.append(
                _problem(
                    scan.site,
                    f"{ident}:captions",
                    "Video without captions",
                    name,
                    f"{name} is shown with no captions track. Tools > WordPress > More "
                    "Media > Captions for Video makes one.",
                    url,
                )
            )
        if mime.startswith("audio/") and not _text(media.get("description")).strip():
            rows.append(
                _problem(
                    scan.site,
                    f"{ident}:transcript",
                    "Audio without a transcript",
                    name,
                    f"{name} has no transcript or description. Tools > WordPress > More "
                    "Media > Transcript for Audio makes one.",
                    url,
                )
            )
    return rows
