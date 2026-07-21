"""Unified safety center: filters, mutes, blocks, and reports (PRD 27).

Pure, wx-free logic for the moderation surface the PRD calls a "Unified Safety
Center" (PRD 27.1). Three concerns live here:

- Local filters (PRD 27.2). A ``Filter`` pairs a ``criteria`` dict (text, regex,
  author, domain, network, post type, media, language, moderation label, time
  range) with a single ``action``. ``matches`` is a pure predicate and
  ``apply_filters`` turns a feed plus a filter set into one ``FilterOutcome`` per
  item, classified as surviving, warned, or hidden, naming the filter that fired.
- Mutes and blocks (PRD 27.1). ``MuteBlock`` records a muted user, blocked user,
  or blocked domain, with an optional expiry for temporary and conversation
  mutes.
- Reporting (PRD 27.3). ``Report`` captures the evidence a user chooses to send
  and, by default, excludes private notes so confidential local text never
  leaves the device.

Everything is deterministic and persists through the store's generic document
API (kinds ``filter``, ``muteblock``, ``report``), so the safety center needs no
bespoke tables.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill_social.model import SocialItem, new_id, now_ms

# The actions a local filter may take (PRD 27.2). ``digest_only`` removes an item
# from the live feed but keeps it for a later digest; the audio actions change
# how an item is announced without hiding it.
ACTIONS = (
    "hide",
    "warn",
    "collapse",
    "mute_speech",
    "suppress_sound",
    "move_to_folder",
    "replace_slurs",
    "require_reveal",
    "digest_only",
)

# How each action maps onto the three-way visibility classification. Anything not
# listed leaves the item visible and merely changes its presentation.
_HIDDEN_ACTIONS = frozenset({"hide", "digest_only"})
_WARNED_ACTIONS = frozenset({"warn", "collapse", "require_reveal"})

_URL_RE = re.compile(r"https?://([^/\s]+)", re.IGNORECASE)


@dataclass
class Filter:
    """A local content filter (PRD 27.2): match criteria plus one action."""

    filter_id: str = field(default_factory=lambda: new_id("filter"))
    name: str = ""
    criteria: dict = field(default_factory=dict)
    action: str = "hide"
    placeholder: str = "[filtered]"  # used by the replace_slurs action
    folder_id: str = ""  # used by the move_to_folder action
    enabled: bool = True
    created: int = field(default_factory=now_ms)

    def to_dict(self) -> dict:
        return {
            "filter_id": self.filter_id,
            "name": self.name,
            "criteria": dict(self.criteria),
            "action": self.action,
            "placeholder": self.placeholder,
            "folder_id": self.folder_id,
            "enabled": self.enabled,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Filter:
        return cls(
            filter_id=d.get("filter_id") or new_id("filter"),
            name=d.get("name", ""),
            criteria=dict(d.get("criteria", {})),
            action=d.get("action", "hide"),
            placeholder=d.get("placeholder", "[filtered]"),
            folder_id=d.get("folder_id", ""),
            enabled=bool(d.get("enabled", True)),
            created=int(d.get("created", 0) or 0),
        )


@dataclass
class FilterOutcome:
    """The decision for one item after evaluating a filter set."""

    item: SocialItem
    classification: str = "surviving"  # surviving | warned | hidden
    filter_id: str = ""
    action: str = ""

    @property
    def hidden(self) -> bool:
        return self.classification == "hidden"

    @property
    def warned(self) -> bool:
        return self.classification == "warned"


@dataclass
class MuteBlock:
    """A muted user, blocked user, or blocked domain (PRD 27.1)."""

    muteblock_id: str = field(default_factory=lambda: new_id("mb"))
    target: str = ""  # a handle for mute/block, a domain for domain_block
    kind: str = "mute"  # mute | block | domain_block
    scope: str = "all"  # all | timeline | notifications | conversation
    expires_at: int | None = None  # set for temporary or conversation mutes
    created: int = field(default_factory=now_ms)

    def to_dict(self) -> dict:
        return {
            "muteblock_id": self.muteblock_id,
            "target": self.target,
            "kind": self.kind,
            "scope": self.scope,
            "expires_at": self.expires_at,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MuteBlock:
        return cls(
            muteblock_id=d.get("muteblock_id") or new_id("mb"),
            target=d.get("target", ""),
            kind=d.get("kind", "mute"),
            scope=d.get("scope", "all"),
            expires_at=d.get("expires_at"),
            created=int(d.get("created", 0) or 0),
        )


@dataclass
class Report:
    """A report to a network's moderators (PRD 27.3).

    ``exclude_private_notes`` defaults to ``True`` so confidential local notes are
    never bundled into what leaves the device.
    """

    report_id: str = field(default_factory=lambda: new_id("report"))
    item_id: str = ""
    categories: list[str] = field(default_factory=list)
    comment: str = ""
    evidence_item_ids: list[str] = field(default_factory=list)
    exclude_private_notes: bool = True
    created: int = field(default_factory=now_ms)

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "item_id": self.item_id,
            "categories": list(self.categories),
            "comment": self.comment,
            "evidence_item_ids": list(self.evidence_item_ids),
            "exclude_private_notes": self.exclude_private_notes,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Report:
        return cls(
            report_id=d.get("report_id") or new_id("report"),
            item_id=d.get("item_id", ""),
            categories=list(d.get("categories", [])),
            comment=d.get("comment", ""),
            evidence_item_ids=list(d.get("evidence_item_ids", [])),
            exclude_private_notes=bool(d.get("exclude_private_notes", True)),
            created=int(d.get("created", 0) or 0),
        )

    def payload(self, private_notes: list[str] | None = None) -> dict:
        """The data that would actually be sent, honoring the exclusion flag.

        ``private_notes`` are only ever attached when the user has explicitly
        cleared ``exclude_private_notes`` (PRD 27.3, 13.4).
        """
        notes: list[str] = []
        if not self.exclude_private_notes and private_notes:
            notes = list(private_notes)
        return {
            "item_id": self.item_id,
            "categories": list(self.categories),
            "comment": self.comment,
            "evidence_item_ids": list(self.evidence_item_ids),
            "private_notes": notes,
        }


# -- matching -----------------------------------------------------------------


def _post_type(item: SocialItem) -> str:
    if item.is_repost:
        return "repost"
    if item.is_quote:
        return "quote"
    if item.is_reply:
        return "reply"
    return "post"


def _domains(item: SocialItem) -> set[str]:
    """Domains associated with an item: the author's home and any link hosts."""
    out: set[str] = set()
    handle = item.author_handle.lstrip("@")
    if "@" in handle:  # mastodon-style user@domain
        out.add(handle.rsplit("@", 1)[-1].lower())
    elif "." in handle:  # bluesky-style handle that is itself a domain
        out.add(handle.lower())
    for host in _URL_RE.findall(item.text):
        out.add(host.lower())
    return {d for d in out if d}


def _domain_matches(target: str, item: SocialItem) -> bool:
    target = target.lower().lstrip("@")
    for d in _domains(item):
        if d == target or d.endswith("." + target):
            return True
    return False


def matches(item: SocialItem, flt: Filter) -> bool:
    """Return whether ``item`` satisfies every criterion in ``flt`` (PRD 27.2).

    An empty or wholly unrecognized criteria set never matches, so a filter can
    never silently hide the entire feed.
    """
    c = flt.criteria
    evaluated = False

    if "text" in c:
        evaluated = True
        if c["text"].lower() not in item.text.lower():
            return False
    if "regex" in c:
        evaluated = True
        try:
            if not re.search(c["regex"], item.text, re.IGNORECASE):
                return False
        except re.error:
            return False
    if "author" in c:
        evaluated = True
        target = c["author"].lower().lstrip("@")
        cand = item.author_handle.lower().lstrip("@")
        if target not in cand and target != item.author_id.lower():
            return False
    if "domain" in c:
        evaluated = True
        if not _domain_matches(c["domain"], item):
            return False
    if "network" in c:
        evaluated = True
        if item.network != c["network"]:
            return False
    if "post_type" in c:
        evaluated = True
        if _post_type(item) != c["post_type"]:
            return False
    if "has_media" in c:
        evaluated = True
        if bool(item.media) != bool(c["has_media"]):
            return False
    if "language" in c:
        evaluated = True
        if item.lang.lower() != str(c["language"]).lower():
            return False
    if "moderation_label" in c:
        evaluated = True
        if c["moderation_label"] not in item.moderation_labels:
            return False
    if "since_ms" in c:
        evaluated = True
        if item.created_at < int(c["since_ms"]):
            return False
    if "until_ms" in c:
        evaluated = True
        if item.created_at > int(c["until_ms"]):
            return False

    return evaluated


def classify_action(action: str) -> str:
    """Map a filter action onto surviving | warned | hidden."""
    if action in _HIDDEN_ACTIONS:
        return "hidden"
    if action in _WARNED_ACTIONS:
        return "warned"
    return "surviving"


def apply_filters(
    items: list[SocialItem], filters: list[Filter]
) -> list[FilterOutcome]:
    """Evaluate every item against the enabled filters, in order (PRD 27.2).

    The first matching filter decides an item's outcome; items that match no
    filter survive untouched.
    """
    active = [f for f in filters if f.enabled]
    outcomes: list[FilterOutcome] = []
    for item in items:
        decision = FilterOutcome(item=item)
        for flt in active:
            if matches(item, flt):
                decision.classification = classify_action(flt.action)
                decision.filter_id = flt.filter_id
                decision.action = flt.action
                break
        outcomes.append(decision)
    return outcomes


def replace_slurs(text: str, terms: list[str], placeholder: str = "[slur]") -> str:
    """Replace each term (case-insensitive) with a spoken placeholder (PRD 27.2)."""
    result = text
    for term in terms:
        term = term.strip()
        if not term:
            continue
        result = re.sub(re.escape(term), placeholder, result, flags=re.IGNORECASE)
    return result


def safety_center_summary(
    *,
    filters: list[Filter] | None = None,
    muteblocks: list[MuteBlock] | None = None,
    reports: list[Report] | None = None,
    hidden_items: list[SocialItem] | None = None,
) -> dict[str, int]:
    """Counts by category for the Safety Center overview (PRD 27.1)."""
    mb = muteblocks or []
    return {
        "muted": sum(1 for m in mb if m.kind == "mute"),
        "blocked": sum(1 for m in mb if m.kind == "block"),
        "blocked_domains": sum(1 for m in mb if m.kind == "domain_block"),
        "filters": len(filters or []),
        "reports": len(reports or []),
        "hidden": len(hidden_items or []),
    }


# -- persistence (generic document store) -------------------------------------

FILTER_KIND = "filter"
MUTEBLOCK_KIND = "muteblock"
REPORT_KIND = "report"


def save_filter(store, flt: Filter) -> Filter:
    store.put_document(FILTER_KIND, flt.filter_id, flt.to_dict(), ordinal=flt.created)
    return flt


def load_filters(store) -> list[Filter]:
    return [Filter.from_dict(d) for d in store.list_documents(FILTER_KIND)]


def delete_filter(store, filter_id: str) -> None:
    store.delete_document(FILTER_KIND, filter_id)


def save_muteblock(store, mb: MuteBlock) -> MuteBlock:
    store.put_document(MUTEBLOCK_KIND, mb.muteblock_id, mb.to_dict(), ordinal=mb.created)
    return mb


def load_muteblocks(store) -> list[MuteBlock]:
    return [MuteBlock.from_dict(d) for d in store.list_documents(MUTEBLOCK_KIND)]


def delete_muteblock(store, muteblock_id: str) -> None:
    store.delete_document(MUTEBLOCK_KIND, muteblock_id)


def save_report(store, report: Report) -> Report:
    store.put_document(REPORT_KIND, report.report_id, report.to_dict(), ordinal=report.created)
    return report


def load_reports(store) -> list[Report]:
    return [Report.from_dict(d) for d in store.list_documents(REPORT_KIND)]


def delete_report(store, report_id: str) -> None:
    store.delete_document(REPORT_KIND, report_id)
