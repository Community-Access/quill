"""The QUILL Ecosystem Bridge (PRD 20).

QUILL Social sits inside a family of accessible QUILL apps -- Editor, Radio,
Cast, Audio Studio, QuilleBeacon (PRD 20). Rather than performing real inter-app
IPC (which would tie tests to whichever apps happen to be installed), this
module produces structured, inspectable *intents*: small dataclasses that
describe exactly what would be handed to another app. Each QUILL app integration
is therefore a clean boundary -- the intent is deterministic and unit-testable,
and a live bridge can be attached later without changing callers.

Every intent carries a ``kind``, a ``to_dict`` for persistence/transport, and a
``describe()`` plain-language summary suitable for a screen reader. Attribution
is preserved through every export and clip (PRD 20.4).

Also here: a thread-to-Markdown exporter powering "Copy as Markdown" and "Send
to QUILL" (PRD 14.3, 20.1). This module is wx-free, has no I/O, and uses no
wall-clock except through :func:`quill_social.model.now_ms`, passed explicitly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from quill_social.model import SocialItem, now_ms

# Beacon target kinds (PRD 20.5).
BEACON_KINDS = (
    "post",
    "thread",
    "profile",
    "feed",
    "github",
    "podcast-chapter",
    "audio-timepoint",
    "heading",
    "campaign-item",
)


def _fmt_clock(ms: int) -> str:
    """``mm:ss`` (or ``h:mm:ss``) for a spoken time point."""
    total = max(0, int(ms)) // 1000
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _attribution(item: SocialItem) -> str:
    """A stable, human attribution line for a post (PRD 20.4 preserve attribution)."""
    who = item.author_display or item.author_handle or "unknown author"
    handle = item.author_handle
    if handle and handle not in who:
        return f"{who} ({handle})"
    return who


# -- thread to markdown -----------------------------------------------------


def thread_to_markdown(
    items: list[SocialItem],
    *,
    title: str = "",
    include_attribution: bool = True,
) -> str:
    """Render a thread/conversation as Markdown (PRD 14.3, 20.1).

    Each post becomes a block with its author attribution and text; replies are
    kept in the given reading order. This is the payload behind "Copy as
    Markdown", "Save a thread as a document", and "Export conversations to
    Markdown" (PRD 20.1). ``items`` is taken as already ordered by the caller.
    """
    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
        lines.append("")
    for idx, item in enumerate(items):
        if include_attribution:
            lines.append(f"## {_attribution(item)}")
        if item.content_warning:
            lines.append(f"> Content warning: {item.content_warning}")
            lines.append("")
        body = item.text.strip()
        if body:
            lines.append(body)
        for media in item.media:
            alt = media.alt_text.strip() or "no alt text"
            lines.append("")
            lines.append(f"[{media.kind}: {alt}]")
        if idx != len(items) - 1:
            lines.append("")
            lines.append("---")
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


# -- intents ----------------------------------------------------------------


@dataclass
class QuillDocumentIntent:
    """Send a post or thread to QUILL as a document (PRD 20.1)."""

    kind: str = "quill.document"
    title: str = ""
    markdown: str = ""
    source_item_ids: list[str] = field(default_factory=list)
    attribution: list[str] = field(default_factory=list)
    created: int = field(default_factory=now_ms)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "markdown": self.markdown,
            "source_item_ids": list(self.source_item_ids),
            "attribution": list(self.attribution),
            "created": self.created,
        }

    def describe(self) -> str:
        n = len(self.source_item_ids)
        who = ", ".join(self.attribution) if self.attribution else "unknown"
        subject = self.title or "a thread"
        return f"Send {subject} ({n} post(s) by {who}) to QUILL as a document."


@dataclass
class BeaconTargetIntent:
    """A QuilleBeacon navigation/share target (PRD 20.5)."""

    kind: str = "post"  # one of BEACON_KINDS
    ref: str = ""  # id, uri, or url the beacon points at
    label: str = ""
    beacon_kind: str = "beacon.target"

    def to_dict(self) -> dict:
        return {
            "kind": self.beacon_kind,
            "target_kind": self.kind,
            "ref": self.ref,
            "label": self.label,
        }

    def describe(self) -> str:
        label = self.label or self.ref or "unnamed target"
        return f"Beacon target ({self.kind}): {label}."


@dataclass
class RadioStreamIntent:
    """Add a stream to QUILL Radio presets (PRD 20.2)."""

    name: str = ""
    url: str = ""
    kind: str = "radio.add_stream"
    created: int = field(default_factory=now_ms)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "name": self.name,
            "url": self.url,
            "created": self.created,
        }

    def describe(self) -> str:
        return f"Add radio stream '{self.name}' ({self.url}) to QUILL Radio presets."


@dataclass
class CastShareIntent:
    """Share a QUILL Cast episode, optionally at a chapter/time point (PRD 20.3)."""

    episode: str = ""
    chapter_ms: int | None = None
    kind: str = "cast.share"
    created: int = field(default_factory=now_ms)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "episode": self.episode,
            "chapter_ms": self.chapter_ms,
            "created": self.created,
        }

    def describe(self) -> str:
        if self.chapter_ms is not None:
            return f"Share Cast episode '{self.episode}' at {_fmt_clock(self.chapter_ms)}."
        return f"Share Cast episode '{self.episode}'."


@dataclass
class ClipIntent:
    """Create a clip from a time range in QUILL Audio Studio (PRD 20.4).

    Attribution is preserved so a clip taken from someone else's media keeps its
    credit when it returns to the composer (PRD 20.4).
    """

    media_uri: str = ""
    start_ms: int = 0
    end_ms: int = 0
    attribution: str = ""
    source_item_id: str = ""
    kind: str = "audio_studio.clip"
    created: int = field(default_factory=now_ms)

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "media_uri": self.media_uri,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
            "attribution": self.attribution,
            "source_item_id": self.source_item_id,
            "created": self.created,
        }

    def describe(self) -> str:
        span = f"{_fmt_clock(self.start_ms)}-{_fmt_clock(self.end_ms)}"
        credit = f", crediting {self.attribution}" if self.attribution else ""
        return f"Create a clip {span} of {self.media_uri} in QUILL Audio Studio{credit}."


# -- bridge factory functions -----------------------------------------------


def send_to_quill(
    item_or_thread: SocialItem | list[SocialItem],
    *,
    title: str = "",
) -> QuillDocumentIntent:
    """Build a :class:`QuillDocumentIntent` for a post or a thread (PRD 20.1)."""
    items = [item_or_thread] if isinstance(item_or_thread, SocialItem) else list(item_or_thread)
    markdown = thread_to_markdown(items, title=title)
    return QuillDocumentIntent(
        title=title,
        markdown=markdown,
        source_item_ids=[i.item_id for i in items],
        attribution=_unique([_attribution(i) for i in items]),
    )


def beacon_target(kind: str, ref: str, label: str = "") -> BeaconTargetIntent:
    """Build a :class:`BeaconTargetIntent` (PRD 20.5).

    ``kind`` must be one of :data:`BEACON_KINDS`; an unknown kind raises so a
    typo never produces a silently dead beacon.
    """
    if kind not in BEACON_KINDS:
        raise ValueError(f"unknown beacon target kind: {kind}")
    return BeaconTargetIntent(kind=kind, ref=ref, label=label)


def add_radio_stream(name: str, url: str, *, now: Callable[[], int] = now_ms) -> RadioStreamIntent:
    """Build a :class:`RadioStreamIntent` for QUILL Radio (PRD 20.2)."""
    return RadioStreamIntent(name=name, url=url, created=now())


def share_cast(
    episode: str, chapter_ms: int | None = None, *, now: Callable[[], int] = now_ms
) -> CastShareIntent:
    """Build a :class:`CastShareIntent` for QUILL Cast (PRD 20.3)."""
    return CastShareIntent(episode=episode, chapter_ms=chapter_ms, created=now())


def audio_studio_clip(
    media: object,
    start_ms: int,
    end_ms: int,
    *,
    source_item_id: str = "",
    attribution: str = "",
    now: Callable[[], int] = now_ms,
) -> ClipIntent:
    """Build a :class:`ClipIntent` from a media object and time range (PRD 20.4).

    ``media`` is duck-typed: anything with a ``uri`` attribute (a
    :class:`quill_social.model.Media`) or a plain uri string works, so the clip
    boundary does not force a model import on callers.
    """
    uri = getattr(media, "uri", None)
    if uri is None:
        uri = str(media)
    return ClipIntent(
        media_uri=uri,
        start_ms=start_ms,
        end_ms=end_ms,
        attribution=attribution,
        source_item_id=source_item_id,
        created=now(),
    )


def _unique(values: list[str]) -> list[str]:
    """Order-preserving de-duplication."""
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out
