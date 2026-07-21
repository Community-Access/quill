"""Notifications and attention management (PRD 25).

Pure, wx-free routing for notifications. Given a per-account, per-category
``NotificationPolicy`` and a ``NotificationItem``, ``classify`` returns exactly
how the item should reach the user -- spoken, brailled, sounded, shown on the
desktop, added silently, or held for a digest -- while honoring quiet hours
(PRD 25.2), "only from selected people" filtering, and focus modes (PRD 25.4).

Two aggregation helpers support attention management: ``group_duplicates``
collapses a burst of like notifications (for example many favourites of one
post) into a single counted summary, and ``build_digest`` renders an ordered,
plain-language digest string. Quiet hours are expressed as a ``(start_min,
end_min)`` minute-of-day window and ``in_quiet_hours`` handles windows that
cross midnight.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill_social.model import new_id, now_ms

# Notification categories (PRD 25.1).
CATEGORIES = (
    "mention",
    "reply",
    "quote",
    "repost",
    "favourite",
    "follow",
    "follow_request",
    "poll",
    "dm",
    "moderation",
    "scheduled_delivery",
    "delivery_failure",
    "approval_request",
    "github_assignment",
    "github_mention",
    "review_request",
    "discussion_response",
    "release",
    "media_done",
)

# Categories that are always safety- or delivery-critical: never silenced by
# quiet hours or focus modes, matching the PRD's rule that sound is never the
# sole indicator of failure or danger (PRD 25.3, 25.4).
CRITICAL_CATEGORIES = frozenset({"delivery_failure", "moderation"})

_MS_PER_MINUTE = 60_000
_MINUTES_PER_DAY = 1440

_SUMMARY_VERBS = {
    "favourite": "favourited your post",
    "repost": "reposted your post",
    "reply": "replied to your post",
    "follow": "followed you",
    "quote": "quoted your post",
    "mention": "mentioned you",
}


@dataclass
class NotificationItem:
    """A single inbound notification (PRD 25.1)."""

    notif_id: str = field(default_factory=lambda: new_id("notif"))
    category: str = "mention"
    account_id: str = ""
    network: str = "mock"
    actor_handle: str = ""
    actor_display: str = ""
    subject_id: str = ""  # the post/thread/PR the notification is about
    text: str = ""
    created: int = field(default_factory=now_ms)
    count: int = 1  # >1 once grouped
    actors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "notif_id": self.notif_id,
            "category": self.category,
            "account_id": self.account_id,
            "network": self.network,
            "actor_handle": self.actor_handle,
            "actor_display": self.actor_display,
            "subject_id": self.subject_id,
            "text": self.text,
            "created": self.created,
            "count": self.count,
            "actors": list(self.actors),
        }

    @classmethod
    def from_dict(cls, d: dict) -> NotificationItem:
        return cls(
            notif_id=d.get("notif_id") or new_id("notif"),
            category=d.get("category", "mention"),
            account_id=d.get("account_id", ""),
            network=d.get("network", "mock"),
            actor_handle=d.get("actor_handle", ""),
            actor_display=d.get("actor_display", ""),
            subject_id=d.get("subject_id", ""),
            text=d.get("text", ""),
            created=int(d.get("created", 0) or 0),
            count=int(d.get("count", 1) or 1),
            actors=list(d.get("actors", [])),
        )


@dataclass
class NotificationPolicy:
    """Per-account, per-category delivery policy (PRD 25.2)."""

    account_id: str = ""
    category: str = "mention"
    speak: bool = True
    braille: bool = True
    sound: bool = True
    desktop: bool = False
    silent: bool = False  # add silently: no speech, sound, or desktop
    digest: bool = False  # include in the digest
    suppress_during_quiet_hours: bool = True
    only_from: list[str] = field(default_factory=list)  # handles to allow
    group_duplicates: bool = True
    escalate_after_ms: int = 0  # 0 = never escalate
    route_to_folder: str = ""

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "category": self.category,
            "speak": self.speak,
            "braille": self.braille,
            "sound": self.sound,
            "desktop": self.desktop,
            "silent": self.silent,
            "digest": self.digest,
            "suppress_during_quiet_hours": self.suppress_during_quiet_hours,
            "only_from": list(self.only_from),
            "group_duplicates": self.group_duplicates,
            "escalate_after_ms": self.escalate_after_ms,
            "route_to_folder": self.route_to_folder,
        }

    @classmethod
    def from_dict(cls, d: dict) -> NotificationPolicy:
        return cls(
            account_id=d.get("account_id", ""),
            category=d.get("category", "mention"),
            speak=bool(d.get("speak", True)),
            braille=bool(d.get("braille", True)),
            sound=bool(d.get("sound", True)),
            desktop=bool(d.get("desktop", False)),
            silent=bool(d.get("silent", False)),
            digest=bool(d.get("digest", False)),
            suppress_during_quiet_hours=bool(d.get("suppress_during_quiet_hours", True)),
            only_from=list(d.get("only_from", [])),
            group_duplicates=bool(d.get("group_duplicates", True)),
            escalate_after_ms=int(d.get("escalate_after_ms", 0) or 0),
            route_to_folder=d.get("route_to_folder", ""),
        )


@dataclass
class FocusMode:
    """A focus mode: mute accounts, sounds, or speech; optional quiet window."""

    name: str = ""
    mute_accounts: list[str] = field(default_factory=list)
    mute_sounds: bool = False
    mute_speech: bool = False
    quiet_hours: tuple[int, int] | None = None
    until_ms: int | None = None  # focus expiry; None = until turned off

    def active_at(self, now: int) -> bool:
        return self.until_ms is None or now < self.until_ms


@dataclass
class NotificationDecision:
    """How a notification should be delivered (PRD 25.2)."""

    delivered: bool = True
    speak: bool = False
    braille: bool = False
    sound: bool = False
    desktop: bool = False
    add_silently: bool = False
    digest: bool = False
    folder: str = ""
    in_quiet_hours: bool = False
    escalate_after_ms: int = 0
    reason: str = ""


def in_quiet_hours(now_minute: int, window: tuple[int, int] | None) -> bool:
    """Whether ``now_minute`` (0-1439) falls inside a quiet-hours window.

    A window ``(start, end)`` where ``start > end`` crosses midnight, e.g.
    ``(1320, 420)`` means 22:00 through 07:00.
    """
    if not window:
        return False
    start, end = window
    now_minute %= _MINUTES_PER_DAY
    if start == end:
        return False
    if start < end:
        return start <= now_minute < end
    return now_minute >= start or now_minute < end


def minute_of_day(now: int) -> int:
    """Convert an epoch-millisecond time to a 0-1439 minute of day (UTC)."""
    return (now // _MS_PER_MINUTE) % _MINUTES_PER_DAY


def classify(
    policy: NotificationPolicy,
    item: NotificationItem,
    now: int | None = None,
    quiet_hours: tuple[int, int] | None = None,
    focus: FocusMode | None = None,
) -> NotificationDecision:
    """Decide how one notification reaches the user (PRD 25.2, 25.4)."""
    at = now if now is not None else now_ms()
    critical = item.category in CRITICAL_CATEGORIES

    # "Only from selected people": drop everything else outright.
    if policy.only_from:
        allowed = {h.lower().lstrip("@") for h in policy.only_from}
        if item.actor_handle.lower().lstrip("@") not in allowed:
            return NotificationDecision(delivered=False, reason="not in only_from list")

    # Focus mode muting for the whole account.
    if focus is not None and focus.active_at(at) and not critical:
        if item.account_id in focus.mute_accounts:
            return NotificationDecision(delivered=False, reason="account muted by focus")

    window = quiet_hours
    if focus is not None and focus.active_at(at) and focus.quiet_hours is not None:
        window = focus.quiet_hours
    quiet = in_quiet_hours(minute_of_day(at), window) and not critical

    decision = NotificationDecision(
        delivered=True,
        braille=policy.braille,
        in_quiet_hours=quiet,
        folder=policy.route_to_folder,
        escalate_after_ms=policy.escalate_after_ms,
    )

    if policy.silent:
        decision.add_silently = True
        decision.digest = policy.digest
        decision.reason = "added silently"
        return decision

    if quiet and policy.suppress_during_quiet_hours:
        decision.add_silently = True
        decision.digest = True  # held for the digest
        decision.reason = "held for quiet hours"
        return decision

    focus_mute_speech = bool(focus and focus.active_at(at) and focus.mute_speech) and not critical
    focus_mute_sound = bool(focus and focus.active_at(at) and focus.mute_sounds) and not critical

    decision.speak = policy.speak and not focus_mute_speech
    decision.sound = policy.sound and not focus_mute_sound
    decision.desktop = policy.desktop
    decision.digest = policy.digest
    if not (decision.speak or decision.sound or decision.desktop):
        decision.add_silently = True
    decision.reason = "critical" if critical else "delivered"
    return decision


def group_duplicates(items: list[NotificationItem]) -> list[NotificationItem]:
    """Collapse repeated notifications about one subject into a counted summary.

    Grouping key is ``(category, subject_id)``. A burst of favourites of a single
    post becomes one item whose ``count`` and ``actors`` summarize the group; the
    earliest item's position is preserved.
    """
    order: list[tuple[str, str]] = []
    groups: dict[tuple[str, str], list[NotificationItem]] = {}
    for it in items:
        key = (it.category, it.subject_id)
        if it.subject_id == "":
            key = (it.category, f"__uniq_{it.notif_id}")
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(it)

    out: list[NotificationItem] = []
    for key in order:
        members = groups[key]
        if len(members) == 1:
            out.append(members[0])
            continue
        members.sort(key=lambda x: x.created)
        first = members[0]
        actors = []
        for m in members:
            name = m.actor_display or m.actor_handle
            if name and name not in actors:
                actors.append(name)
        out.append(
            NotificationItem(
                notif_id=first.notif_id,
                category=first.category,
                account_id=first.account_id,
                network=first.network,
                actor_handle=first.actor_handle,
                actor_display=first.actor_display,
                subject_id=first.subject_id,
                text=first.text,
                created=members[-1].created,
                count=len(members),
                actors=actors,
            )
        )
    return out


def _summarize(item: NotificationItem) -> str:
    verb = _SUMMARY_VERBS.get(item.category, f"sent a {item.category.replace('_', ' ')}")
    if item.count > 1:
        actors = item.actors or [item.actor_display or item.actor_handle]
        lead = actors[0] if actors else "Someone"
        others = item.count - 1
        who = f"{lead} and {others} other{'s' if others != 1 else ''}"
        return f"{who} {verb}"
    who = item.actor_display or item.actor_handle or "Someone"
    return f"{who} {verb}"


def build_digest(
    items: list[NotificationItem], policy: NotificationPolicy | None = None
) -> str:
    """Render an ordered, plain-language digest of notifications (PRD 25.2)."""
    grouped = group_duplicates(items) if (policy is None or policy.group_duplicates) else items
    grouped = sorted(grouped, key=lambda x: x.created)
    if not grouped:
        return "No notifications."
    lines = [f"{len(grouped)} notification group(s):"]
    for it in grouped:
        lines.append(f"- {_summarize(it)}")
    return "\n".join(lines)


# -- persistence (generic document store) -------------------------------------

POLICY_KIND = "notification_policy"


def _policy_key(policy: NotificationPolicy) -> str:
    return f"{policy.account_id}:{policy.category}"


def save_policy(store, policy: NotificationPolicy) -> NotificationPolicy:
    store.put_document(POLICY_KIND, _policy_key(policy), policy.to_dict())
    return policy


def load_policies(store) -> list[NotificationPolicy]:
    return [NotificationPolicy.from_dict(d) for d in store.list_documents(POLICY_KIND)]


def get_policy(
    store, account_id: str, category: str
) -> NotificationPolicy | None:
    d = store.get_document(POLICY_KIND, f"{account_id}:{category}")
    return NotificationPolicy.from_dict(d) if d else None
