"""Search, sitemaps, overdue schedules, the certificate and editing locks (PRD 15.11).

Each row of Sites > site > Search and Upkeep ends with where its answer
came from and what that source cannot say, because every one of these is
something the core REST API only half shows:

- **Search engine visibility** (:func:`visibility_row`): core does not put
  ``blog_public`` in ``wp/v2/settings``. When a site (or a plugin) adds it,
  it is read; otherwise it is judged from ``wp-sitemap.xml``, which core
  turns off when the site asks not to be indexed. Settings > Reading says
  for certain, and the row opens it.
- **The sitemap** (:func:`sitemap_row`): ``/wp-sitemap.xml`` read from the
  site itself, its sub-sitemaps counted; an SEO plugin's own sitemap
  replaces it, which the row says.
- **Overdue schedules** (:func:`overdue_rows`): posts and pages still
  ``future`` after their time, which means WP-Cron did not run them. The
  REST API lists no other WP-Cron task; Site Health and WP Crontrol do.
- **The certificate** (:func:`certificate_row`): its expiry date, from the
  connection QUILL already makes to the site (:func:`read_certificate`), and
  a warning inside 30 days. Where the date cannot be read, the row says the
  connection was verified and no more.
- **Editing locks** (:func:`lock_rows`): WordPress holds a post's lock in
  ``_edit_lock`` meta through wp-admin's heartbeat, which REST does not
  show; where a site exposes it, a lock under 150 seconds old is named, and
  otherwise items changed in the last 15 minutes are listed as maybe open.

Wx-free; the two reads that leave the REST API reach only the connected
site's own host, through its client's opener.
"""

from __future__ import annotations

import re
import ssl
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from quill.core.wordpress.site import friendly_date
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "CERT_WARN_DAYS",
    "LOCK_SECONDS",
    "certificate_row",
    "lock_rows",
    "overdue_rows",
    "peer_certificate",
    "read_certificate",
    "sitemap_row",
    "visibility_row",
]

CERT_WARN_DAYS = 30
LOCK_SECONDS = 150
"""WordPress's own lock window (``wp_check_post_lock_window``)."""
_RECENT = timedelta(minutes=15)
_SITEMAP = re.compile(r"<sitemap>\s*<loc>([^<]+)</loc>", re.IGNORECASE)
_URL = re.compile(r"<url>", re.IGNORECASE)


def _row(
    site: str, key: str, what: str, state: str, detail: str, source: str, link: str = ""
) -> WbRow:
    return WbRow(
        "upkeep",
        site,
        key,
        {"what": what, "state": state, "source": source},
        f"{detail} Where this comes from: {source}",
        link=link,
        raw={"source": source},
    )


def visibility_row(
    site: str, site_url: str, settings: Mapping[str, Any] | None, sitemap_found: bool | None
) -> WbRow:
    """Whether the site asks search engines to stay away, and how QUILL knows."""
    reading = site_url.rstrip("/") + "/wp-admin/options-reading.php"
    if settings is not None and "blog_public" in settings:
        public = str(settings.get("blog_public")) not in ("0", "False", "false")
        state = "visible" if public else "asks not to be indexed"
        return _row(
            site,
            "visibility",
            "Search engine visibility",
            state,
            f"{site} lets search engines index it."
            if public
            else f"{site} asks search engines not to index it.",
            "the blog_public setting, which this site adds to its REST settings.",
            reading,
        )
    if sitemap_found is None:
        state, said = "unknown", f"QUILL could not tell whether {site} asks not to be indexed."
    elif sitemap_found:
        state = "probably visible"
        said = f"{site} serves WordPress's sitemap, so it probably lets search engines index it."
    else:
        state = "maybe hidden"
        said = (
            f"{site} serves no WordPress sitemap. That happens when it asks search engines not "
            "to index it, or when an SEO plugin replaces the sitemap."
        )
    return _row(
        site,
        "visibility",
        "Search engine visibility",
        state,
        said,
        "judged from wp-sitemap.xml, because WordPress's REST API does not include the "
        "Search engine visibility setting. Enter opens Settings > Reading, which says for certain.",
        reading,
    )


def sitemap_row(site: str, site_url: str, body: bytes | None, error: str = "") -> WbRow:
    """``/wp-sitemap.xml``: whether it is there and how many sitemaps it lists."""
    address = site_url.rstrip("/") + "/wp-sitemap.xml"
    source = "wp-sitemap.xml, read from the site itself."
    if body is None:
        return _row(
            site,
            "sitemap",
            "Sitemap",
            "not found",
            f"{site} did not serve {address}"
            + (f": {error}." if error else ".")
            + " An SEO plugin (Yoast's sitemap_index.xml, for one) may serve its own instead.",
            source,
            address,
        )
    text = body.decode("utf-8", "replace")
    subs = _SITEMAP.findall(text)
    urls = len(_URL.findall(text))
    names = [s.rstrip("/").rsplit("/", 1)[-1] for s in subs]
    count = f"{len(subs)} sitemaps" if subs else f"{urls} addresses"
    listed = f": {', '.join(names[:12])}" if names else ""
    return _row(
        site,
        "sitemap",
        "Sitemap",
        "found",
        f"{address} lists {count}{listed}.",
        source,
        address,
    )


def _when(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text).replace(tzinfo=UTC)
    except ValueError:
        return None


def overdue_rows(
    site: str, items: Sequence[Mapping[str, Any]], *, now: datetime | None = None
) -> list[WbRow]:
    """Scheduled posts and pages whose time has passed: WP-Cron did not publish them."""
    today = now or datetime.now(UTC)
    source = (
        "posts and pages still Scheduled after their time. WordPress's REST API lists no "
        "other WP-Cron task; Site Health and the WP Crontrol plugin do."
    )
    rows = []
    for item in items:
        if item.get("status") != "future":
            continue
        when = _when(str(item.get("date_gmt", "") or ""))
        if when is None or when > today - timedelta(minutes=1):
            continue
        title = item.get("title")
        name = (
            str(title.get("raw") or title.get("rendered") or "")
            if isinstance(title, Mapping)
            else str(title or "")
        )
        name = name or f"#{item.get('id')}"
        rows.append(
            _row(
                site,
                f"overdue:{item.get('id')}",
                f"Missed schedule: {name}",
                "overdue",
                f"{name} was due on {friendly_date(str(item.get('date_gmt')))} and is still "
                "waiting. WordPress publishes on a visit through WP-Cron; Approve and Schedule "
                "on its row in Posts or Pages publishes it now.",
                source,
                str(item.get("link", "") or ""),
            )
        )
    if not rows:
        rows.append(
            _row(
                site,
                "overdue",
                "Overdue schedules",
                "none",
                "Nothing scheduled is overdue.",
                source,
            )
        )
    return rows


def peer_certificate(response: Any) -> dict[str, Any] | None:
    """The verified certificate behind an open HTTPS response, where Python exposes it."""
    sock: Any = None
    try:
        sock = response.fp.raw._sock
    except AttributeError:
        return None
    try:
        cert = sock.getpeercert()
    except (AttributeError, ValueError, OSError):
        return None
    return dict(cert) if isinstance(cert, Mapping) and cert else None


def read_certificate(api: Any) -> dict[str, Any] | None:
    """The site's certificate, from one request to its own REST index (None when unknown)."""
    from urllib.request import Request

    from quill.core.wordpress import api as wpapi

    address = getattr(getattr(api, "address", None), "site_url", "")
    opener = getattr(api, "_opener", None)
    if urlparse(address).scheme != "https" or opener is None:
        return None
    url = wpapi.route_url(api.address, "")
    request = Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with opener(request, timeout=api.timeout, context=wpapi._context(url)) as response:
            return peer_certificate(response)
    except (OSError, ValueError):
        return None


def certificate_row(
    site: str, site_url: str, cert: Mapping[str, Any] | None, *, now: datetime | None = None
) -> WbRow:
    """The certificate's expiry, in days, with a warning inside :data:`CERT_WARN_DAYS`."""
    today = now or datetime.now(UTC)
    source = "the certificate the site showed QUILL's own connection to it."
    if urlparse(site_url).scheme != "https":
        return _row(
            site,
            "certificate",
            "Certificate",
            "no HTTPS",
            f"{site} is connected over plain HTTP, so there is no certificate to read.",
            "the site's address in your list of sites.",
        )
    after = str((cert or {}).get("notAfter", "") or "")
    if not after:
        return _row(
            site,
            "certificate",
            "Certificate",
            "valid now",
            f"QUILL's connection to {site} checked its certificate, which is valid today. "
            "Its expiry date was not handed over, so no warning can be given ahead of time.",
            "QUILL's verified connection; the expiry date was not available from it.",
        )
    try:
        ends = datetime.fromtimestamp(ssl.cert_time_to_seconds(after), UTC)
    except ValueError:
        return _row(
            site,
            "certificate",
            "Certificate",
            "unknown",
            f"The expiry {after} was not readable.",
            source,
        )
    days = (ends - today).days
    state = "expired" if days < 0 else ("expires soon" if days <= CERT_WARN_DAYS else "valid")
    said = (
        f"{site}'s certificate expired {-days} days ago."
        if days < 0
        else f"{site}'s certificate is good until {ends:%d %B %Y}, {days} days from now."
    )
    if 0 <= days <= CERT_WARN_DAYS:
        said += " Ask your host to renew it before then."
    return _row(site, "certificate", "Certificate", state, said, source)


def _lock_of(item: Mapping[str, Any]) -> tuple[int, int] | None:
    meta = item.get("meta")
    raw = meta.get("_edit_lock") if isinstance(meta, Mapping) else None
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    match = re.match(r"^(\d+):(\d+)$", str(raw or ""))
    return (int(match.group(1)), int(match.group(2))) if match else None


def lock_rows(
    site: str,
    items: Sequence[Mapping[str, Any]],
    *,
    me: int = 0,
    people: Mapping[int, str] | None = None,
    now: datetime | None = None,
) -> list[WbRow]:
    """Who is editing what, as far as the site lets REST see it."""
    today = now or datetime.now(UTC)
    names = people or {}
    rows: list[WbRow] = []
    exposed = any(isinstance(i.get("meta"), Mapping) and "_edit_lock" in i["meta"] for i in items)
    for item in items:
        title = item.get("title")
        name = (
            str(title.get("raw") or title.get("rendered") or "")
            if isinstance(title, Mapping)
            else str(title or "")
        )
        name = name or f"#{item.get('id')}"
        lock = _lock_of(item)
        if lock is not None:
            stamp, who = lock
            age = today.timestamp() - stamp
            if age <= LOCK_SECONDS and who != me:
                person = names.get(who, f"user {who}")
                rows.append(
                    _row(
                        site,
                        f"lock:{item.get('id')}",
                        f"Being edited: {name}",
                        "locked",
                        f"{person} has {name} open in WordPress's editor now. Changing it "
                        "here as well can lose one of the two changes; Properties checks "
                        "for that before saving.",
                        "the _edit_lock field, which this site exposes to REST.",
                        str(item.get("link", "") or ""),
                    )
                )
            continue
        changed = _when(str(item.get("modified_gmt", "") or ""))
        if not exposed and changed is not None and today - changed <= _RECENT:
            rows.append(
                _row(
                    site,
                    f"recent:{item.get('id')}",
                    f"Changed in the last 15 minutes: {name}",
                    "maybe open",
                    f"{name} changed at {friendly_date(str(item.get('modified_gmt')))}; someone "
                    "may still have it open.",
                    "the time it last changed. WordPress keeps its editing lock out of REST, so "
                    "who has a post open is not known; Properties refuses to save over a newer "
                    "change.",
                    str(item.get("link", "") or ""),
                )
            )
    if not rows:
        rows.append(
            _row(
                site,
                "locks",
                "Editing locks",
                "none seen",
                "No one is seen editing a post or page now.",
                "the _edit_lock field where the site exposes it"
                if exposed
                else "the time each item last changed; WordPress keeps its editing lock out of "
                "REST, so this cannot see someone who has a post open without saving.",
            )
        )
    return rows
