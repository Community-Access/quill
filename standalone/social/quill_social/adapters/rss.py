"""A read-only RSS / Atom feed adapter (plan xxx.md Part 3, PRD 34 extensibility).

This is the reference *read-only* :class:`NetworkAdapter`: it fetches and parses
one feed and maps its entries onto the shared :class:`SocialItem` model, newest
first, exactly like a timeline. It never publishes -- ``publish`` and the
interaction hooks raise a ``permission`` :class:`AdapterError`, and the RSS
capability profile hides those actions in the UI.

Design choices that fit product B:
- **No new hard dependency.** The parser is a focused, safe standard-library
  implementation covering RSS 2.0 and Atom (the overwhelming majority of feeds),
  so an RSS account works with zero extra install -- just like the mock network.
  Robustness beyond these formats can later ride an optional ``feedparser`` path.
- **Two-mode construction.** The adapter takes the feed URL plus an optional
  ``fetch`` callable (dependency injection); tests pass fixture bytes and never
  touch the network. The default fetch is HTTPS-only, TLS-verified, timed out,
  and size-capped.
- **Untrusted input.** Feed XML is hostile: the parser rejects DOCTYPE/ENTITY
  declarations (billion-laughs / XXE defense) before parsing, and entry bodies
  are stripped to plain text here (rich, sanitized HTML rendering lands with the
  reader UI increment).
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

from quill_social.adapters.base import (
    AdapterError,
    NetworkAdapter,
    PublishRequest,
    PublishResult,
)
from quill_social.capabilities import Capabilities, default_for
from quill_social.model import Media, SocialItem, now_ms

# A fetch takes a URL and returns the raw feed bytes.
Fetch = Callable[[str], bytes]

_USER_AGENT = "QUILL-Social-RSS/0.1 (+https://github.com/Community-Access/quill-social)"
_TIMEOUT_S = 15.0
_MAX_BYTES = 20_000_000
_NOT_WIRED = "RSS is read-only; publishing and interactions are not supported."

# JSON Feed (https://jsonfeed.org) version markers we accept.
_JSONFEED_PREFIX = "https://jsonfeed.org/version/"

# XML namespaces we read.
_ATOM = "http://www.w3.org/2005/Atom"
_CONTENT = "http://purl.org/rss/1.0/modules/content/"
_DC = "http://purl.org/dc/elements/1.1/"


# -- parsed feed shapes -------------------------------------------------------


@dataclass
class ParsedEntry:
    """One normalized feed entry, before it becomes a :class:`SocialItem`."""

    guid: str = ""
    title: str = ""
    link: str = ""
    summary: str = ""  # plain text, tags stripped
    content_html: str = ""  # raw entry HTML (kept for the reader UI increment)
    author: str = ""
    published_ms: int = 0
    enclosures: list[Media] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)  # tags/labels on the entry


@dataclass
class ParsedFeed:
    """A feed's channel metadata plus its entries, newest first."""

    title: str = ""
    home_url: str = ""
    entries: list[ParsedEntry] = field(default_factory=list)
    # WebSub / PubSubHubbub discovery (rel="hub" / rel="self"). Real-time push
    # needs a public callback endpoint the desktop app has no place to host, so
    # these are recorded for future use; reading always falls back to polling.
    hub_url: str = ""
    self_url: str = ""


# -- plain-text extraction ----------------------------------------------------


class _TextStripper(HTMLParser):
    """Collapse feed HTML into readable plain text (no external dependency)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("br", "p", "div", "li", "tr"):
            self._parts.append("\n")

    def text(self) -> str:
        joined = "".join(self._parts)
        # Collapse runs of blank lines / trailing whitespace.
        lines = [ln.strip() for ln in joined.splitlines()]
        out: list[str] = []
        blank = False
        for ln in lines:
            if ln:
                out.append(ln)
                blank = False
            elif not blank:
                out.append("")
                blank = True
        return "\n".join(out).strip()


def strip_html(value: str) -> str:
    """Return the visible text of an HTML fragment. Never raises."""
    if not value:
        return ""
    if "<" not in value and "&" not in value:
        return value.strip()
    stripper = _TextStripper()
    try:
        stripper.feed(value)
        stripper.close()
    except Exception:  # noqa: BLE001 -- malformed HTML must not break a feed
        return value.strip()
    return stripper.text()


# -- date parsing -------------------------------------------------------------


def _to_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def parse_date_ms(value: str) -> int:
    """Parse an RSS (RFC 822) or Atom (RFC 3339) date to epoch ms, else ``0``."""
    text = (value or "").strip()
    if not text:
        return 0
    # RFC 822 / 2822 (RSS pubDate), e.g. "Tue, 10 Jun 2003 04:00:00 GMT".
    try:
        dt = parsedate_to_datetime(text)
        if dt is not None:
            return _to_ms(dt)
    except (TypeError, ValueError, IndexError):
        pass
    # RFC 3339 / ISO 8601 (Atom updated/published), e.g. "2003-12-13T18:30:02Z".
    iso = text.replace("Z", "+00:00")
    try:
        return _to_ms(datetime.fromisoformat(iso))
    except ValueError:
        return 0


# -- XML helpers --------------------------------------------------------------


def _local(tag: str) -> str:
    """The local name of a possibly-namespaced tag (``{ns}name`` -> ``name``)."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _find_text(el: ET.Element, *local_names: str) -> str:
    """First non-empty child text matching any of ``local_names`` (ns-agnostic)."""
    for child in el:
        if _local(child.tag) in local_names:
            text = (child.text or "").strip()
            if text:
                return text
    return ""


def _reject_dtd(raw: bytes) -> None:
    """Refuse DOCTYPE/ENTITY declarations (billion-laughs / XXE defense)."""
    head = raw[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in head:
        raise AdapterError("feed declares a DTD/entity; refused", kind="validation")


def _enclosure(url: str, mime: str) -> Media:
    kind = "unknown"
    m = (mime or "").lower()
    if m.startswith("image/"):
        kind = "image"
    elif m.startswith("audio/"):
        kind = "audio"
    elif m.startswith("video/"):
        kind = "video"
    return Media(kind=kind, uri=url, mime=mime)


def _add_category(entry: ParsedEntry, child: ET.Element) -> None:
    """Collect a ``<category>`` value: Atom ``term`` attr or RSS element text."""
    value = (child.attrib.get("term") or child.text or "").strip()
    if value and value not in entry.categories:
        entry.categories.append(value)


def _hub_links(el: ET.Element) -> tuple[str, str]:
    """Find WebSub ``rel="hub"`` / ``rel="self"`` link hrefs on a channel/feed."""
    hub = self_url = ""
    for child in el:
        if _local(child.tag) != "link":
            continue
        rel = child.attrib.get("rel", "")
        href = child.attrib.get("href", "")
        if not href:
            continue
        if rel == "hub" and not hub:
            hub = href
        elif rel == "self" and not self_url:
            self_url = href
    return hub, self_url


# -- RSS 2.0 ------------------------------------------------------------------


def _parse_rss(channel: ET.Element) -> ParsedFeed:
    feed = ParsedFeed(
        title=_find_text(channel, "title"),
        home_url=_find_text(channel, "link"),
    )
    feed.hub_url, feed.self_url = _hub_links(channel)
    for item in channel:
        if _local(item.tag) != "item":
            continue
        entry = ParsedEntry(
            title=_find_text(item, "title"),
            link=_find_text(item, "link"),
            author=_find_text(item, "creator", "author"),
        )
        entry.guid = _find_text(item, "guid") or entry.link
        content = ""
        summary = ""
        for child in item:
            name = _local(child.tag)
            if child.tag == f"{{{_CONTENT}}}encoded" or name == "encoded":
                content = child.text or ""
            elif name in ("description", "summary"):
                summary = child.text or ""
            elif name == "pubDate" or name == "date":
                entry.published_ms = parse_date_ms(child.text or "")
            elif name == "enclosure":
                url = child.attrib.get("url", "")
                if url:
                    entry.enclosures.append(_enclosure(url, child.attrib.get("type", "")))
            elif name == "category":
                _add_category(entry, child)
        entry.content_html = content or summary
        entry.summary = strip_html(summary or content)
        if entry.title or entry.summary or entry.link:
            feed.entries.append(entry)
    return feed


# -- Atom ---------------------------------------------------------------------


def _atom_link(entry: ET.Element) -> str:
    """The alternate (or first) link href of an Atom entry/feed."""
    fallback = ""
    for child in entry:
        if _local(child.tag) != "link":
            continue
        href = child.attrib.get("href", "")
        if not href:
            continue
        rel = child.attrib.get("rel", "alternate")
        if rel == "alternate":
            return href
        fallback = fallback or href
    return fallback


def _atom_author(entry: ET.Element) -> str:
    for child in entry:
        if _local(child.tag) == "author":
            return _find_text(child, "name") or _find_text(child, "email")
    return ""


def _parse_atom(feed_el: ET.Element) -> ParsedFeed:
    feed = ParsedFeed(title=_find_text(feed_el, "title"), home_url=_atom_link(feed_el))
    feed.hub_url, feed.self_url = _hub_links(feed_el)
    for entry_el in feed_el:
        if _local(entry_el.tag) != "entry":
            continue
        entry = ParsedEntry(
            title=_find_text(entry_el, "title"),
            link=_atom_link(entry_el),
            author=_atom_author(entry_el),
        )
        entry.guid = _find_text(entry_el, "id") or entry.link
        entry.published_ms = parse_date_ms(_find_text(entry_el, "published", "updated"))
        content = ""
        summary = ""
        for child in entry_el:
            name = _local(child.tag)
            if name == "content":
                content = "".join(child.itertext()) if len(child) else (child.text or "")
            elif name == "summary":
                summary = child.text or ""
            elif name == "link":
                href = child.attrib.get("href", "")
                rel = child.attrib.get("rel", "")
                if rel == "enclosure" and href:
                    entry.enclosures.append(_enclosure(href, child.attrib.get("type", "")))
            elif name == "category":
                _add_category(entry, child)
        entry.content_html = content or summary
        entry.summary = strip_html(summary or content)
        if entry.title or entry.summary or entry.link:
            feed.entries.append(entry)
    return feed


# -- JSON Feed (https://jsonfeed.org) -----------------------------------------


def _jsonfeed_author(obj: dict) -> str:
    """A JSON Feed author name from ``authors`` (1.1) or ``author`` (1.0)."""
    authors = obj.get("authors")
    if isinstance(authors, list):
        for a in authors:
            if isinstance(a, dict):
                name = (a.get("name") or "").strip()
                if name:
                    return name
    author = obj.get("author")
    if isinstance(author, dict):
        return (author.get("name") or "").strip()
    return ""


def _jsonfeed_attachments(item: dict) -> list[Media]:
    out: list[Media] = []
    atts = item.get("attachments")
    if not isinstance(atts, list):
        return out
    for att in atts:
        if not isinstance(att, dict):
            continue
        url = (att.get("url") or "").strip()
        if url:
            out.append(_enclosure(url, att.get("mime_type", "")))
    return out


def parse_json_feed(raw: bytes) -> ParsedFeed:
    """Parse a JSON Feed 1.0/1.1 document into a :class:`ParsedFeed`.

    JSON Feed is a well-specified, closed format (no external entities), so it is
    safe to decode without the DTD guard the XML path needs.
    """
    try:
        doc = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AdapterError(f"feed is not valid JSON: {exc}", kind="validation") from exc
    if not isinstance(doc, dict):
        raise AdapterError("JSON feed is not an object", kind="validation")
    version = str(doc.get("version", ""))
    if not version.startswith(_JSONFEED_PREFIX):
        raise AdapterError("not a JSON Feed document", kind="validation")

    feed = ParsedFeed(
        title=str(doc.get("title", "") or ""),
        home_url=str(doc.get("home_page_url", "") or ""),
    )
    raw_items = doc.get("items")
    if not isinstance(raw_items, list):
        return feed
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        content_html = str(raw_item.get("content_html", "") or "")
        content_text = str(raw_item.get("content_text", "") or "")
        summary = str(raw_item.get("summary", "") or "")
        link = str(raw_item.get("url", "") or "") or str(raw_item.get("external_url", "") or "")
        # ``id`` is required by the spec but tolerate its absence.
        guid = str(raw_item.get("id", "") or "") or link
        tags = raw_item.get("tags")
        categories = (
            [str(t).strip() for t in tags if str(t).strip()] if isinstance(tags, list) else []
        )
        entry = ParsedEntry(
            guid=guid,
            title=str(raw_item.get("title", "") or ""),
            link=link,
            author=_jsonfeed_author(raw_item),
            content_html=content_html,
            enclosures=_jsonfeed_attachments(raw_item),
            categories=categories,
        )
        entry.published_ms = parse_date_ms(
            str(raw_item.get("date_published", "") or raw_item.get("date_modified", "") or "")
        )
        # Body precedence mirrors the spec: prefer HTML, then plain text.
        if content_html:
            entry.summary = strip_html(content_html)
        else:
            entry.summary = content_text or strip_html(summary)
            if not content_text and summary:
                entry.content_html = summary
        if entry.title or entry.summary or entry.link:
            feed.entries.append(entry)
    return feed


def _looks_like_json(raw: bytes) -> bool:
    """True if ``raw`` starts (past BOM/whitespace) with a JSON object brace."""
    head = raw.lstrip(b"\xef\xbb\xbf \t\r\n")
    return head[:1] == b"{"


def parse_feed(raw: bytes) -> ParsedFeed:
    """Parse RSS 2.0, Atom, or JSON Feed bytes into a :class:`ParsedFeed`.

    Never fetches. The format is sniffed from the leading bytes (``{`` -> JSON
    Feed, otherwise XML). Raises :class:`AdapterError` (``validation``) on unsafe
    or unparseable input.
    """
    if not raw:
        raise AdapterError("empty feed body", kind="validation")
    if _looks_like_json(raw):
        return parse_json_feed(raw)
    _reject_dtd(raw)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise AdapterError(f"feed is not well-formed XML: {exc}", kind="validation") from exc

    tag = _local(root.tag)
    if tag == "feed":  # Atom
        return _parse_atom(root)
    if tag == "rss":
        channel = next((c for c in root if _local(c.tag) == "channel"), None)
        if channel is None:
            raise AdapterError("RSS feed has no channel", kind="validation")
        return _parse_rss(channel)
    if tag == "channel":  # RSS 1.0 / RDF-ish: a bare channel
        return _parse_rss(root)
    raise AdapterError(f"unrecognized feed root <{tag}>", kind="validation")


# -- entry -> SocialItem ------------------------------------------------------


def entry_to_item(entry: ParsedEntry, *, account_id: str, feed_url: str = "") -> SocialItem:
    """Map a parsed feed entry onto the shared :class:`SocialItem` model.

    The title leads the item text; the body is the entry's **full content**,
    HTML-sanitized into safe, readable text (links inlined, images as
    ``[Image: alt]``, script/style dropped) so the article pane shows the whole
    piece securely rather than a truncated summary (plan xxx.md 3.7).
    """
    from quill_social.services.html_sanitize import sanitize_to_text

    base = entry.link or feed_url
    body = (
        sanitize_to_text(entry.content_html, base_url=base) if entry.content_html else entry.summary
    )
    if entry.title and body:
        text = f"{entry.title}\n\n{body}"
    else:
        text = entry.title or body
    return SocialItem(
        network="rss",
        account_id=account_id,
        remote_id=entry.guid or entry.link or entry.title,
        uri=entry.link or feed_url,
        author_handle=entry.author,
        author_display=entry.author,
        author_id=entry.author,
        text=text,
        created_at=entry.published_ms or now_ms(),
        media=list(entry.enclosures),
        tags=list(entry.categories),
    )


# -- fetch --------------------------------------------------------------------


@dataclass
class FetchResult:
    """The outcome of a (possibly conditional) feed fetch.

    ``status`` is the HTTP status; ``304`` means *not modified* and ``body`` is
    empty. ``etag``/``last_modified`` are the validators the server returned (or,
    on a ``304``, the ones the caller sent), to persist for the next poll.
    """

    body: bytes = b""
    status: int = 200
    etag: str = ""
    last_modified: str = ""

    @property
    def not_modified(self) -> bool:
        return self.status == 304


# A conditional fetch takes a URL plus the caller's stored validators and returns
# a full :class:`FetchResult` (honoring 304 and transparent gzip/deflate).
ConditionalFetch = Callable[..., FetchResult]


def _decode_body(raw: bytes, encoding: str) -> bytes:
    """Transparently decode a gzip/deflate response body, bounded to the cap.

    A hostile server could ship a small payload that inflates to gigabytes, so
    decompression is capped at ``_MAX_BYTES`` and simply truncated past it (the
    XML/JSON parser then rejects the fragment) -- never an unbounded expansion.
    """
    enc = (encoding or "").strip().lower()
    if enc in ("", "identity"):
        return raw[:_MAX_BYTES]
    if enc == "gzip":
        decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
    elif enc == "deflate":
        # Prefer zlib-wrapped deflate; fall back to raw deflate if that fails.
        try:
            return zlib.decompressobj(zlib.MAX_WBITS).decompress(raw, _MAX_BYTES)
        except zlib.error:
            decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
    else:
        # Unknown encoding: hand back the bytes and let the parser decide.
        return raw[:_MAX_BYTES]
    try:
        return decompressor.decompress(raw, _MAX_BYTES)
    except zlib.error as exc:
        raise AdapterError(f"could not decode feed body: {exc}", kind="validation") from exc


def default_conditional_fetch(url: str, *, etag: str = "", last_modified: str = "") -> FetchResult:
    """Fetch a feed over HTTPS with conditional GET and gzip/deflate support.

    Sends ``If-None-Match`` / ``If-Modified-Since`` from the stored validators
    and ``Accept-Encoding: gzip, deflate``. A ``304 Not Modified`` returns an
    empty-body :class:`FetchResult` carrying the caller's validators forward.
    """
    if not url.lower().startswith("https://"):
        raise AdapterError("feed URL must be https://", kind="validation")
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S, context=ctx) as resp:
            raw = resp.read(_MAX_BYTES + 1)
            body = _decode_body(raw, resp.headers.get("Content-Encoding", ""))
            return FetchResult(
                body=body,
                status=getattr(resp, "status", 200) or 200,
                etag=resp.headers.get("ETag", "") or etag,
                last_modified=resp.headers.get("Last-Modified", "") or last_modified,
            )
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            hdrs = exc.headers or {}
            return FetchResult(
                status=304,
                etag=hdrs.get("ETag", "") or etag,
                last_modified=hdrs.get("Last-Modified", "") or last_modified,
            )
        raise _rss_error(exc) from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise AdapterError(f"could not fetch feed: {exc}", kind="transient") from exc


def default_fetch(url: str) -> bytes:
    """Fetch feed bytes over HTTPS (non-conditional): the simple ``Fetch`` path."""
    return default_conditional_fetch(url).body


def _rss_error(exc: Exception) -> AdapterError:
    """Normalize a fetch failure into an :class:`AdapterError`."""
    if isinstance(exc, AdapterError):
        return exc
    status = getattr(exc, "code", None)
    msg = str(exc) or "rss error"
    if status in (401, 403):
        return AdapterError(msg, kind="permission")
    if status in (400, 404, 410, 422):
        return AdapterError(msg, kind="validation")
    if status == 429 or (isinstance(status, int) and status >= 500):
        return AdapterError(msg, kind="transient")
    return AdapterError(msg, kind="transient")


# -- adapter ------------------------------------------------------------------


@dataclass
class FeedPoll:
    """The result of a conditional feed poll (plan xxx.md 1.1 conditional GET).

    ``not_modified`` is ``True`` when the server answered ``304`` -- ``items`` is
    then empty and the caller should keep its cached entries. ``etag`` and
    ``last_modified`` are the validators to persist for the next poll.
    """

    items: list[SocialItem] = field(default_factory=list)
    etag: str = ""
    last_modified: str = ""
    not_modified: bool = False
    hub_url: str = ""  # WebSub hub advertised by the feed (rel="hub"), if any


class RssAdapter(NetworkAdapter):
    """A read-only feed subscription surfaced as a home timeline."""

    name = "rss"

    def __init__(
        self,
        *,
        feed_url: str,
        account_id: str = "",
        fetch: Fetch | None = None,
        conditional_fetch: ConditionalFetch | None = None,
    ) -> None:
        self.feed_url = feed_url
        self._account_id = account_id
        self._fetch: Fetch = fetch or default_fetch
        # A conditional fetch is optional: without one (e.g. a test injecting a
        # plain ``fetch``), ``poll`` degrades to an unconditional GET.
        self._conditional_fetch = conditional_fetch

    @classmethod
    def available(cls) -> bool:
        # Pure standard library -- always usable.
        return True

    def capabilities(self) -> Capabilities:
        return default_for("rss")

    def home_timeline(self, *, limit: int = 40, since_id: str = "") -> list[SocialItem]:
        if not self.feed_url:
            raise AdapterError("no feed URL configured", kind="validation")
        raw = self._fetch(self.feed_url)
        feed = parse_feed(raw)
        items: list[SocialItem] = []
        for entry in feed.entries:
            if since_id and (entry.guid == since_id or entry.link == since_id):
                break
            items.append(entry_to_item(entry, account_id=self._account_id, feed_url=self.feed_url))
        items.sort(key=lambda it: it.created_at, reverse=True)
        return items[:limit]

    def poll(self, *, etag: str = "", last_modified: str = "", limit: int = 60) -> FeedPoll:
        """Conditionally re-fetch the feed, honoring ETag / Last-Modified.

        Uses conditional GET when a conditional fetch is available: a ``304`` is
        returned as ``FeedPoll(not_modified=True)`` with no body parsed. Without
        a conditional fetch it falls back to a plain GET (never reports 304).
        """
        if not self.feed_url:
            raise AdapterError("no feed URL configured", kind="validation")
        if self._conditional_fetch is None:
            return FeedPoll(items=self.home_timeline(limit=limit))
        result = self._conditional_fetch(self.feed_url, etag=etag, last_modified=last_modified)
        if result.not_modified:
            return FeedPoll(
                etag=result.etag,
                last_modified=result.last_modified,
                not_modified=True,
            )
        feed = parse_feed(result.body)
        items = [
            entry_to_item(e, account_id=self._account_id, feed_url=self.feed_url)
            for e in feed.entries
        ]
        items.sort(key=lambda it: it.created_at, reverse=True)
        return FeedPoll(
            items=items[:limit],
            etag=result.etag,
            last_modified=result.last_modified,
            hub_url=feed.hub_url,
        )

    def notifications(self, *, limit: int = 40) -> list[SocialItem]:
        # Feeds have no notifications.
        return []

    def thread(self, item: SocialItem) -> list[SocialItem]:
        # A feed entry stands alone.
        return [item]

    def publish(self, request: PublishRequest) -> PublishResult:
        raise AdapterError(_NOT_WIRED, kind="permission")

    def set_favourite(self, remote_id: str, on: bool = True) -> None:
        raise AdapterError(_NOT_WIRED, kind="permission")

    def set_reblog(self, remote_id: str, on: bool = True) -> None:
        raise AdapterError(_NOT_WIRED, kind="permission")

    def delete(self, remote_id: str) -> None:
        raise AdapterError(_NOT_WIRED, kind="permission")
