"""Core domain entities for QUILL Social (PRD section 30).

Pure dataclasses with ``to_row``/``from_row`` helpers. Nested structures
(media lists, poll options, per-network variants, smart-folder rules) are
stored as JSON text in single columns so the SQLite schema stays flat and the
model stays easy to test. This module is wx-free and has no I/O; it is the
shared contract between the persistence layer, the adapters, the services, and
the UI.

Design notes:
- Timestamps are integer milliseconds since the Unix epoch (UTC), matching
  ``quill_beacon.model``. Helpers live here so every layer agrees.
- Identity is durable: Mastodon accounts carry an instance domain, Bluesky
  accounts carry a DID (PRD 11.3). A ``SocialItem`` keeps the network's own
  remote id so local records survive handle changes.
- Nothing here decides *capability*; that lives in ``capabilities.py``. The
  model only records data.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

# -- shared helpers -----------------------------------------------------------

# The networks the P0 slice understands. "mock" is a fully local, deterministic
# network used so the whole app runs and is testable without credentials.
NETWORKS = ("mastodon", "bluesky", "github", "rss", "mock")

# Post visibility, normalized across networks (PRD 6.2, 15.1). Adapters map
# these onto each network's own vocabulary.
VISIBILITIES = ("public", "unlisted", "followers", "direct")

# Delivery / scheduling states (PRD 18.8). A superset that both the local and
# native schedulers move through; not every state applies to every tier.
PLAN_STATES = (
    "idea",
    "draft",
    "ready",
    "changes_requested",
    "approved",
    "queued",
    "scheduled",
    "publishing",
    "partial",
    "published",
    "failed",
    "paused",
    "cancelled",
    "archived",
)


def now_ms() -> int:
    """Current time in integer milliseconds since the Unix epoch (UTC)."""
    return int(time.time() * 1000)


def new_id(prefix: str) -> str:
    """A short, sortable-enough unique id with a type prefix, e.g. ``acct_1a2b``."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _loads(text: str, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return default


# -- media --------------------------------------------------------------------


@dataclass
class Media:
    """A media attachment on a post or draft (PRD 19.4)."""

    media_id: str = field(default_factory=lambda: new_id("media"))
    kind: str = "image"  # image | video | audio | gifv | unknown
    uri: str = ""
    local_path: str = ""
    mime: str = ""
    alt_text: str = ""
    caption: str = ""
    transcript: str = ""
    duration_ms: int = 0
    sensitive: bool = False

    def to_dict(self) -> dict:
        return {
            "media_id": self.media_id,
            "kind": self.kind,
            "uri": self.uri,
            "local_path": self.local_path,
            "mime": self.mime,
            "alt_text": self.alt_text,
            "caption": self.caption,
            "transcript": self.transcript,
            "duration_ms": self.duration_ms,
            "sensitive": self.sensitive,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Media:
        return cls(
            media_id=d.get("media_id") or new_id("media"),
            kind=d.get("kind", "image"),
            uri=d.get("uri", ""),
            local_path=d.get("local_path", ""),
            mime=d.get("mime", ""),
            alt_text=d.get("alt_text", ""),
            caption=d.get("caption", ""),
            transcript=d.get("transcript", ""),
            duration_ms=int(d.get("duration_ms", 0) or 0),
            sensitive=bool(d.get("sensitive", False)),
        )

    @property
    def has_alt(self) -> bool:
        return bool(self.alt_text.strip())


@dataclass
class PollOption:
    title: str = ""
    votes: int = 0


@dataclass
class Poll:
    """A native poll on a post (PRD 17)."""

    options: list[PollOption] = field(default_factory=list)
    multiple: bool = False
    expires_at: int | None = None
    voted: bool = False
    own_votes: list[int] = field(default_factory=list)
    total_votes: int = 0

    def to_dict(self) -> dict:
        return {
            "options": [{"title": o.title, "votes": o.votes} for o in self.options],
            "multiple": self.multiple,
            "expires_at": self.expires_at,
            "voted": self.voted,
            "own_votes": self.own_votes,
            "total_votes": self.total_votes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Poll:
        return cls(
            options=[PollOption(o.get("title", ""), int(o.get("votes", 0) or 0))
                     for o in d.get("options", [])],
            multiple=bool(d.get("multiple", False)),
            expires_at=d.get("expires_at"),
            voted=bool(d.get("voted", False)),
            own_votes=list(d.get("own_votes", [])),
            total_votes=int(d.get("total_votes", 0) or 0),
        )


# -- account ------------------------------------------------------------------


@dataclass
class Account:
    """A connected social identity (PRD 11).

    ``instance`` carries the Mastodon server domain; ``did`` carries the Bluesky
    durable identifier. ``local_alias`` is a user-chosen rename that never
    leaves the device. ``paused`` accounts stay configured but are skipped by
    refresh and hidden from the default posting picker.
    """

    account_id: str = field(default_factory=lambda: new_id("acct"))
    network: str = "mock"
    handle: str = ""
    display_name: str = ""
    instance: str = ""
    did: str = ""
    local_alias: str = ""
    workspace_id: str = ""
    is_default: bool = False
    paused: bool = False
    color: str = ""
    signature: str = ""
    created: int = field(default_factory=now_ms)

    @property
    def full_handle(self) -> str:
        """A stable, human display of the identity including the network home."""
        if self.network == "mastodon" and self.instance:
            base = self.handle.lstrip("@")
            return f"@{base}@{self.instance}" if "@" not in base else f"@{base}"
        if self.network == "bluesky":
            return self.handle if self.handle.startswith("@") else f"@{self.handle}"
        return self.handle or self.account_id

    @property
    def label(self) -> str:
        """What the UI shows: the alias if set, else display name, else handle."""
        return self.local_alias or self.display_name or self.full_handle

    def to_row(self) -> dict:
        return {
            "account_id": self.account_id,
            "network": self.network,
            "handle": self.handle,
            "display_name": self.display_name,
            "instance": self.instance,
            "did": self.did,
            "local_alias": self.local_alias,
            "workspace_id": self.workspace_id,
            "is_default": int(self.is_default),
            "paused": int(self.paused),
            "color": self.color,
            "signature": self.signature,
            "created": self.created,
        }

    @classmethod
    def from_row(cls, r: dict) -> Account:
        return cls(
            account_id=r["account_id"],
            network=r["network"],
            handle=r["handle"],
            display_name=r["display_name"],
            instance=r["instance"],
            did=r["did"],
            local_alias=r["local_alias"],
            workspace_id=r["workspace_id"],
            is_default=bool(r["is_default"]),
            paused=bool(r["paused"]),
            color=r["color"],
            signature=r["signature"],
            created=r["created"],
        )


@dataclass
class Workspace:
    """A named grouping of accounts, folders, and schedules (PRD 9.1)."""

    workspace_id: str = field(default_factory=lambda: new_id("ws"))
    name: str = ""
    position: int = 0
    created: int = field(default_factory=now_ms)

    def to_row(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "position": self.position,
            "created": self.created,
        }

    @classmethod
    def from_row(cls, r: dict) -> Workspace:
        return cls(
            workspace_id=r["workspace_id"],
            name=r["name"],
            position=r["position"],
            created=r["created"],
        )


# -- social item (post) -------------------------------------------------------


@dataclass
class SocialItem:
    """A single post, reply, quote, or repost from any network (PRD 12, 14).

    Keeps the network's own ``remote_id`` so the local record survives handle
    changes and re-fetches. Local-only state (read, folders, tags, flagged)
    lives alongside the network state so a row can be rendered without a join.
    """

    item_id: str = field(default_factory=lambda: new_id("item"))
    network: str = "mock"
    account_id: str = ""
    remote_id: str = ""
    uri: str = ""
    author_handle: str = ""
    author_display: str = ""
    author_id: str = ""
    text: str = ""
    lang: str = ""
    created_at: int = field(default_factory=now_ms)
    visibility: str = "public"
    content_warning: str = ""
    sensitive: bool = False
    in_reply_to: str = ""
    thread_root: str = ""
    quote_of: str = ""
    reblog_of: str = ""
    reblog_by: str = ""  # handle that boosted, when this row represents a boost
    thread_level: int = 0
    reply_count: int = 0
    reblog_count: int = 0
    favourite_count: int = 0
    favourited: bool = False
    bookmarked: bool = False
    reblogged: bool = False
    moderation_labels: list[str] = field(default_factory=list)
    media: list[Media] = field(default_factory=list)
    poll: Poll | None = None
    # local-only
    read: bool = False
    flagged: bool = False
    folders: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    fetched_at: int = field(default_factory=now_ms)

    @property
    def is_reply(self) -> bool:
        return bool(self.in_reply_to)

    @property
    def is_repost(self) -> bool:
        return bool(self.reblog_of)

    @property
    def is_quote(self) -> bool:
        return bool(self.quote_of)

    @property
    def missing_alt_count(self) -> int:
        return sum(1 for m in self.media if not m.has_alt)

    def to_row(self) -> dict:
        return {
            "item_id": self.item_id,
            "network": self.network,
            "account_id": self.account_id,
            "remote_id": self.remote_id,
            "uri": self.uri,
            "author_handle": self.author_handle,
            "author_display": self.author_display,
            "author_id": self.author_id,
            "text": self.text,
            "lang": self.lang,
            "created_at": self.created_at,
            "visibility": self.visibility,
            "content_warning": self.content_warning,
            "sensitive": int(self.sensitive),
            "in_reply_to": self.in_reply_to,
            "thread_root": self.thread_root,
            "quote_of": self.quote_of,
            "reblog_of": self.reblog_of,
            "reblog_by": self.reblog_by,
            "thread_level": self.thread_level,
            "reply_count": self.reply_count,
            "reblog_count": self.reblog_count,
            "favourite_count": self.favourite_count,
            "favourited": int(self.favourited),
            "bookmarked": int(self.bookmarked),
            "reblogged": int(self.reblogged),
            "moderation_labels": _dumps(self.moderation_labels),
            "media": _dumps([m.to_dict() for m in self.media]),
            "poll": _dumps(self.poll.to_dict()) if self.poll else "",
            "read": int(self.read),
            "flagged": int(self.flagged),
            "folders": _dumps(self.folders),
            "tags": _dumps(self.tags),
            "fetched_at": self.fetched_at,
        }

    @classmethod
    def from_row(cls, r: dict) -> SocialItem:
        poll_text = r["poll"]
        return cls(
            item_id=r["item_id"],
            network=r["network"],
            account_id=r["account_id"],
            remote_id=r["remote_id"],
            uri=r["uri"],
            author_handle=r["author_handle"],
            author_display=r["author_display"],
            author_id=r["author_id"],
            text=r["text"],
            lang=r["lang"],
            created_at=r["created_at"],
            visibility=r["visibility"],
            content_warning=r["content_warning"],
            sensitive=bool(r["sensitive"]),
            in_reply_to=r["in_reply_to"],
            thread_root=r["thread_root"],
            quote_of=r["quote_of"],
            reblog_of=r["reblog_of"],
            reblog_by=r["reblog_by"],
            thread_level=r["thread_level"],
            reply_count=r["reply_count"],
            reblog_count=r["reblog_count"],
            favourite_count=r["favourite_count"],
            favourited=bool(r["favourited"]),
            bookmarked=bool(r["bookmarked"]),
            reblogged=bool(r["reblogged"]),
            moderation_labels=_loads(r["moderation_labels"], []),
            media=[Media.from_dict(m) for m in _loads(r["media"], [])],
            poll=Poll.from_dict(_loads(poll_text, {})) if poll_text else None,
            read=bool(r["read"]),
            flagged=bool(r["flagged"]),
            folders=_loads(r["folders"], []),
            tags=_loads(r["tags"], []),
            fetched_at=r["fetched_at"],
        )


# -- drafts -------------------------------------------------------------------


@dataclass
class Draft:
    """A composed post before it is published or scheduled (PRD 15, 16).

    ``targets`` is the list of account ids this draft will publish from.
    ``variants`` maps a network name to override text for cross-network
    composition (PRD 15.6). ``thread_mode`` marks a draft that should be split
    and published as an ordered thread.
    """

    draft_id: str = field(default_factory=lambda: new_id("draft"))
    text: str = ""
    targets: list[str] = field(default_factory=list)
    visibility: str = "public"
    content_warning: str = ""
    lang: str = ""
    in_reply_to: str = ""
    quote_of: str = ""
    thread_mode: bool = False
    media: list[Media] = field(default_factory=list)
    poll: Poll | None = None
    variants: dict[str, str] = field(default_factory=dict)
    campaign_id: str = ""
    name: str = ""
    local_only: bool = False
    created: int = field(default_factory=now_ms)
    updated: int = field(default_factory=now_ms)
    version: int = 1

    def to_row(self) -> dict:
        return {
            "draft_id": self.draft_id,
            "text": self.text,
            "targets": _dumps(self.targets),
            "visibility": self.visibility,
            "content_warning": self.content_warning,
            "lang": self.lang,
            "in_reply_to": self.in_reply_to,
            "quote_of": self.quote_of,
            "thread_mode": int(self.thread_mode),
            "media": _dumps([m.to_dict() for m in self.media]),
            "poll": _dumps(self.poll.to_dict()) if self.poll else "",
            "variants": _dumps(self.variants),
            "campaign_id": self.campaign_id,
            "name": self.name,
            "local_only": int(self.local_only),
            "created": self.created,
            "updated": self.updated,
            "version": self.version,
        }

    @classmethod
    def from_row(cls, r: dict) -> Draft:
        poll_text = r["poll"]
        return cls(
            draft_id=r["draft_id"],
            text=r["text"],
            targets=_loads(r["targets"], []),
            visibility=r["visibility"],
            content_warning=r["content_warning"],
            lang=r["lang"],
            in_reply_to=r["in_reply_to"],
            quote_of=r["quote_of"],
            thread_mode=bool(r["thread_mode"]),
            media=[Media.from_dict(m) for m in _loads(r["media"], [])],
            poll=Poll.from_dict(_loads(poll_text, {})) if poll_text else None,
            variants=_loads(r["variants"], {}),
            campaign_id=r["campaign_id"],
            name=r["name"],
            local_only=bool(r["local_only"]),
            created=r["created"],
            updated=r["updated"],
            version=r["version"],
        )


# -- folders (manual + smart) -------------------------------------------------


@dataclass
class Folder:
    """A manual or smart folder in the Social Library (PRD 13).

    Smart folders carry a ``rule`` dict evaluated by ``services.smartfolder``;
    manual folders carry an explicit member set stored separately.
    """

    folder_id: str = field(default_factory=lambda: new_id("folder"))
    name: str = ""
    parent_id: str = ""
    kind: str = "manual"  # manual | smart
    rule: dict = field(default_factory=dict)
    position: int = 0
    created: int = field(default_factory=now_ms)

    def to_row(self) -> dict:
        return {
            "folder_id": self.folder_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "kind": self.kind,
            "rule": _dumps(self.rule),
            "position": self.position,
            "created": self.created,
        }

    @classmethod
    def from_row(cls, r: dict) -> Folder:
        return cls(
            folder_id=r["folder_id"],
            name=r["name"],
            parent_id=r["parent_id"],
            kind=r["kind"],
            rule=_loads(r["rule"], {}),
            position=r["position"],
            created=r["created"],
        )


# -- private notes ------------------------------------------------------------


@dataclass
class Note:
    """A private, local-only note attached to a person, post, or feed (PRD 13.4).

    Private notes must never be posted and must be excluded from AI unless
    explicitly selected; this model records the ``confidential`` flag the higher
    layers enforce.
    """

    note_id: str = field(default_factory=lambda: new_id("note"))
    target_type: str = "profile"  # profile | post | thread | feed | github | campaign
    target_id: str = ""
    text: str = ""
    alias: str = ""
    follow_up_at: int | None = None
    tags: list[str] = field(default_factory=list)
    confidential: bool = False
    created: int = field(default_factory=now_ms)
    updated: int = field(default_factory=now_ms)

    def to_row(self) -> dict:
        return {
            "note_id": self.note_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "text": self.text,
            "alias": self.alias,
            "follow_up_at": self.follow_up_at,
            "tags": _dumps(self.tags),
            "confidential": int(self.confidential),
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_row(cls, r: dict) -> Note:
        return cls(
            note_id=r["note_id"],
            target_type=r["target_type"],
            target_id=r["target_id"],
            text=r["text"],
            alias=r["alias"],
            follow_up_at=r["follow_up_at"],
            tags=_loads(r["tags"], []),
            confidential=bool(r["confidential"]),
            created=r["created"],
            updated=r["updated"],
        )


# -- campaigns ----------------------------------------------------------------


@dataclass
class Campaign:
    """A named publishing campaign (PRD 18.6)."""

    campaign_id: str = field(default_factory=lambda: new_id("camp"))
    name: str = ""
    description: str = ""
    start_at: int | None = None
    end_at: int | None = None
    account_ids: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    created: int = field(default_factory=now_ms)

    def to_row(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "description": self.description,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "account_ids": _dumps(self.account_ids),
            "hashtags": _dumps(self.hashtags),
            "created": self.created,
        }

    @classmethod
    def from_row(cls, r: dict) -> Campaign:
        return cls(
            campaign_id=r["campaign_id"],
            name=r["name"],
            description=r["description"],
            start_at=r["start_at"],
            end_at=r["end_at"],
            account_ids=_loads(r["account_ids"], []),
            hashtags=_loads(r["hashtags"], []),
            created=r["created"],
        )


# -- publication plans + delivery attempts ------------------------------------


@dataclass
class DeliveryAttempt:
    """One attempt to publish a plan to a network (PRD 18.12)."""

    attempted_at: int = field(default_factory=now_ms)
    ok: bool = False
    published_id: str = ""
    error_kind: str = ""  # transient | validation | permission | privacy | unknown
    error_message: str = ""

    def to_dict(self) -> dict:
        return {
            "attempted_at": self.attempted_at,
            "ok": self.ok,
            "published_id": self.published_id,
            "error_kind": self.error_kind,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DeliveryAttempt:
        return cls(
            attempted_at=int(d.get("attempted_at", 0) or 0),
            ok=bool(d.get("ok", False)),
            published_id=d.get("published_id", ""),
            error_kind=d.get("error_kind", ""),
            error_message=d.get("error_message", ""),
        )


@dataclass
class PublicationPlan:
    """A single account's scheduled/queued delivery of a draft (PRD 18.8).

    A cross-network draft produces one plan per target account, so a failure on
    one destination never blocks or duplicates the others (PRD 39.3).
    """

    plan_id: str = field(default_factory=lambda: new_id("plan"))
    draft_id: str = ""
    account_id: str = ""
    network: str = "mock"
    tier: str = "local"  # native | local | cloud
    scheduled_for: int | None = None
    state: str = "queued"
    remote_id: str = ""
    campaign_id: str = ""
    attempts: list[DeliveryAttempt] = field(default_factory=list)
    next_retry_at: int | None = None
    created: int = field(default_factory=now_ms)
    updated: int = field(default_factory=now_ms)

    @property
    def retry_count(self) -> int:
        return sum(1 for a in self.attempts if not a.ok)

    def to_row(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "draft_id": self.draft_id,
            "account_id": self.account_id,
            "network": self.network,
            "tier": self.tier,
            "scheduled_for": self.scheduled_for,
            "state": self.state,
            "remote_id": self.remote_id,
            "campaign_id": self.campaign_id,
            "attempts": _dumps([a.to_dict() for a in self.attempts]),
            "next_retry_at": self.next_retry_at,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_row(cls, r: dict) -> PublicationPlan:
        return cls(
            plan_id=r["plan_id"],
            draft_id=r["draft_id"],
            account_id=r["account_id"],
            network=r["network"],
            tier=r["tier"],
            scheduled_for=r["scheduled_for"],
            state=r["state"],
            remote_id=r["remote_id"],
            campaign_id=r["campaign_id"],
            attempts=[DeliveryAttempt.from_dict(a) for a in _loads(r["attempts"], [])],
            next_retry_at=r["next_retry_at"],
            created=r["created"],
            updated=r["updated"],
        )


# -- saved searches + reading positions ---------------------------------------


@dataclass
class SavedSearch:
    """A saved query that can become a feed, folder, or digest (PRD 26.3)."""

    search_id: str = field(default_factory=lambda: new_id("search"))
    name: str = ""
    query: str = ""
    scope: str = "local"  # local | network | cross
    created: int = field(default_factory=now_ms)

    def to_row(self) -> dict:
        return {
            "search_id": self.search_id,
            "name": self.name,
            "query": self.query,
            "scope": self.scope,
            "created": self.created,
        }

    @classmethod
    def from_row(cls, r: dict) -> SavedSearch:
        return cls(
            search_id=r["search_id"],
            name=r["name"],
            query=r["query"],
            scope=r["scope"],
            created=r["created"],
        )


@dataclass
class ReadingPosition:
    """The last-read item for one account + feed (PRD 12.5)."""

    account_id: str = ""
    feed: str = ""
    item_id: str = ""
    updated: int = field(default_factory=now_ms)

    def to_row(self) -> dict:
        return {
            "account_id": self.account_id,
            "feed": self.feed,
            "item_id": self.item_id,
            "updated": self.updated,
        }

    @classmethod
    def from_row(cls, r: dict) -> ReadingPosition:
        return cls(
            account_id=r["account_id"],
            feed=r["feed"],
            item_id=r["item_id"],
            updated=r["updated"],
        )
