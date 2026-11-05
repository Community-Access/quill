"""Listening to and watching Media Library files (wordpress.md 6.1a).

The wx-free half of Play, Play Media Here and the captions reader:

* **What to play**: a :class:`Playable` -- title, address, audio or video, and
  any WebVTT captions tracks -- made from a Media Library row
  (:func:`from_library`) or from the audio or video block at the caret
  (:func:`media_at`). A block is found by its own comments first, so a video
  nested in a group or kept as a Markdown island is found; a bare ``<audio>``
  or ``<video>`` tag at the caret is found as well, because that is what
  Insert from Media Library writes.
* **Streamed, not saved**: :func:`stream_problem` refuses anything but HTTPS
  (or a loopback test site, the same rule the connection itself keeps), and
  nothing here writes a file.
* **Captions on request**: a WebVTT file is read (:func:`fetch_captions`, only
  from the site's own host) and :func:`caption_at` gives the words being
  spoken at a position.
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import Request

from quill.core.error_codes import CodedError
from quill.core.wordpress import block_spans as bs
from quill.core.wordpress.blocks import Block
from quill.core.wordpress.listening import Cue, language_label, parse_time
from quill.core.wordpress.site_media import MediaItem

PLAYABLE_KINDS: frozenset[str] = frozenset({"audio", "video"})

#: A captions file larger than this is not a captions file.
CAPTIONS_LIMIT = 2_000_000


class MediaPlayError(CodedError):
    """A file or captions track that cannot be played or read; the message says why."""

    code = "QUILL-WP-PLAYER-UNAVAILABLE"


@dataclass(frozen=True)
class CaptionTrack:
    src: str
    label: str
    srclang: str


@dataclass(frozen=True)
class Playable:
    """One audio or video file, as the player window needs it."""

    title: str
    url: str
    kind: str  # "audio" or "video"
    media_id: int = 0
    captions: tuple[CaptionTrack, ...] = field(default_factory=tuple)


# --------------------------------------------------------------------------- #
# addresses


def _is_loopback(host: str) -> bool:
    return (
        host in {"127.0.0.1", "::1", "[::1]", "localhost"}
        or host.endswith(".localhost")
        or host.endswith(".test")
    )


def stream_problem(url: str) -> str:
    """Why *url* will not be streamed, or "" when it can be."""
    parsed = urlparse((url or "").strip())
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if scheme == "https" and host:
        return ""
    if scheme == "http" and _is_loopback(host):
        return ""
    if not scheme or not host:
        return "This file has no web address to play from."
    return (
        "This file's address is not HTTPS, so QUILL will not stream it. "
        "Open it in your browser instead."
    )


def title_from_url(url: str) -> str:
    name = PurePosixPath(unquote(urlparse(url).path)).name
    return name or url


def same_host(url: str, site_url: str) -> bool:
    a, b = urlparse(url), urlparse(site_url)
    return bool(a.hostname) and (a.hostname or "").lower() == (b.hostname or "").lower()


# --------------------------------------------------------------------------- #
# from the Media Library


def library_captions(video: MediaItem, items: Sequence[MediaItem]) -> tuple[CaptionTrack, ...]:
    """Captions files in the library named for *video*: ``clip.en.vtt`` for ``clip.mp4``.

    That is the name Add Captions gives the file it uploads (9.6), so a video
    captioned from QUILL is found without reading any page.
    """
    stem = PurePosixPath(video.filename or title_from_url(video.source_url)).stem.lower()
    if not stem:
        return ()
    found: list[CaptionTrack] = []
    for item in items:
        name = (item.filename or title_from_url(item.source_url)).lower()
        if not name.endswith(".vtt") or not name.startswith(stem + "."):
            continue
        middle = name[len(stem) + 1 : -len(".vtt")]
        lang = middle if re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]+)?", middle) else "en"
        found.append(CaptionTrack(item.source_url, language_label(lang), lang))
    return tuple(found)


def from_library(item: MediaItem, items: Sequence[MediaItem] = ()) -> Playable | None:
    """The row as something to play, or None for a picture or a document."""
    if item.kind_label not in PLAYABLE_KINDS:
        return None
    captions = library_captions(item, items) if item.kind_label == "video" else ()
    return Playable(
        title=item.title or item.filename or title_from_url(item.source_url),
        url=item.source_url,
        kind=item.kind_label,
        media_id=item.id,
        captions=captions,
    )


# --------------------------------------------------------------------------- #
# from the document

_TAG = re.compile(r"<(audio|video)\b([^>]*)>(.*?)</\1>", re.S | re.I)
_SRC = re.compile(r"""\bsrc\s*=\s*["']([^"']+)["']""", re.I)
_TRACK = re.compile(r"<track\b([^>]*)/?>", re.I)
_ATTR = re.compile(r"""\b([a-z-]+)\s*=\s*["']([^"']*)["']""", re.I)
_CAPTION = re.compile(r"<figcaption[^>]*>(.*?)</figcaption>", re.S | re.I)
_TAGS = re.compile(r"<[^>]+>")


def _tracks_from_markup(markup: str) -> list[CaptionTrack]:
    tracks: list[CaptionTrack] = []
    for match in _TRACK.finditer(markup):
        attrs = {k.lower(): html.unescape(v) for k, v in _ATTR.findall(match.group(1))}
        kind = attrs.get("kind", "captions")
        if attrs.get("src") and kind in {"captions", "subtitles"}:
            lang = attrs.get("srclang", "en")
            tracks.append(
                CaptionTrack(attrs["src"], attrs.get("label") or language_label(lang), lang)
            )
    return tracks


def _from_tag(markup: str) -> Playable | None:
    match = _TAG.search(markup)
    if match is None:
        return None
    kind = match.group(1).lower()
    src = _SRC.search(match.group(2))
    url = html.unescape(src.group(1)) if src else ""
    if not url:  # <video><source src=...></video>
        inner = re.search(r"<source\b([^>]*)>", match.group(3), re.I)
        found = _SRC.search(inner.group(1)) if inner else None
        url = html.unescape(found.group(1)) if found else ""
    if not url:
        return None
    caption = _CAPTION.search(markup)
    words = " ".join(html.unescape(_TAGS.sub("", caption.group(1))).split()) if caption else ""
    tracks = tuple(_tracks_from_markup(match.group(3))) if kind == "video" else ()
    return Playable(words or title_from_url(url), url, kind, captions=tracks)


def _from_block(block: Block) -> Playable | None:
    name = block.name or ""
    kind = name.removeprefix("core/")
    if kind not in PLAYABLE_KINDS:
        return None
    found = _from_tag(block.inner_html)
    url = str(block.attrs.get("src") or (found.url if found else ""))
    if not url:
        return None
    tracks: list[CaptionTrack] = []
    for raw in block.attrs.get("tracks") or []:
        if isinstance(raw, dict) and raw.get("src"):
            lang = str(raw.get("srcLang") or raw.get("srclang") or "en")
            tracks.append(
                CaptionTrack(str(raw["src"]), str(raw.get("label") or language_label(lang)), lang)
            )
    if not tracks and found is not None:
        tracks = list(found.captions)
    media_id = block.attrs.get("id")
    return Playable(
        title=found.title if found else title_from_url(url),
        url=url,
        kind=kind,
        media_id=media_id if isinstance(media_id, int) else 0,
        captions=tuple(tracks) if kind == "video" else (),
    )


def _line(text: str, offset: int) -> str:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    return text[start : end if end >= 0 else len(text)]


def media_at(
    text: str, text_format: str, caret: int, islands: Mapping[str, str] | None = None
) -> Playable | None:
    """The audio or video block (or bare tag) at *caret*, or None."""
    fmt = "html" if text_format == "html" else "markdown"
    try:
        spans = bs.spans_for(text, fmt)
    except Exception:  # noqa: BLE001 - a half-typed document must not stop Play
        spans = []
    index = bs.innermost_at(spans, caret) if spans else None
    chain = [index, *bs.ancestors(spans, index)] if index is not None else []
    for i in chain:
        if spans[i].name.removeprefix("core/") in PLAYABLE_KINDS:
            block = bs.block_at(text, fmt, spans, i, islands)
            found = _from_block(block) if block is not None else None
            if found is not None:
                return found
    if index is not None:
        span = spans[index]
        region = (islands or {}).get(span.island, "") or text[span.start : span.end]
        found = _from_tag(region)
        if found is not None:
            return found
    return _from_tag(_line(text, caret))


# --------------------------------------------------------------------------- #
# captions


def parse_webvtt(text: str) -> list[Cue]:
    """The cues of a WebVTT file; NOTE, STYLE and REGION blocks are skipped."""
    cues: list[Cue] = []
    body = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    for chunk in re.split(r"\n\s*\n", body):
        lines = [line for line in chunk.split("\n") if line.strip()]
        timing = next((n for n, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            continue
        left, _, right = lines[timing].partition("-->")
        try:
            start = parse_time(left.strip())
            end = parse_time(right.strip().split()[0])
        except (ValueError, IndexError):
            continue
        words = " ".join(html.unescape(_TAGS.sub("", " ".join(lines[timing + 1 :]))).split())
        if words and end > start:
            cues.append(Cue(start, end, words))
    return cues


def caption_at(cues: Sequence[Cue], position_ms: int) -> str:
    """The words on screen at *position_ms*, or ""."""
    seconds = max(0, position_ms) / 1000.0
    return " ".join(c.text for c in cues if c.start <= seconds < c.end)


def fetch_captions(api: Any, track: CaptionTrack, site_url: str) -> list[Cue]:
    """Read one captions track from the site (run in the background).

    Only from the site's own host and only over HTTPS (or a loopback test
    site): a captions address in a page can point anywhere, and QUILL reads
    nothing from a host the person did not connect.
    """
    problem = stream_problem(track.src)
    if problem:
        raise MediaPlayError(problem)
    if not same_host(track.src, site_url):
        raise MediaPlayError(
            "These captions are on another site, so QUILL does not read them. "
            "Open the video in your browser to see them."
        )
    context = None
    if urlparse(track.src).scheme == "https":
        from quill.core.net import verified_ssl_context

        context = verified_ssl_context()
    request = Request(track.src, headers={"User-Agent": "QUILL", "Accept": "text/vtt"})
    try:
        with api._opener(request, timeout=api.timeout, context=context) as response:
            raw = response.read()
    except Exception as exc:  # noqa: BLE001 - every failure becomes one sentence
        raise MediaPlayError(
            f"The captions could not be read from the site ({exc}). Try again, or open the "
            "video in your browser."
        ) from exc
    if len(raw) > CAPTIONS_LIMIT:
        raise MediaPlayError("That captions file is too large to be captions.")
    cues = parse_webvtt(raw.decode("utf-8", errors="replace"))
    if not cues:
        raise MediaPlayError("That captions file has no captions in it that QUILL could read.")
    return cues
