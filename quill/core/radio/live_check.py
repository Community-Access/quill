"""Check that each Find Streams candidate is live audio before it is listed.

A website scan finds addresses that *look* like streams. Some are dead, some
answer with a web page, and some are a podcast episode -- audio, but a file,
not a station. So each candidate is opened and only its headers and first
4 KB are read (:data:`PROBE_BYTES`):

* recognisable audio (:func:`~quill.core.radio.audio_sniff.sniff_codec`) with
  **no** ``Content-Length`` is a live stream; with one it is a file;
* an HLS playlist is live only by the HLS rules in
  :func:`~quill.core.radio.audio_sniff.read_hls`, and a playlist (M3U, PLS,
  XSPF, ASX) is as live as its first entry, read one level deep;
* a web page, a 404 or an encrypted playlist is *not audio* and is left out;
* anything that could not be answered -- a timeout, a refusal, a 403, a server
  error, or the overall time running out -- stays listed as **not checked**, so
  nothing disappears just because a server was slow.

``icy-name``, ``icy-br`` and ``icy-genre`` are read from the headers so a
checked row can say what it is. The checks run a few at a time
(:data:`MAX_WORKERS`) under one overall deadline (:data:`TOTAL_SECONDS`).

There is no request code here. The caller passes its own reviewed egress
function (``link_finder._probe``, which reads through
:func:`quill.core.net_public.fetch`), so this module adds no network site. An
address that is not on the public internet -- the page named a router, a NAS,
this computer -- is left out ("not on the public internet"), never listed,
because Test would otherwise hand it to the player.

The idea of proving a candidate is live audio before listing it is from Andre
Louis's StreamSift (https://github.com/OnjLouis/StreamSift); this is QUILL's
own implementation, not a port.

wx-free, strict-typed.
"""

from __future__ import annotations

import concurrent.futures
import http.client
import re
import time
import urllib.error
import urllib.parse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from quill.core.net_public import HttpReply, NotPublicAddress, RefusedAddress
from quill.core.radio.audio_sniff import read_hls, sniff_codec

__all__ = [
    "LIVE",
    "FILE",
    "NOT_AUDIO",
    "UNCHECKED",
    "OUT_OF_TIME",
    "TOO_MANY",
    "HttpReply",
    "Verdict",
    "check_urls",
    "verdict_from_reply",
]

LIVE = "live"
FILE = "file"
NOT_AUDIO = "not audio"
UNCHECKED = "not checked"

#: The most of a candidate's body that is ever read.
PROBE_BYTES = 4096
#: Checks in flight at once, and the most candidates checked per scan.
MAX_WORKERS = 4
MAX_CHECKS = 16
#: The whole check, start to finish. What is unanswered by then is "not checked".
TOTAL_SECONDS = 20.0

#: Why a link QUILL never contacted is "not checked": the scan's own limits,
#: not the server's fault. "it took too long to answer" is kept for a link
#: that was asked and timed out.
TOO_MANY = "there were too many links to check them all"
OUT_OF_TIME = "QUILL ran out of time before checking it"

_NAME_LIMIT = 60
#: What a server says when nobody named the stream; the host is used instead.
_PLACEHOLDER_NAMES = frozenset({"", "unnamed server", "no name", "stream", "unknown", "untitled"})
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]+")
_PLAYLIST_TYPES = ("mpegurl", "scpls", "xspf", "x-ms-asf", "ms-asx")


#: ``get(url, timeout) -> HttpReply``; raises on network failure.
Getter = Callable[[str, float], HttpReply]


@dataclass(frozen=True, slots=True)
class Verdict:
    """One candidate's check: :data:`LIVE`, :data:`FILE`, :data:`NOT_AUDIO` or
    :data:`UNCHECKED`, with what was learnt on the way."""

    state: str
    codec: str = ""
    bitrate_kbps: int = 0
    name: str = ""
    genre: str = ""
    #: Why, in a few words -- above all why a link is "not checked".
    note: str = ""


def clean_header_text(value: str) -> str:
    """A server-supplied header (``icy-name``) made safe to show and speak.

    Headers arrive decoded as Latin-1; most stations actually send UTF-8, so
    that is tried first. Control characters go, whitespace collapses, and the
    result is capped at :data:`_NAME_LIMIT` characters.
    """
    try:
        value = value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    value = " ".join(_CONTROL_RE.sub(" ", value).split())
    if value.lower().strip(" -_.") in _PLACEHOLDER_NAMES:
        return ""
    if len(value) <= _NAME_LIMIT:
        return value
    # Cut at a word, with no ellipsis: "dot dot dot" mid-row helps nobody.
    cut = value[:_NAME_LIMIT]
    return (cut.rsplit(" ", 1)[0] if " " in cut else cut).rstrip(" ,;:-")


def _bitrate(value: str) -> int:
    match = re.match(r"\s*(\d{1,5})", value or "")
    kbps = int(match.group(1)) if match else 0
    return kbps if 0 < kbps <= 10000 else 0


def _header(headers: Mapping[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name:
            return str(value)
    return ""


def _looks_like_html(body: bytes, content_type: str) -> bool:
    head = body[:512].lstrip().lower()
    return "html" in content_type or head.startswith((b"<!doctype html", b"<html", b"<head"))


def _first_entry(text: str, url: str, content_type: str) -> str:
    from quill.core.radio.playlist_formats import parse_playlist

    stations = parse_playlist(text, url=url, content_type=content_type)
    return stations[0].stream_url if stations else ""


def verdict_from_reply(reply: HttpReply, url: str) -> tuple[Verdict, str]:
    """Judge one reply (pure): ``(verdict, address to read next or "")``.

    The second value is set for a playlist or an HLS master: the caller reads
    that address once and judges it instead.
    """
    headers = reply.headers
    content_type = _header(headers, "content-type").lower()

    def heard(state: str, codec: str) -> Verdict:
        return Verdict(
            state,
            codec=codec,
            bitrate_kbps=_bitrate(_header(headers, "icy-br")),
            name=clean_header_text(_header(headers, "icy-name")),
            genre=clean_header_text(_header(headers, "icy-genre")),
        )

    if reply.status in (404, 410):
        return Verdict(NOT_AUDIO, note=f"the server said it is gone ({reply.status})"), ""
    if reply.status in (401, 403):
        return Verdict(
            UNCHECKED, note=f"the server refused to let QUILL check ({reply.status})"
        ), ""
    if reply.status >= 400:
        return Verdict(UNCHECKED, note=f"the server had an error ({reply.status})"), ""
    codec = sniff_codec(reply.body)
    if codec:
        state = FILE if _header(headers, "content-length").strip() else LIVE
        return heard(state, codec), ""
    text = reply.body.decode("utf-8", errors="replace")
    base = reply.final_url or url
    hls = read_hls(text, base)
    if hls.kind == "live":
        return heard(LIVE, "HLS"), ""
    if hls.kind == "recording":
        return heard(FILE, "HLS"), ""
    if hls.kind == "encrypted":
        return Verdict(NOT_AUDIO, note="an encrypted HLS stream"), ""
    if hls.kind == "video":
        return Verdict(NOT_AUDIO, note="a video stream"), ""
    if hls.kind == "master":
        return Verdict(UNCHECKED, note="an HLS playlist QUILL could not follow"), hls.follow
    if _looks_like_html(reply.body, content_type):
        return Verdict(NOT_AUDIO, note="a web page"), ""
    entry = _first_entry(text, base, content_type)
    if entry:
        return Verdict(UNCHECKED, note="a playlist QUILL could not follow"), entry
    if content_type.startswith("audio/") and not any(t in content_type for t in _PLAYLIST_TYPES):
        return Verdict(UNCHECKED, note="audio QUILL could not recognise"), ""
    return Verdict(NOT_AUDIO, note="not audio"), ""


def _icy_status(error: BaseException) -> bool:
    """A SHOUTcast v1 server answers ``ICY 200 OK``, which http.client refuses."""
    return isinstance(error, http.client.BadStatusLine) and "ICY 200" in str(error)


#: Why a link is left out when it is not on the public internet.
NOT_PUBLIC = "not on the public internet"


def _failure(error: BaseException) -> Verdict:
    if isinstance(error, NotPublicAddress):
        return Verdict(NOT_AUDIO, note=NOT_PUBLIC)
    if isinstance(error, RefusedAddress):
        return Verdict(NOT_AUDIO, note="an address QUILL does not read")
    if isinstance(error, urllib.error.HTTPError):
        return verdict_from_reply(
            HttpReply(error.code, dict(error.headers or {}), b""), error.geturl() or ""
        )[0]
    if _icy_status(error):
        return Verdict(LIVE, codec="", note="a SHOUTcast server")
    reason = getattr(error, "reason", error)
    if isinstance(reason, TimeoutError) or isinstance(error, TimeoutError):
        return Verdict(UNCHECKED, note="it took too long to answer")
    if isinstance(reason, ConnectionRefusedError):
        return Verdict(UNCHECKED, note="the server refused the connection")
    return Verdict(UNCHECKED, note="it could not be reached")


def check_url(url: str, get: Getter, deadline: float) -> Verdict:
    """Check one address, following a playlist or HLS master at most once."""
    for _depth in range(2):
        remaining = deadline - time.monotonic()
        if remaining <= 0.5:
            return Verdict(UNCHECKED, note=OUT_OF_TIME)
        try:
            reply = get(url, remaining)
        except Exception as error:  # noqa: BLE001 - every failure is "not checked"
            return _failure(error)
        verdict, follow = verdict_from_reply(reply, url)
        if not follow:
            return verdict
        url = follow
    return Verdict(UNCHECKED, note="a playlist of playlists")


def check_urls(
    urls: Sequence[str],
    get: Getter,
    *,
    total_seconds: float = TOTAL_SECONDS,
    workers: int = MAX_WORKERS,
    limit: int = MAX_CHECKS,
    on_verdict: Callable[[str, Verdict], None] | None = None,
) -> dict[str, Verdict]:
    """Check *urls* a few at a time under one deadline: ``{url: verdict}``.

    Every address gets a verdict. Those past *limit*, and those still waiting
    when the deadline passes, are :data:`UNCHECKED` -- listed, and said to be
    unchecked, rather than dropped.

    *on_verdict*, when given, is called with ``(url, verdict)`` from the worker
    thread as each check finishes, so a window can show the name a stream
    reports while the rest are still being checked. A callback that raises is
    ignored: showing progress must never fail a scan.
    """

    def _checked(url: str) -> Verdict:
        verdict = check_url(url, get, deadline)
        if on_verdict is not None:
            try:
                on_verdict(url, verdict)
            except Exception:  # noqa: BLE001 - progress is never worth a failed scan
                pass
        return verdict

    deadline = time.monotonic() + total_seconds
    verdicts: dict[str, Verdict] = {url: Verdict(UNCHECKED, note=TOO_MANY) for url in urls[limit:]}
    to_check = list(dict.fromkeys(urls[:limit]))
    if not to_check:
        return verdicts
    pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, workers), thread_name_prefix="radio-live-check"
    )
    try:
        futures = {pool.submit(_checked, url): url for url in to_check}
        done, _pending = concurrent.futures.wait(
            futures, timeout=max(0.0, deadline - time.monotonic())
        )
        for future, url in futures.items():
            if future in done and future.exception() is None:
                verdicts[url] = future.result()
            else:
                verdicts[url] = Verdict(UNCHECKED, note=OUT_OF_TIME)
    finally:
        # Do not wait for stragglers: each is bounded by its own socket timeout.
        pool.shutdown(wait=False, cancel_futures=True)
    return verdicts


def https_twin_url(url: str) -> str:
    """*url* with its scheme dropped, so an http and an https copy compare equal."""
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(parsed._replace(scheme=""))
