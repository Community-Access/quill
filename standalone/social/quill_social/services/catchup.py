"""Catch-Up Mode grouping (PRD 12.6).

Pure functions that turn a flat, cross-account item list into the catch-up
digests the PRD calls for: unread totals, people-first grouping, conversation
grouping, repost collapse, and cross-network duplicate collapse. Every grouping
keeps the original items so an AI summary (a later phase) can always lead back
to the source (PRD 12.6, "AI summaries must always lead back to original
items").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill_social.model import SocialItem


@dataclass
class Group:
    key: str
    label: str
    items: list[SocialItem] = field(default_factory=list)

    @property
    def unread(self) -> int:
        return sum(1 for it in self.items if not it.read)


@dataclass
class CatchUp:
    total: int = 0
    unread: int = 0
    groups: list[Group] = field(default_factory=list)

    def group_for(self, key: str) -> Group | None:
        for g in self.groups:
            if g.key == key:
                return g
        return None


def unread_total(items: list[SocialItem]) -> int:
    return sum(1 for it in items if not it.read)


def collapse_reposts(items: list[SocialItem]) -> list[SocialItem]:
    """Drop a boost when the original post is already present (PRD 12.6)."""
    present = {it.remote_id for it in items if not it.is_repost}
    out: list[SocialItem] = []
    seen_boosts: set[str] = set()
    for it in items:
        if it.is_repost:
            if it.reblog_of in present or it.reblog_of in seen_boosts:
                continue
            seen_boosts.add(it.reblog_of)
        out.append(it)
    return out


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def collapse_cross_network(items: list[SocialItem]) -> list[SocialItem]:
    """Collapse the same content cross-posted to two networks (PRD 12.6).

    Two items collapse when the same author name posts identical normalized text
    on different networks. The earliest-created copy is kept.
    """
    by_sig: dict[tuple[str, str], SocialItem] = {}
    order: list[tuple[str, str]] = []
    for it in sorted(items, key=lambda x: x.created_at):
        sig = (it.author_display.lower().strip(), _norm_text(it.text))
        if not sig[1]:
            # keep empty-text items (media-only) individually
            uniq = (f"__uniq_{it.item_id}", "")
            by_sig[uniq] = it
            order.append(uniq)
            continue
        if sig not in by_sig:
            by_sig[sig] = it
            order.append(sig)
    return [by_sig[s] for s in order]


def group_by_person(items: list[SocialItem]) -> CatchUp:
    """People-first grouping: one group per author, unread-heavy first."""
    cu = CatchUp(total=len(items), unread=unread_total(items))
    groups: dict[str, Group] = {}
    for it in items:
        key = it.author_id or it.author_handle
        g = groups.get(key)
        if g is None:
            g = Group(key=key, label=it.author_display or it.author_handle)
            groups[key] = g
        g.items.append(it)
    cu.groups = sorted(
        groups.values(), key=lambda g: (-g.unread, -len(g.items), g.label.lower())
    )
    return cu


def group_by_conversation(items: list[SocialItem]) -> CatchUp:
    """Conversation grouping: one group per thread root (PRD 12.6)."""
    cu = CatchUp(total=len(items), unread=unread_total(items))
    groups: dict[str, Group] = {}
    for it in items:
        key = it.thread_root or it.remote_id or it.item_id
        g = groups.get(key)
        if g is None:
            g = Group(key=key, label=f"Conversation ({it.author_display})")
            groups[key] = g
        g.items.append(it)
    for g in groups.values():
        g.items.sort(key=lambda x: x.created_at)
    cu.groups = sorted(groups.values(), key=lambda g: (-g.unread, -len(g.items)))
    return cu


def media_only(items: list[SocialItem]) -> list[SocialItem]:
    """The media-only review pass (PRD 12.6)."""
    return [it for it in items if it.media]
