"""Captions, transcripts, listening versions and named embeds (wordpress.md 9.6).

The markup half of File > WordPress > Media and Files, with no wx and no
network of its own (the oEmbed question goes through :class:`WordPressApi`):

* **Captions** are reviewed as one line per cue -- its time, then its words --
  because that is a shape a screen reader can walk with Up and Down. WebVTT
  proper (a header, then blank-line-separated cues) is made from the reviewed
  lines, and the problems that would make a player drop the file are found
  before anything is uploaded.
* **Media blocks** are found in the document by their own block comments, so a
  video nested in a group is found as well as one at the top. In a Markdown
  document a video or audio block is an *island* (``fences``), and the island's
  text in the working copy is what changes; the line the writer sees does not.
* **Embeds** are named by asking the site's oEmbed proxy what each link is,
  and given a caption where they have none.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.blocks import parse, serialize_block

# --------------------------------------------------------------------------- #
# captions: review lines and WebVTT


class CaptionsError(CodedError):
    """Captions a player would refuse; the message says which line and why."""

    code = "QUILL-WP-CAPTIONS-INVALID"


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


_TIME = r"(?:\d+:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?"
_REVIEW_LINE = re.compile(rf"^\s*({_TIME})\s*-->\s*({_TIME})\s*(.*)$")

LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "uk": "Ukrainian",
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
}


def language_label(code: str | None) -> str:
    short = (code or "en").split("-", 1)[0].lower()
    return LANGUAGE_NAMES.get(short, short or "English")


def timestamp(seconds: float) -> str:
    total = int(round(max(0.0, seconds) * 1000))
    hours, total = divmod(total, 3_600_000)
    minutes, total = divmod(total, 60_000)
    secs, millis = divmod(total, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def parse_time(text: str) -> float:
    parts = text.replace(",", ".").split(":")
    seconds = float(parts[-1])
    minutes = int(parts[-2]) if len(parts) >= 2 else 0
    hours = int(parts[-3]) if len(parts) >= 3 else 0
    return hours * 3600 + minutes * 60 + seconds


def cues_from_segments(segments: object, full_text: str = "", duration: float = 0.0) -> list[Cue]:
    """Cues from a transcription's segments; one cue for the whole text without them.

    A speaker's name, when the engine knows it, starts the cue ("Speaker 1:"),
    where the writer can change it to a real name in the review.
    """
    cues: list[Cue] = []
    for segment in segments or ():  # type: ignore[attr-defined]
        words = " ".join(str(getattr(segment, "text", "")).split())
        if not words:
            continue
        speaker = str(getattr(segment, "speaker", "") or "")
        cues.append(
            Cue(
                float(getattr(segment, "start_seconds", 0.0)),
                float(getattr(segment, "end_seconds", 0.0)),
                f"{speaker}: {words}" if speaker else words,
            )
        )
    if not cues and full_text.strip():
        cues.append(Cue(0.0, max(duration, 1.0), " ".join(full_text.split())))
    return cues


def review_text(cues: list[Cue]) -> str:
    """One line per cue: ``00:00:01.000 --> 00:00:04.200 The words``."""
    return "\n".join(f"{timestamp(c.start)} --> {timestamp(c.end)} {c.text}" for c in cues) + "\n"


def cues_from_review(text: str) -> list[Cue]:
    """The reviewed lines back to cues, or :class:`CaptionsError` naming the line."""
    cues: list[Cue] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        match = _REVIEW_LINE.match(line)
        if match is None:
            raise CaptionsError(
                f"Line {number} does not start with a time, like 00:00:01.000 --> 00:00:04.000, "
                "so a player would skip it. Put the time back, or delete the line."
            )
        start, end = parse_time(match.group(1)), parse_time(match.group(2))
        words = match.group(3).strip()
        if end <= start:
            raise CaptionsError(
                f"Line {number} ends before it starts. Make the second time later than the first."
            )
        if not words:
            raise CaptionsError(f"Line {number} has a time but no words. Add them, or delete it.")
        cues.append(Cue(start, end, words))
    if not cues:
        raise CaptionsError("There are no captions left to upload.")
    return cues


def to_webvtt(cues: list[Cue]) -> str:
    parts = ["WEBVTT", ""]
    for cue in cues:
        # "-->" inside the words would end the cue's text early.
        words = cue.text.replace("-->", "->")
        parts += [f"{timestamp(cue.start)} --> {timestamp(cue.end)}", words, ""]
    return "\n".join(parts)


def transcript_paragraphs(segments: object, full_text: str) -> str:
    """The transcript for review: one paragraph per speaker turn, or a few sentences each."""
    cues = cues_from_segments(segments, full_text)
    if not cues:
        return ""
    if any(getattr(s, "speaker", "") for s in segments or ()):  # type: ignore[attr-defined]
        paragraphs: list[str] = []
        for cue in cues:
            speaker, sep, words = cue.text.partition(": ")
            if sep and paragraphs and paragraphs[-1].startswith(speaker + ": "):
                paragraphs[-1] += " " + words
            else:
                paragraphs.append(cue.text)
        return "\n\n".join(paragraphs) + "\n"
    groups = [cues[i : i + 5] for i in range(0, len(cues), 5)]
    return "\n\n".join(" ".join(c.text for c in group) for group in groups) + "\n"


# --------------------------------------------------------------------------- #
# media blocks in the document


@dataclass(frozen=True)
class Span:
    start: int
    end: int


def _block_pattern(name: str) -> re.Pattern[str]:
    short = name.removeprefix("core/")
    return re.compile(
        rf"<!--\s+wp:{short}(?:\s+(\{{.*?\}}))?\s+-->(.*?)<!--\s+/wp:{short}\s+-->", re.S
    )


def _matches(markup: str, attrs_text: str | None, media_id: int, src: str) -> bool:
    if media_id and attrs_text:
        try:
            attrs = json.loads(attrs_text)
        except ValueError:
            attrs = {}
        if isinstance(attrs, dict) and attrs.get("id") == media_id:
            return True
    return bool(src) and (f'src="{src}"' in markup or f'src="{html.escape(src)}"' in markup)


def find_media_block(text: str, name: str, media_id: int, src: str) -> Span | None:
    """Where the ``core/video`` or ``core/audio`` block for one library file sits."""
    for match in _block_pattern(name).finditer(text):
        if _matches(match.group(0), match.group(1), media_id, src):
            return Span(match.start(), match.end())
    return None


def find_media_island(islands: Mapping[str, str], name: str, media_id: int, src: str) -> str:
    """The island token holding that block in a Markdown document, or ""."""
    for token, markup in islands.items():
        if find_media_block(markup, name, media_id, src) is not None:
            return token
    return ""


def island_line(text: str, token: str) -> Span | None:
    """The ``::: block ... <token>`` line in a Markdown document."""
    match = re.search(rf"^:::[ \t]+block[ \t][^\n]*?[ \t]{re.escape(token)}[ \t]*$", text, re.M)
    return Span(match.start(), match.end()) if match else None


def new_island_token(islands: Mapping[str, str], stem: str) -> str:
    number = 1
    while f"{stem}-{number}" in islands:
        number += 1
    return f"{stem}-{number}"


def island_fence(name: str, token: str, label: str = "") -> str:
    middle = f" {label}" if label and not re.search(r"\s", label) else ""
    return f"::: block {name}{middle} {token}"


def track_markup(src: str, label: str, srclang: str) -> str:
    return (
        f'<track src="{html.escape(src)}" label="{html.escape(label)}" kind="captions" '
        f'srclang="{html.escape(srclang)}"/>'
    )


def add_track(block_text: str, src: str, label: str, srclang: str) -> str:
    """A ``core/video`` block with one more captions track, in markup and attributes."""
    blocks = parse(block_text)
    block = next((b for b in blocks if b.name == "core/video"), None)
    if block is None:
        return block_text
    tracks = [t for t in block.attrs.get("tracks", []) or [] if isinstance(t, dict)]
    if any(t.get("src") == src for t in tracks):
        return block_text
    tracks.append({"src": src, "label": label, "kind": "captions", "srcLang": srclang})
    block.attrs["tracks"] = tracks
    tag = track_markup(src, label, srclang)
    for index, part in enumerate(block.inner_content):
        if isinstance(part, str) and "</video>" in part:
            block.inner_content[index] = part.replace("</video>", tag + "</video>", 1)
            break
    return "".join(serialize_block(b) for b in blocks)


def video_block(media_id: int, src: str, *, track: tuple[str, str, str] | None = None) -> str:
    attrs: dict[str, object] = {"id": media_id}
    inner = ""
    if track is not None:
        src_, label, lang = track
        attrs["tracks"] = [{"src": src_, "label": label, "kind": "captions", "srcLang": lang}]
        inner = track_markup(*track)
    return (
        f"<!-- wp:video {json.dumps(attrs, separators=(',', ':'))} -->\n"
        f'<figure class="wp-block-video"><video controls src="{html.escape(src)}">{inner}</video>'
        "</figure>\n<!-- /wp:video -->"
    )


def audio_block(media_id: int, src: str, caption: str = "") -> str:
    figcaption = (
        f'<figcaption class="wp-element-caption">{html.escape(caption, quote=False)}</figcaption>'
        if caption
        else ""
    )
    return (
        f'<!-- wp:audio {{"id":{media_id}}} -->\n'
        f'<figure class="wp-block-audio"><audio controls src="{html.escape(src)}"></audio>'
        f"{figcaption}</figure>\n<!-- /wp:audio -->"
    )


def details_markdown(summary: str, body: str) -> str:
    """A ``::: details`` fence around plain paragraphs (Markdown documents)."""
    safe = summary.replace('"', "'")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    return "\n".join([f'::: details "{safe}"', "", "\n\n".join(paragraphs), "", "::: end details"])


def details_html(summary: str, body: str) -> str:
    """The same as block markup (HTML documents), the way the block editor saves it."""
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", body) if p.strip()]
    inner = "".join(
        f"<!-- wp:paragraph -->\n<p>{html.escape(p, quote=False)}</p>\n<!-- /wp:paragraph -->"
        for p in paragraphs
    )
    return (
        f'<!-- wp:details -->\n<details class="wp-block-details"><summary>'
        f"{html.escape(summary, quote=False)}</summary>{inner}</details>\n<!-- /wp:details -->"
    )


# --------------------------------------------------------------------------- #
# embeds (9.6)


@dataclass(frozen=True)
class Embed:
    url: str
    span: Span
    #: "fence" (a ``::: embed`` line), "html" (block markup in the text) or "island".
    where: str
    token: str = ""
    captioned: bool = False


_EMBED_FENCE = re.compile(r"^:::[ \t]+embed[ \t]+(\S+)[^\n]*$", re.M)


def find_embeds(text: str, text_format: str, islands: Mapping[str, str]) -> list[Embed]:
    found: list[Embed] = []
    if text_format == "markdown":
        for match in _EMBED_FENCE.finditer(text):
            found.append(Embed(match.group(1), Span(match.start(), match.end()), "fence"))
        for token, markup in islands.items():
            line = island_line(text, token)
            embed = _first_embed(markup)
            if line is not None and embed is not None:
                url, captioned = embed
                found.append(Embed(url, line, "island", token, captioned))
    else:
        for match in _block_pattern("core/embed").finditer(text):
            embed = _first_embed(match.group(0))
            if embed is not None:
                span = Span(match.start(), match.end())
                found.append(Embed(embed[0], span, "html", "", embed[1]))
    return sorted(found, key=lambda e: e.span.start)


def _first_embed(markup: str) -> tuple[str, bool] | None:
    for block in parse(markup):
        if block.name == "core/embed" and isinstance(block.attrs.get("url"), str):
            return str(block.attrs["url"]), "<figcaption" in block.inner_html
    return None


def caption_embed(markup: str, caption: str) -> str:
    """Embed markup with a caption added, the way the block editor saves one."""
    tag = f'<figcaption class="wp-element-caption">{html.escape(caption, quote=False)}</figcaption>'
    return re.sub(r"</div></figure>", "</div>" + tag + "</figure>", markup, count=1)


@dataclass(frozen=True)
class OEmbedInfo:
    title: str
    author: str
    provider: str

    def caption(self) -> str:
        return self.title


def oembed(api: WordPressApi, url: str) -> OEmbedInfo:
    """What a link is, asked of the site's own oEmbed proxy (``oembed/1.0/proxy``)."""
    raw = api.get("oembed/1.0/proxy", url=url)
    data = raw if isinstance(raw, dict) else {}
    return OEmbedInfo(
        title=" ".join(str(data.get("title", "") or "").split()),
        author=" ".join(str(data.get("author_name", "") or "").split()),
        provider=" ".join(str(data.get("provider_name", "") or "").split()),
    )


# --------------------------------------------------------------------------- #
# the listening version


LISTEN_MARK = "quill-listening-version"


def fingerprint(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()[:16]


def minutes_label(duration_ms: int) -> str:
    minutes = max(1, round(duration_ms / 60000)) if duration_ms > 0 else 0
    if not minutes:
        return ""
    return "1 minute" if minutes == 1 else f"{minutes} minutes"


def listening_label(kind: str, duration_ms: int) -> str:
    noun = "page" if kind == "page" else "post"
    length = minutes_label(duration_ms)
    return f"Listen to this {noun} ({length})" if length else f"Listen to this {noun}"


def strip_listening_block(text: str, text_format: str, islands: Mapping[str, str]) -> str:
    """The text without a listening version this command added before."""
    if text_format == "markdown":
        for token, markup in islands.items():
            if LISTEN_MARK in markup:
                line = island_line(text, token)
                if line is not None:
                    end = line.end + (2 if text[line.end : line.end + 2] == "\n\n" else 0)
                    return text[: line.start] + text[end:]
        return text
    for match in _block_pattern("core/audio").finditer(text):
        if LISTEN_MARK in match.group(0):
            end = match.end() + (2 if text[match.end() : match.end() + 2] == "\n\n" else 0)
            return text[: match.start()] + text[end:]
    return text


def listening_audio_block(media_id: int, src: str, label: str) -> str:
    block = audio_block(media_id, src, label)
    block = block.replace('class="wp-block-audio"', f'class="wp-block-audio {LISTEN_MARK}"', 1)
    old_attrs = f'{{"id":{media_id}}}'
    return block.replace(old_attrs, f'{{"id":{media_id},"className":"{LISTEN_MARK}"}}', 1)
