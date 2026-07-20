"""Pure data model for QuillBeacon (wx-free, unit-testable).

Mirrors the entities in PRD section 24. Every record carries a stable ULID-like
id and a schema version so the portable JSON archive (section 26) and a future
sync layer can round-trip it.

The model is deliberately plain dataclasses plus to/from-row helpers. Persistence
lives in ``db.py``; locator resolution lives in ``uld.py``. Keeping this module
free of wx and sqlite lets the whole domain be unit-tested in isolation, the
same separation ``quill.core.bookmarks`` uses.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = 2

# Resource types (PRD 9.1). Kept as constants so the UI and search grammar
# agree with the engine without a string-typed free-for-all.
TYPE_WEB = "web"
TYPE_WEB_HEADING = "webHeading"
TYPE_WEB_PASSAGE = "webPassage"
TYPE_FILE = "file"
TYPE_FOLDER = "folder"
TYPE_DOCUMENT = "document"
TYPE_DOC_LOCATION = "documentLocation"
TYPE_PODCAST_SHOW = "podcastShow"
TYPE_PODCAST_EPISODE = "podcastEpisode"
TYPE_PODCAST_CHAPTER = "podcastChapter"
TYPE_TIME_POINT = "timePoint"
TYPE_TIME_RANGE = "timeRange"
TYPE_TRANSCRIPT_QUOTE = "transcriptQuote"
TYPE_RADIO_STATION = "radioStation"
TYPE_RADIO_STREAM = "radioStream"
TYPE_RADIO_PROGRAM = "radioProgram"
TYPE_URI = "uri"
TYPE_VIDEO = "video"

ALL_TYPES = (
    TYPE_WEB,
    TYPE_WEB_HEADING,
    TYPE_WEB_PASSAGE,
    TYPE_FILE,
    TYPE_FOLDER,
    TYPE_DOCUMENT,
    TYPE_DOC_LOCATION,
    TYPE_PODCAST_SHOW,
    TYPE_PODCAST_EPISODE,
    TYPE_PODCAST_CHAPTER,
    TYPE_TIME_POINT,
    TYPE_TIME_RANGE,
    TYPE_TRANSCRIPT_QUOTE,
    TYPE_RADIO_STATION,
    TYPE_RADIO_STREAM,
    TYPE_RADIO_PROGRAM,
    TYPE_URI,
    TYPE_VIDEO,
)

# Health states (PRD 9.2). Conveyed as text, never color alone.
HEALTH_AVAILABLE = "available"
HEALTH_OFFLINE = "availableOffline"
HEALTH_ONLINE_ONLY = "onlineOnly"
HEALTH_MOVED = "moved"
HEALTH_CHANGED = "changed"
HEALTH_PARTIAL = "partiallyMatched"
HEALTH_AUTH = "authRequired"
HEALTH_UNAVAILABLE = "temporarilyUnavailable"
HEALTH_BROKEN = "broken"
HEALTH_UNSUPPORTED = "unsupported"
HEALTH_REMOVED = "providerRemoved"
HEALTH_ARCHIVED = "archived"
HEALTH_DELETED = "deleted"

# Relationship types (PRD 16.4).
RELATIONSHIPS = (
    "relatedTo",
    "explains",
    "contradicts",
    "sourceFor",
    "followUpTo",
    "episodeDiscusses",
    "documentReferencedBy",
    "newerVersionOf",
    "replaces",
    "duplicateOf",
    "parentOf",
    "childOf",
    "custom",
)


def _now_ms() -> int:
    """Monotonic-ish epoch milliseconds. ``time.time`` is fine for a local store."""
    return int(time.time() * 1000)


def _new_id(prefix: str) -> str:
    """Compact unique id without external deps.

    Uses os.urandom for entropy (not Math.random) and time for ordering. Good
    enough for a local-first store; a sync layer would replace this with ULID.
    """
    import os

    raw = os.urandom(8).hex()
    return f"{prefix}_{raw}"


@dataclass
class Resource:
    """The underlying thing (PRD 24.1)."""

    resource_id: str = field(default_factory=lambda: _new_id("res"))
    type: str = TYPE_URI
    canonical_id: str = ""  # normalized URL, file identity, feed/episode GUID...
    title: str = ""
    creator: str = ""
    mime: str = ""
    primary_uri: str = ""
    alt_uris: list[str] = field(default_factory=list)
    provider_ids: dict[str, str] = field(default_factory=dict)
    fingerprint: str = ""
    availability: str = HEALTH_AVAILABLE
    metadata: dict[str, Any] = field(default_factory=dict)
    created: int = field(default_factory=_now_ms)
    updated: int = field(default_factory=_now_ms)

    def to_row(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "type": self.type,
            "canonical_id": self.canonical_id,
            "title": self.title,
            "creator": self.creator,
            "mime": self.mime,
            "primary_uri": self.primary_uri,
            "alt_uris": json.dumps(self.alt_uris),
            "provider_ids": json.dumps(self.provider_ids),
            "fingerprint": self.fingerprint,
            "availability": self.availability,
            "metadata": json.dumps(self.metadata),
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Resource:
        return cls(
            resource_id=row["resource_id"],
            type=row["type"],
            canonical_id=row["canonical_id"] or "",
            title=row["title"] or "",
            creator=row["creator"] or "",
            mime=row["mime"] or "",
            primary_uri=row["primary_uri"] or "",
            alt_uris=_loads_list(row.get("alt_uris")),
            provider_ids=_loads_dict(row.get("provider_ids")),
            fingerprint=row.get("fingerprint") or "",
            availability=row.get("availability") or HEALTH_AVAILABLE,
            metadata=_loads_dict(row.get("metadata")),
            created=row["created"],
            updated=row["updated"],
        )


@dataclass
class Location:
    """A place within a Resource -- the Universal Location Descriptor (PRD 10).

    The six locator layers are stored as JSON blobs so the descriptor can carry
    every strategy at once and the resolver (``uld.py``) can fall through them
    in order. ``confidence`` is 0..1; ``display_summary`` is the human string
    shown in results and announced by screen readers.
    """

    location_id: str = field(default_factory=lambda: _new_id("loc"))
    resource_id: str = ""
    type: str = "native"  # native, structural, textQuote, positional, media
    native_locator: dict[str, Any] = field(default_factory=dict)
    structural_locator: dict[str, Any] = field(default_factory=dict)
    text_quote: dict[str, Any] = field(default_factory=dict)
    positional_locator: dict[str, Any] = field(default_factory=dict)
    recovery_hints: dict[str, Any] = field(default_factory=dict)
    media_start_ms: int | None = None
    media_end_ms: int | None = None
    heading_path: list[str] = field(default_factory=list)
    display_summary: str = ""
    confidence: float = 1.0
    last_resolved: int | None = None
    resolution_history: list[dict[str, Any]] = field(default_factory=list)

    def to_row(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "resource_id": self.resource_id,
            "type": self.type,
            "native_locator": json.dumps(self.native_locator),
            "structural_locator": json.dumps(self.structural_locator),
            "text_quote": json.dumps(self.text_quote),
            "positional_locator": json.dumps(self.positional_locator),
            "recovery_hints": json.dumps(self.recovery_hints),
            "media_start_ms": self.media_start_ms,
            "media_end_ms": self.media_end_ms,
            "heading_path": json.dumps(self.heading_path),
            "display_summary": self.display_summary,
            "confidence": self.confidence,
            "last_resolved": self.last_resolved,
            "resolution_history": json.dumps(self.resolution_history),
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Location:
        return cls(
            location_id=row["location_id"],
            resource_id=row["resource_id"],
            type=row["type"],
            native_locator=_loads_dict(row.get("native_locator")),
            structural_locator=_loads_dict(row.get("structural_locator")),
            text_quote=_loads_dict(row.get("text_quote")),
            positional_locator=_loads_dict(row.get("positional_locator")),
            recovery_hints=_loads_dict(row.get("recovery_hints")),
            media_start_ms=row.get("media_start_ms"),
            media_end_ms=row.get("media_end_ms"),
            heading_path=_loads_list(row.get("heading_path")),
            display_summary=row.get("display_summary") or "",
            confidence=row.get("confidence") or 1.0,
            last_resolved=row.get("last_resolved"),
            resolution_history=_loads_list(row.get("resolution_history")),
        )


@dataclass
class Beacon:
    """The user's saved relationship with a Resource (PRD 24.1)."""

    beacon_id: str = field(default_factory=lambda: _new_id("bcn"))
    resource_id: str = ""
    title: str = ""
    note: str = ""
    favorite: bool = False
    in_inbox: bool = True
    archived: bool = False
    trashed: bool = False
    date_added: int = field(default_factory=_now_ms)
    last_opened: int | None = None
    open_count: int = 0
    privacy: str = "private"
    health: str = HEALTH_AVAILABLE
    capture_source: str = "manual"
    version: int = 1
    updated: int = field(default_factory=_now_ms)
    dirty: int = 0
    # Joined fields populated by the loader, not stored on the beacon row:
    tags: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    locations: list[Location] = field(default_factory=list)

    def to_row(self) -> dict[str, Any]:
        return {
            "beacon_id": self.beacon_id,
            "resource_id": self.resource_id,
            "title": self.title,
            "note": self.note,
            "favorite": 1 if self.favorite else 0,
            "in_inbox": 1 if self.in_inbox else 0,
            "archived": 1 if self.archived else 0,
            "trashed": 1 if self.trashed else 0,
            "date_added": self.date_added,
            "last_opened": self.last_opened,
            "open_count": self.open_count,
            "privacy": self.privacy,
            "health": self.health,
            "capture_source": self.capture_source,
            "version": self.version,
            "updated": self.updated,
            "dirty": self.dirty,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Beacon:
        return cls(
            beacon_id=row["beacon_id"],
            resource_id=row["resource_id"],
            title=row["title"] or "",
            note=row["note"] or "",
            favorite=bool(row["favorite"]),
            in_inbox=bool(row["in_inbox"]),
            archived=bool(row["archived"]),
            trashed=bool(row["trashed"]),
            date_added=row["date_added"],
            last_opened=row.get("last_opened"),
            open_count=row.get("open_count") or 0,
            privacy=row.get("privacy") or "private",
            health=row.get("health") or HEALTH_AVAILABLE,
            capture_source=row.get("capture_source") or "manual",
            version=row.get("version") or 1,
            updated=row.get("updated") or 0,
            dirty=row.get("dirty") or 0,
        )

    def to_portable(self) -> dict[str, Any]:
        """Portable JSON archive record (PRD 24.2)."""
        return {
            "schemaVersion": SCHEMA_VERSION,
            "beaconId": self.beacon_id,
            "title": self.title,
            "note": self.note,
            "tags": self.tags,
            "collections": self.collections,
            "favorite": self.favorite,
            "createdAt": self.date_added,
            "resource": {"resourceId": self.resource_id},
            "locations": [asdict(loc) for loc in self.locations],
        }


@dataclass
class Collection:
    collection_id: str = field(default_factory=lambda: _new_id("col"))
    name: str = ""
    description: str = ""
    parent_id: str | None = None
    manual_order: int = 0
    sharing: str = "private"
    color: str = ""

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Collection:
        return cls(
            collection_id=row["collection_id"],
            name=row["name"] or "",
            description=row.get("description") or "",
            parent_id=row.get("parent_id"),
            manual_order=row.get("manual_order") or 0,
            sharing=row.get("sharing") or "private",
            color=row.get("color") or "",
        )


@dataclass
class Tag:
    tag_id: str = field(default_factory=lambda: _new_id("tag"))
    name: str = ""
    aliases: list[str] = field(default_factory=list)
    parent_id: str | None = None

    def to_row(self) -> dict[str, Any]:
        return {
            "tag_id": self.tag_id,
            "name": self.name,
            "aliases": json.dumps(self.aliases),
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Tag:
        return cls(
            tag_id=row["tag_id"],
            name=row["name"] or "",
            aliases=_loads_list(row.get("aliases")),
            parent_id=row.get("parent_id"),
        )


@dataclass
class Trail:
    trail_id: str = field(default_factory=lambda: _new_id("trl"))
    title: str = ""
    description: str = ""
    current_step: int = 0
    sharing: str = "private"
    steps: list[dict[str, Any]] = field(default_factory=list)
    # each step: {beacon_id, note, completed}

    def to_row(self) -> dict[str, Any]:
        return {
            "trail_id": self.trail_id,
            "title": self.title,
            "description": self.description,
            "current_step": self.current_step,
            "sharing": self.sharing,
            "steps": json.dumps(self.steps),
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Trail:
        return cls(
            trail_id=row["trail_id"],
            title=row["title"] or "",
            description=row.get("description") or "",
            current_step=row.get("current_step") or 0,
            sharing=row.get("sharing") or "private",
            steps=_loads_list(row.get("steps")),
        )


@dataclass
class Relationship:
    src_beacon: str = ""
    tgt_beacon: str = ""
    type: str = "relatedTo"
    note: str = ""
    created: int = field(default_factory=_now_ms)


@dataclass
class MediaChapter:
    chapter_id: str = field(default_factory=lambda: _new_id("chap"))
    resource_id: str = ""
    source_type: str = "publisher"  # publisher|provider|suggested|personal|shared
    title: str = ""
    start_ms: int = 0
    end_ms: int | None = None
    url: str = ""
    image_ref: str = ""
    publisher_id: str = ""
    user_edit: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "resource_id": self.resource_id,
            "source_type": self.source_type,
            "title": self.title,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "url": self.url,
            "image_ref": self.image_ref,
            "publisher_id": self.publisher_id,
            "user_edit": json.dumps(self.user_edit),
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> MediaChapter:
        return cls(
            chapter_id=row["chapter_id"],
            resource_id=row["resource_id"],
            source_type=row.get("source_type") or "publisher",
            title=row.get("title") or "",
            start_ms=row.get("start_ms") or 0,
            end_ms=row.get("end_ms"),
            url=row.get("url") or "",
            image_ref=row.get("image_ref") or "",
            publisher_id=row.get("publisher_id") or "",
            user_edit=_loads_dict(row.get("user_edit")),
        )


@dataclass
class SavedSearch:
    """A persisted structured search, surfaced as a Smart Collection (PRD 15.6).

    ``query`` is the Section-15 grammar string; ``sort`` and ``scope_collection``
    pin the view. The saved search evaluates live against the store, so a Smart
    Collection always reflects the current library, never a frozen snapshot.
    """

    search_id: str = field(default_factory=lambda: _new_id("ss"))
    name: str = ""
    query: str = ""
    sort: str = "added"
    scope_collection: str = ""
    created: int = field(default_factory=_now_ms)

    def to_row(self) -> dict[str, Any]:
        return {
            "search_id": self.search_id,
            "name": self.name,
            "query": self.query,
            "sort": self.sort,
            "scope_collection": self.scope_collection,
            "created": self.created,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> SavedSearch:
        return cls(
            search_id=row["search_id"],
            name=row.get("name") or "",
            query=row.get("query") or "",
            sort=row.get("sort") or "added",
            scope_collection=row.get("scope_collection") or "",
            created=row.get("created") or _now_ms(),
        )


@dataclass
class Attachment:
    """A file or reference attached to a Beacon (PRD 24.1, 44.3).

    An attachment is anything the user pinned to a saved item that is not the
    resource itself: a screenshot, a PDF, an audio memo, a related file on
    disk, or a note-style blob. ``kind`` is ``file`` (on disk), ``url``
    (remote), or ``note`` (inline text in ``content``). Stored locally; never
    synced as a blob (only its manifest, like Quill Cast pipeline outputs).
    """

    attachment_id: str = field(default_factory=lambda: _new_id("att"))
    beacon_id: str = ""
    name: str = ""
    kind: str = "file"  # file | url | note
    uri: str = ""  # filesystem path for file, URL for url
    content: str = ""  # inline text for note
    mime: str = ""
    size: int = 0
    fingerprint: str = ""
    created: int = field(default_factory=_now_ms)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        return {
            "attachment_id": self.attachment_id,
            "beacon_id": self.beacon_id,
            "name": self.name,
            "kind": self.kind,
            "uri": self.uri,
            "content": self.content,
            "mime": self.mime,
            "size": self.size,
            "fingerprint": self.fingerprint,
            "created": self.created,
            "metadata": json.dumps(self.metadata),
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Attachment:
        return cls(
            attachment_id=row["attachment_id"],
            beacon_id=row.get("beacon_id") or "",
            name=row.get("name") or "",
            kind=row.get("kind") or "file",
            uri=row.get("uri") or "",
            content=row.get("content") or "",
            mime=row.get("mime") or "",
            size=row.get("size") or 0,
            fingerprint=row.get("fingerprint") or "",
            created=row.get("created") or _now_ms(),
            metadata=_loads_dict(row.get("metadata")),
        )


def _loads_list(raw: Any) -> list[Any]:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _loads_dict(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}
