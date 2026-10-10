"""Podcast RSS/Atom feed fetching and parsing.

The network fetch and the parsing are deliberately two separate steps: QUILL
fetches the raw feed bytes itself (:func:`_fetch_feed_bytes`, the one
reviewed egress site -- see ``quill/tools/network_egress_audit.py``), then
hands those bytes to ``feedparser`` for parsing only. ``feedparser`` can
fetch a URL itself, but doing that would move the actual HTTP request outside
QUILL's own audited code -- fetching first keeps QUILL in control of
HTTPS-only enforcement, the timeout, and HTTP Basic auth for private feeds,
and it is also the reviewed egress site GATE-9 requires.

``feedparser`` gives reliable access to `itunes:*` tags out of the box;
Podcasting 2.0's `podcast:chapters` / `podcast:transcript` tags are newer and
not consistently exposed under a friendly attribute name across feedparser
versions, so those two are additionally extracted with a direct, tolerant
regex pass over the raw feed text as a robust fallback -- correctness here
does not depend on guessing feedparser's exact internal key mapping.

wx-free, strict-typed.
"""

from __future__ import annotations

import base64
import re
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

import feedparser

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net_retry import retry_transient
from quill.core.podcasts import feed_auth, feed_problems, namespace_tags, transport
from quill.core.podcasts.models import PodcastEpisode
from quill.core.podcasts.namespace_tags import NamespaceTags
from quill.stability.task_manager import CancelledError

_TIMEOUT_SECONDS = 15.0
#: The secure try at a plain-http address is a courtesy, so it gets one
#: attempt and a shorter wait: a host with no https listener should cost
#: seconds, not a whole retry schedule, before the address it gave is used.
_UPGRADE_TIMEOUT_SECONDS = 8.0
#: How much of one feed Cast reads. Raised from 20 MB (check.md bug 13): seven
#: long-running shows in one real library -- The Daily among them -- publish
#: feeds bigger than that, and the cut was silent. A feed that still reaches
#: the cap is marked ``truncated`` so Player Information can say so.
_MAX_BYTES = 48_000_000
#: Redirect statuses that mean "this is the new address; keep it".
_PERMANENT_REDIRECTS: frozenset[int] = frozenset({301, 308})

_CHAPTERS_TAG_RE = re.compile(r'<podcast:chapters\b[^>]*\burl\s*=\s*"([^"]+)"', re.IGNORECASE)
_TRANSCRIPT_TAG_RE = re.compile(
    r'<podcast:transcript\b[^>]*\burl\s*=\s*"([^"]+)"'
    r'(?:[^>]*\btype\s*=\s*"([^"]*)")?',
    re.IGNORECASE,
)


class FeedReaderError(CodedError):
    """A feed fetch/parse failed (network, auth, or Safe Mode refusal).

    The message is always a plain sentence somebody can hear
    (:mod:`quill.core.podcasts.feed_problems`): ``kind`` says which sort of
    failure it was, and ``detail`` keeps the technical text for the log, where
    it helps, rather than the screen reader, where it never did (check.md bug 7).
    """

    code = "QUILL-PODCASTS-FEED-READ"

    def __init__(self, message: str = "", *, kind: str = "", detail: str = "") -> None:
        super().__init__(message)
        self.kind = kind
        self.detail = detail


class FeedAuthError(FeedReaderError):
    """The feed demanded a sign-in, or refused the credentials we sent
    (HTTP 401/403) -- distinct from a network failure so the UI can prompt
    for credentials instead of blaming the connection.

    Raised only when it really is about signing in: the podcast had saved
    credentials, or the server asked for them (``WWW-Authenticate``). A bot
    check or a paywall is a :class:`FeedReaderError` with its own kind
    (check.md bug 6), because Feed Credentials cannot fix either."""

    code = "QUILL-PODCASTS-FEED-AUTH"


class FeedTimeoutError(FeedReaderError):
    code = "QUILL-PODCASTS-FEED-TIMEOUT"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`FeedReaderError` when Safe Mode is active.

    Safe Mode (``QUILL_SAFE_MODE=1``) disables every network service.
    Subscribing to / refreshing a podcast feed is a network service.
    """
    if safe_mode:
        raise FeedReaderError(
            "Podcast feeds are disabled in Safe Mode. Restart QUILL normally to use them.",
            kind=feed_problems.SAFE_MODE,
        )


@dataclass(slots=True)
class FeedInfo:
    """Show-level metadata plus every episode found in the feed."""

    title: str
    homepage: str
    artwork_url: str
    episodes: list[PodcastEpisode]
    #: Channel-level Podcasting 2.0 tags: the show's regular hosts, its podroll,
    #: its funding link, where it is about. Separate from the per-episode set
    #: because a guest belongs to one episode and a host belongs to the show.
    tags: NamespaceTags = field(default_factory=NamespaceTags)
    #: What the feed declares about its own cadence (qc.md 5e): sy:updatePeriod
    #: and sy:updateFrequency, or Podcasting 2.0 podcast:updateFrequency.
    hint_minutes: int = 0
    hint_words: str = ""
    #: The server answered "not modified" to a conditional request: nothing
    #: has changed since the last read, so there is nothing to merge (bug 9).
    not_modified: bool = False
    #: The feed was bigger than Cast reads and was cut off, so its oldest
    #: episodes are missing from this read (check.md bug 13).
    truncated: bool = False


@dataclass(slots=True)
class FetchNotes:
    """What one fetch learned besides the feed itself.

    Handed in by a caller that keeps per-podcast bookkeeping (the refresh) and
    filled in by the fetch. ``etag`` and ``last_modified`` go both ways: in,
    the validators from the last read, sent as If-None-Match and
    If-Modified-Since; out, whatever this response carried, to keep for next
    time (check.md bug 9). Every other field is out only.
    """

    etag: str = ""
    last_modified: str = ""
    not_modified: bool = False
    #: Where the server said -- with a 301 or 308 on every hop -- this feed now
    #: lives, or ``""``. A temporary redirect never sets it (check.md bug 4).
    permanent_url: str = ""
    truncated: bool = False
    #: A plain-http address was read over https (the https-first rule).
    read_securely: bool = False


def _basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return f"Basic {token}"


def permanent_landing(url: str, hops: list[tuple[int, str]]) -> str:
    """The address to remember after *hops*, or ``""``.

    Only when **every** hop was permanent: a 301 to a 302 is a temporary
    address in the end, and Libsyn's 301-then-302 to an internal
    ``destinations`` URL is exactly the address a publisher changes when they
    switch hosts. Never a downgrade from https to plain http. A plain-http
    landing reached from a plain-http address is fine -- the old check skipped
    those, so a feed that had moved within http was never reported.
    """
    if not hops or any(code not in _PERMANENT_REDIRECTS for code, _ in hops):
        return ""
    landed = hops[-1][1]
    if not landed or landed == url:
        return ""
    if transport.is_plain_http(landed) and not transport.is_plain_http(url):
        return ""
    return landed


def _failure(error: BaseException, *, had_credentials: bool) -> FeedReaderError:
    """The exception to raise for *error*, worded for a person."""
    problem = feed_problems.classify(error, had_credentials=had_credentials)
    if problem.kind == feed_problems.SIGN_IN:
        return FeedAuthError(problem.sentence, kind=problem.kind, detail=problem.detail)
    return FeedReaderError(problem.sentence, kind=problem.kind, detail=problem.detail)


def _attempt(
    address: str, headers: dict[str, str], *, timeout: float, retry: bool, context: ssl.SSLContext
) -> tuple[bytes, list[tuple[int, str]], str, str]:
    """One address: ``(payload, redirect hops, etag, last_modified)``.

    The payload is read up to one byte past :data:`_MAX_BYTES`, so a feed that
    is too big is *detected* rather than silently cut.
    """
    request = urllib.request.Request(address, headers=headers)
    hops: list[tuple[int, str]] = []

    def _fetch_once() -> tuple[bytes, str, str]:
        """One attempt. The reviewed egress site; the retry wraps it."""
        with feed_auth.recording_redirects() as followed:
            with feed_auth.urlopen_auth_safe(request, timeout=timeout, context=context) as resp:
                payload: bytes = resp.read(_MAX_BYTES + 1)
                info = getattr(resp, "headers", None)
                etag = str(info.get("ETag", "") or "") if info is not None else ""
                modified = str(info.get("Last-Modified", "") or "") if info is not None else ""
        hops[:] = followed
        return payload, etag, modified

    payload, etag, modified = retry_transient(_fetch_once) if retry else _fetch_once()
    return payload, hops, etag, modified


def _fetch_feed_bytes(
    url: str,
    *,
    username: str = "",
    password: str = "",
    redirected_to: list[str] | None = None,
    notes: FetchNotes | None = None,
) -> bytes:
    """One HTTPS GET returning raw feed bytes -- the reviewed egress site.

    Retried on a transient failure (:mod:`quill.core.net_retry`): a refresh
    that fails because a podcast host was briefly overloaded looks exactly
    like a feed that has stopped publishing, and the listener has no way to
    tell the two apart. Two retries, a second and then two seconds later.

    A 401/403 is **not** retried -- asking three times with the same answer
    only delays the sentence that says what is wrong.

    **https first** (:func:`transport.attempts_for`, check.md bug 14): a plain
    http address is first asked for over https, once and briefly; only when
    that genuinely fails -- no https listener, a broken certificate, a web page
    where the feed should be -- is the address as given used. A refusal over
    https is final, never retried in clear text.

    *notes*, when given, carries the stored validators in (a conditional
    request; a 304 returns ``b""`` with ``notes.not_modified`` set) and what
    this response said out. *redirected_to* collects a **permanent** new
    address only.
    """
    if not transport.is_allowed(url):
        raise FeedReaderError(
            "A feed address must start with https:// or http://.",
            kind=feed_problems.BAD_ADDRESS,
        )
    redirected_to = redirected_to if redirected_to is not None else []
    notes = notes if notes is not None else FetchNotes()
    headers = {
        "User-Agent": http_client.podcast_user_agent(),
        "Accept": "application/rss+xml, application/xml, */*",
    }
    if notes.etag:
        headers["If-None-Match"] = notes.etag
    if notes.last_modified:
        headers["If-Modified-Since"] = notes.last_modified
    if username:
        # Sent preemptively rather than waiting for a 401 challenge: some
        # hosts never issue a proper WWW-Authenticate challenge, and
        # urllib's HTTPBasicAuthHandler only engages after one, so sending
        # the header up front matches every other client's behavior for
        # feeds that expect it unconditionally.
        headers["Authorization"] = _basic_auth_header(username, password)
    context = ssl.create_default_context()

    #: Where the server said this feed now lives, when it said so permanently.
    #: Collected rather than acted on: rewriting a subscription's address is a
    #: decision the listener makes per podcast (``follow_redirects``), not one
    #: a fetch makes for them -- and a saved username and password are never
    #: carried to a new host whatever they chose.
    for address in transport.attempts_for(url):
        upgrade = address != url
        try:
            payload, hops, etag, modified = _attempt(
                address,
                headers,
                timeout=_UPGRADE_TIMEOUT_SECONDS if upgrade else _TIMEOUT_SECONDS,
                retry=not upgrade,
                context=context,
            )
        except urllib.error.HTTPError as error:
            if error.code == 304:
                notes.not_modified = True
                return b""
            if upgrade and transport.may_retry_insecure(error.code):
                continue
            raise _failure(error, had_credentials=bool(username)) from error
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
            if upgrade:
                continue
            raise _failure(error, had_credentials=bool(username)) from error
        if upgrade and feed_problems.looks_like_html(payload[:4096]):
            # The https side of this host is a web page, not this feed: the
            # address the publisher gave is the one that works.
            continue
        notes.read_securely = upgrade
        notes.truncated = len(payload) > _MAX_BYTES
        notes.etag = etag
        notes.last_modified = modified
        notes.permanent_url = permanent_landing(address, hops)
        if notes.permanent_url:
            redirected_to.append(notes.permanent_url)
        return payload[:_MAX_BYTES]
    # attempts_for always ends with the address as given, and that attempt
    # either returns or raises -- so this is unreachable short of a bug.
    raise FeedReaderError(
        feed_problems.sentence_for(feed_problems.UNKNOWN), kind=feed_problems.UNKNOWN
    )


def _read_bounded(response: object, deadline: float | None, is_cancelled: object) -> bytes:
    """Read a response in chunks while honoring cancellation and a deadline."""
    if deadline is None and not callable(is_cancelled):
        raw = response.read(_MAX_BYTES)  # type: ignore[attr-defined]
        if not isinstance(raw, bytes):
            raise TypeError("Podcast feed response did not return bytes.")
        return raw
    chunks: list[bytes] = []
    while True:
        if callable(is_cancelled) and is_cancelled():
            raise CancelledError()
        if deadline is not None and time.monotonic() >= deadline:
            raise FeedTimeoutError("Podcast feed took too long to answer.")
        chunk = response.read(64 * 1024)  # type: ignore[attr-defined]
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _parse_number(raw: object) -> int:
    """``itunes:season`` / ``itunes:episode`` as a count; 0 when unreadable.

    Zero rather than a guess, and zero means *the feed did not say* rather
    than *episode zero* -- an unnumbered episode must not sort as though it
    were the first one.
    """
    try:
        number = int(str(raw or "").strip())
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def _parse_duration(raw: object) -> int:
    """``itunes:duration`` as HH:MM:SS, MM:SS, or a bare second count."""
    text = str(raw or "").strip()
    if not text:
        return 0
    if text.isdigit():
        return int(text)
    parts = text.split(":")
    if not all(p.isdigit() for p in parts) or not (1 <= len(parts) <= 3):
        return 0
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds


def _episode_extra_tags(entry_xml: str) -> tuple[str, str, str]:
    """Best-effort ``(chapters_url, transcript_url, transcript_type)`` for one
    entry's raw XML fragment."""
    from quill.core.podcasts import transcript_choice

    chapters_match = _CHAPTERS_TAG_RE.search(entry_xml)
    chapters_url = chapters_match.group(1) if chapters_match else ""
    # **Every** transcript tag, not the first (list.md 2.6). A feed may offer
    # the same words as JSON, WebVTT, SRT and HTML, and only the structured
    # ones carry cue times -- so taking whichever the publisher happened to
    # list first cost the timed reader, the chapter cascade's transcript tier
    # and Markdown timestamps, silently, on every episode of that show.
    offered = [
        (match.group(1), match.group(2) or "") for match in _TRANSCRIPT_TAG_RE.finditer(entry_xml)
    ]
    transcript_url, transcript_type = transcript_choice.best(offered)
    return chapters_url, transcript_url, transcript_type


def _split_item_fragments(raw_text: str) -> list[str]:
    """Split raw feed text into one string per ``<item>``/``<entry>`` block,
    good enough to scope the chapters/transcript regex search per-episode
    without a full second XML parse."""
    return re.split(r"(?=<item\b)|(?=<entry\b)", raw_text, flags=re.IGNORECASE)


def _entry_to_episode(entry: object, entry_xml: str) -> PodcastEpisode | None:
    title = str(getattr(entry, "title", "")).strip()
    enclosures = getattr(entry, "enclosures", None) or []
    audio_url = ""
    for enclosure in enclosures:
        href = enclosure.get("href") if isinstance(enclosure, dict) else None
        if href:
            audio_url = str(href)
            break
    if not audio_url:
        link = getattr(entry, "link", "")
        if link:
            audio_url = str(link)
    if not title or not audio_url:
        return None
    guid = str(getattr(entry, "id", "") or getattr(entry, "guid", "") or audio_url)
    chapters_url, transcript_url, transcript_type = _episode_extra_tags(entry_xml)
    duration = _parse_duration(getattr(entry, "itunes_duration", ""))
    description = str(getattr(entry, "summary", "") or getattr(entry, "description", ""))
    published = str(getattr(entry, "published", ""))
    return PodcastEpisode(
        guid=guid,
        title=title,
        audio_url=audio_url,
        published=published,
        duration_seconds=duration,
        # The publisher's own numbering and their own answer to "is this the
        # show, a trailer, or a bonus". Both were in these bytes all along and
        # both were discarded: the numbering is the only reliable order a
        # serial show has (published dates get re-stamped on a feed rebuild),
        # and the type is the publisher saying, in their vocabulary, the thing
        # an Episode Filter would otherwise have to guess from a title.
        season=_parse_number(getattr(entry, "itunes_season", "")),
        episode_number=_parse_number(getattr(entry, "itunes_episode", "")),
        episode_type=str(getattr(entry, "itunes_episodetype", "") or "").strip().lower(),
        description=description,
        chapters_url=chapters_url,
        transcript_url=transcript_url,
        transcript_type=transcript_type,
        # Who is on it, the bits the publisher marked, what else they
        # recommend -- all of it was already in these bytes and all of it was
        # being thrown away (namespace_tags.py).
        tags=namespace_tags.parse(entry_xml),
    )


def parse_feed(raw_bytes: bytes) -> FeedInfo:
    """Parse already-fetched feed bytes (pure; tolerant of malformed XML).

    Raises :class:`FeedReaderError` when the bytes are not a feed at all: a
    web page (an expired domain's sales page, FeedBurner's "this feed is gone"
    page) used to parse as a feed with no episodes and no error, so Feed Check
    called it healthy for ever (check.md bug 3). A real feed with no episodes
    is *not* an error here -- it is still that show's feed -- and the refresh
    gives it a status of its own.
    """
    parsed = feedparser.parse(raw_bytes)
    if not getattr(parsed, "version", "") and not getattr(parsed, "entries", None):
        kind = (
            feed_problems.WEB_PAGE
            if feed_problems.looks_like_html(raw_bytes[:4096])
            else feed_problems.NOT_A_FEED
        )
        raise FeedReaderError(
            feed_problems.sentence_for(kind),
            kind=kind,
            detail=f"no feed element; first bytes {raw_bytes[:120]!r}",
        )
    feed = getattr(parsed, "feed", None)
    title = str(getattr(feed, "title", "")) if feed is not None else ""
    homepage = str(getattr(feed, "link", "")) if feed is not None else ""
    image = getattr(feed, "image", None) if feed is not None else None
    artwork_url = str(image.get("href", "")) if isinstance(image, dict) else ""

    raw_text = raw_bytes.decode("utf-8", errors="replace")
    fragments = _split_item_fragments(raw_text)
    entries = list(getattr(parsed, "entries", []) or [])

    episodes: list[PodcastEpisode] = []
    for index, entry in enumerate(entries):
        # fragments[0] is anything before the first <item>/<entry>; entry
        # fragments start at index 1, aligned with feedparser's entry order
        # for well-formed feeds. A misaligned/odd feed just loses the
        # chapters/transcript extras for that entry, not the episode itself.
        fragment = fragments[index + 1] if index + 1 < len(fragments) else ""
        episode = _entry_to_episode(entry, fragment)
        if episode is not None:
            episodes.append(episode)
    # fragments[0] is the channel header -- everything before the first item --
    # which is where a feed declares its regular hosts, its podroll and its
    # funding link. Reading the whole text here would re-read every episode's
    # people as the show's own.
    channel_tags = namespace_tags.parse(fragments[0] if fragments else "")
    # ...except live items, which are channel-level but may be written anywhere
    # among the episodes, so those are looked for across the whole feed.
    channel_tags.live_items = namespace_tags.parse_live_items(raw_text)
    from quill.core.podcasts.refresh_schedule import parse_hint

    hint = parse_hint(fragments[0] if fragments else "")
    return FeedInfo(
        title=title,
        homepage=homepage,
        artwork_url=artwork_url,
        episodes=episodes,
        tags=channel_tags,
        hint_minutes=hint.minutes,
        hint_words=hint.words,
    )


def fetch_and_parse_feed(
    url: str,
    *,
    username: str = "",
    password: str = "",
    safe_mode: bool = False,
    redirected_to: list[str] | None = None,
    notes: FetchNotes | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> FeedInfo:
    """Fetch *url* and parse it in one step.

    *redirected_to*, when given, collects the address this feed has
    **permanently** moved to. Reported rather than followed: whether a
    subscription's stored address is rewritten is a per-podcast decision
    (7.20), and the fetch is not the place to make it.

    *notes* makes the request conditional (see :class:`FetchNotes`). When the
    server answers 304 the result is an empty :class:`FeedInfo` with
    ``not_modified`` set -- nothing to merge, and nothing wrong.
    """
    refuse_in_safe_mode(safe_mode)
    if is_cancelled is not None and is_cancelled():
        raise CancelledError()
    notes = notes if notes is not None else FetchNotes()
    raw_bytes = _fetch_feed_bytes(
        url, username=username, password=password, redirected_to=redirected_to, notes=notes
    )
    if notes.not_modified:
        return FeedInfo(title="", homepage="", artwork_url="", episodes=[], not_modified=True)
    if is_cancelled is not None and is_cancelled():
        raise CancelledError()
    info = parse_feed(raw_bytes)
    info.truncated = notes.truncated
    return info
