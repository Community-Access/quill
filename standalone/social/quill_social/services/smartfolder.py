"""Smart-folder rule evaluation (PRD 13.2).

A smart folder is a saved predicate over cached posts. Rules are plain dicts so
they serialize as JSON in the folder's ``rule`` column and can be built by an
accessible dialog. Evaluation is a pure function -- given a rule and a list of
items, return the matching items -- so a smart folder is always inspectable and
never makes content disappear for a reason the user cannot see (PRD 13.2,
"model-driven results should remain inspectable").

Supported rule keys (all optional; all must match -- logical AND):

    network:            "mastodon" | "bluesky" | ...
    account_id:         match one account
    author:             substring match on author handle/display
    has_media:          bool
    missing_alt:        bool  (has media with at least one missing alt text)
    unreplied:          bool  (reply_count == 0)
    keyword:            substring match on text (case-insensitive)
    language:           exact lang match
    moderation_label:   label present on the item
    min_engagement:     int   (replies + boosts + favourites >= n)
    since_ms / until_ms: created_at range
    unread:             bool
    bookmarked:         bool
"""

from __future__ import annotations

from quill_social.model import SocialItem


def matches(item: SocialItem, rule: dict) -> bool:
    """True if ``item`` satisfies every clause in ``rule``."""
    if not rule:
        return True

    net = rule.get("network")
    if net and item.network != net:
        return False

    acc = rule.get("account_id")
    if acc and item.account_id != acc:
        return False

    author = rule.get("author")
    if author:
        hay = f"{item.author_handle} {item.author_display}".lower()
        if author.lower() not in hay:
            return False

    if rule.get("has_media") is True and not item.media:
        return False
    if rule.get("has_media") is False and item.media:
        return False

    if rule.get("missing_alt") is True:
        if not item.media or item.missing_alt_count == 0:
            return False

    if rule.get("unreplied") is True and item.reply_count != 0:
        return False

    kw = rule.get("keyword")
    if kw and kw.lower() not in item.text.lower():
        return False

    lang = rule.get("language")
    if lang and item.lang != lang:
        return False

    label = rule.get("moderation_label")
    if label and label not in item.moderation_labels:
        return False

    min_eng = rule.get("min_engagement")
    if min_eng is not None:
        total = item.reply_count + item.reblog_count + item.favourite_count
        if total < min_eng:
            return False

    since = rule.get("since_ms")
    if since is not None and item.created_at < since:
        return False
    until = rule.get("until_ms")
    if until is not None and item.created_at > until:
        return False

    if rule.get("unread") is True and item.read:
        return False
    if rule.get("unread") is False and not item.read:
        return False

    if rule.get("bookmarked") is True and not item.bookmarked:
        return False

    return True


def evaluate(items: list[SocialItem], rule: dict) -> list[SocialItem]:
    """Return the items matching ``rule``, newest first."""
    hits = [it for it in items if matches(it, rule)]
    hits.sort(key=lambda it: it.created_at, reverse=True)
    return hits
