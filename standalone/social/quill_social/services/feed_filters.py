"""Per-feed keyword filters (plan xxx.md 1.5 "Per-feed keyword filters").

A subscription may carry a small list of keyword rules applied to each entry as
it arrives during a refresh. This is deliberately narrower than the Unified
Safety Center (``services.moderation``): safety filters classify *social posts*
for display (hide/warn/collapse), whereas these feed rules act on *reader*
entries at fetch time with reader-specific verbs -- drop it, pre-mark it read,
or auto-star it -- so a noisy feed self-curates without a manual pass.

The matcher is a pure, case-insensitive substring test over the entry's title
and body (which ``entry_to_item`` joins into ``SocialItem.text``). Evaluation is
first-match-wins so the rule order the user sees is the order that applies.
"""

from __future__ import annotations

from quill_social.model import SocialItem

# The reader-side verbs a per-feed rule may take, first-match-wins:
#   hide      -- do not store the entry at all (it never reaches the list)
#   mark_read -- store it already read (no unread count, no announcement)
#   star      -- store it flagged for follow-up (and protected from retention)
FEED_ACTIONS = ("hide", "mark_read", "star")


def keyword_matches(item: SocialItem, keyword: str) -> bool:
    """True if ``keyword`` (case-insensitive) appears in the entry's text."""
    kw = (keyword or "").strip().lower()
    if not kw:
        return False
    return kw in (item.text or "").lower()


def decide(item: SocialItem, filters: list[dict]) -> str:
    """Return the action of the first matching keyword rule, or ``""``.

    A rule is ``{"keyword": str, "action": one of FEED_ACTIONS}``. Rules with an
    empty keyword or an unrecognized action are skipped, so a malformed record
    can never silently swallow a whole feed.
    """
    for rule in filters:
        if not isinstance(rule, dict):
            continue
        action = rule.get("action", "")
        if action not in FEED_ACTIONS:
            continue
        if keyword_matches(item, rule.get("keyword", "")):
            return action
    return ""
