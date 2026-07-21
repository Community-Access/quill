"""Configurable row fields and field-by-field reading (PRD 12.4, 28.5).

Screen-reader users move Up/Down between items and Left/Right between the
*fields* of the focused item. This module owns the list of available fields,
the user's ordered field profile, and the pure functions that turn a
``SocialItem`` into either a compact one-line row or an ordered list of
``(label, value)`` pairs for field navigation.

It is wx-free: the UI reads these strings straight into list item text and
speech. What is spoken is data, never color or position (PRD 6.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from quill_social.a11y import A11ySettings
from quill_social.model import Account, SocialItem

# Every field a row can expose (PRD 12.4), keyed by a stable id.
AVAILABLE_FIELDS: dict[str, str] = {
    "author": "Author",
    "handle": "Handle",
    "text": "Post",
    "date": "Date",
    "network": "Network",
    "account": "Account",
    "visibility": "Visibility",
    "relation": "Reply or repost",
    "engagement": "Engagement",
    "media": "Media",
    "alt": "Alt text",
    "content_warning": "Content warning",
    "moderation": "Moderation",
    "language": "Language",
    "thread": "Thread position",
    "read": "Read state",
    "organize": "Folders and tags",
    "note": "Private note",
}

# A sensible default order (PRD 12.4 "Users can reorder and save field profiles").
DEFAULT_FIELD_ORDER: tuple[str, ...] = (
    "author",
    "text",
    "relation",
    "content_warning",
    "media",
    "alt",
    "moderation",
    "network",
    "account",
    "date",
    "engagement",
    "visibility",
    "read",
)


@dataclass
class FieldProfile:
    """An ordered, named subset of fields shown in a list (PRD 12.4)."""

    name: str = "Default"
    order: list[str] = field(default_factory=lambda: list(DEFAULT_FIELD_ORDER))

    def enabled(self) -> list[str]:
        return [f for f in self.order if f in AVAILABLE_FIELDS]


def _rel_time(created_at: int, *, now: int | None = None) -> str:
    from quill_social.model import now_ms

    now = now if now is not None else now_ms()
    delta = max(0, now - created_at) // 1000
    if delta < 60:
        return "just now"
    if delta < 3600:
        m = delta // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if delta < 86400:
        h = delta // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    if delta < 604800:
        d = delta // 86400
        return f"{d} day{'s' if d != 1 else ''} ago"
    dt = datetime.fromtimestamp(created_at / 1000, tz=UTC)
    return dt.strftime("%Y-%m-%d")


def _media_summary(item: SocialItem) -> str:
    if not item.media:
        return ""
    kinds: dict[str, int] = {}
    for m in item.media:
        kinds[m.kind] = kinds.get(m.kind, 0) + 1
    parts = [f"{n} {k}{'s' if n != 1 else ''}" for k, n in kinds.items()]
    return ", ".join(parts)


def field_value(
    item: SocialItem,
    field_id: str,
    *,
    account: Account | None = None,
    settings: A11ySettings | None = None,
    now: int | None = None,
) -> str:
    """The spoken value of one field for one item. Empty string means omit."""
    s = settings or A11ySettings()
    if field_id == "author":
        return item.author_display or item.author_handle
    if field_id == "handle":
        return item.author_handle
    if field_id == "text":
        return item.text.replace("\n", " ").strip()
    if field_id == "date":
        return _rel_time(item.created_at, now=now)
    if field_id == "network":
        return item.network.capitalize()
    if field_id == "account":
        return account.label if account else item.account_id
    if field_id == "visibility":
        return item.visibility
    if field_id == "relation":
        bits = []
        if item.is_repost:
            who = item.reblog_by or "someone"
            bits.append(f"boosted by {who}")
        if item.is_reply:
            bits.append("reply")
        if item.is_quote:
            bits.append("quote")
        return ", ".join(bits)
    if field_id == "engagement":
        return (
            f"{item.reply_count} replies, {item.reblog_count} boosts, "
            f"{item.favourite_count} favourites"
        )
    if field_id == "media":
        return _media_summary(item)
    if field_id == "alt":
        if not item.media:
            return ""
        missing = item.missing_alt_count
        if missing == 0:
            return "all media described"
        return f"{missing} of {len(item.media)} missing alt text"
    if field_id == "content_warning":
        return f"content warning: {item.content_warning}" if item.content_warning else ""
    if field_id == "moderation":
        return ", ".join(item.moderation_labels)
    if field_id == "language":
        return item.lang
    if field_id == "thread":
        return f"thread level {item.thread_level}" if item.thread_level else ""
    if field_id == "read":
        if not s.announce_read_state:
            return ""
        return "read" if item.read else "unread"
    if field_id == "organize":
        bits = list(item.folders) + [f"#{t}" for t in item.tags]
        return ", ".join(bits)
    if field_id == "note":
        return ""  # populated by the UI which owns the note store
    return ""


def read_fields(
    item: SocialItem,
    profile: FieldProfile,
    *,
    account: Account | None = None,
    settings: A11ySettings | None = None,
    now: int | None = None,
) -> list[tuple[str, str]]:
    """Ordered ``(label, value)`` pairs for Left/Right field navigation.

    Empty-valued fields are dropped so the user never lands on "Media: " with
    nothing after it.
    """
    out: list[tuple[str, str]] = []
    for fid in profile.enabled():
        val = field_value(item, fid, account=account, settings=settings, now=now)
        if val:
            out.append((AVAILABLE_FIELDS[fid], val))
    return out


def render_row(
    item: SocialItem,
    profile: FieldProfile,
    *,
    account: Account | None = None,
    settings: A11ySettings | None = None,
    now: int | None = None,
) -> str:
    """A single compact string for one list row.

    Honors the a11y speech toggles: the network prefix and engagement are only
    included when the user asked for them (PRD 28.5), so the default row stays
    terse and fast to hear.
    """
    s = settings or A11ySettings()
    pieces: list[str] = []
    for fid in profile.enabled():
        if fid == "network" and not s.speak_network_prefix:
            continue
        if fid == "engagement" and not s.speak_engagement:
            continue
        val = field_value(item, fid, account=account, settings=s, now=now)
        if val:
            pieces.append(val)
    return ". ".join(pieces)
