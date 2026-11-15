"""The settings wp-admin keeps to itself, explained with this site's own example (PRD D2, WP-R-047).

WordPress's REST API does not share the Permalinks structure, the Discussion
rules or Search engine visibility, so they cannot be changed from here. They
can still be explained with the site's own content, which is what D2 asks:

- **Permalinks:** what the newest post's address would become under each of
  WordPress's five common choices, which one the site uses now (read from
  that post's own address), and that Redirects can carry an old address on.
- **Discussion:** for each rule wp-admin offers, how many of the site's recent
  comments it would have held (or refused), counted from those comments.
- **Search engine visibility:** what the setting does, and does not do.
- **Plugin settings:** for each plugin the Workbench recognises, which of its
  settings the Workbench reaches, and its own documentation, linked.

Each is a ``setting_help`` row: Enter reads it, Open Its Documentation goes to
the link, and Open in Dashboard goes to the wp-admin screen that changes it.
Wx-free; :func:`more_rows` makes at most two small requests (the newest post,
and the latest hundred comments).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "PLUGIN_DOCS",
    "VISIBILITY",
    "discussion_lines",
    "more_rows",
    "permalink_lines",
]

VISIBILITY = (
    "Search engine visibility (Settings > Reading, Discourage search engines from indexing "
    "this site): when checked, WordPress asks search engines to leave the site out, so "
    "people searching will not find it. It only asks; most engines listen, but the site is "
    "not hidden, and anyone with the address can still read it. It is meant for a site still "
    "being built: uncheck it at launch. WordPress does not share it over its API, so Open in "
    "Dashboard goes to Settings > Reading."
)

#: (namespace, plugin, what the Workbench reaches, its own documentation).
PLUGIN_DOCS: tuple[tuple[str, str, str, str], ...] = (
    (
        "wc/v3",
        "WooCommerce",
        "store settings, shipping, taxes and payment gateways, under Shop > Store Settings",
        "https://woocommerce.com/documentation/woocommerce/",
    ),
    (
        "tribe/events/v1",
        "The Events Calendar",
        "events, venues and organizers; its settings stay in Events > Settings in wp-admin",
        "https://theeventscalendar.com/knowledgebase/",
    ),
    (
        "yoast/v1",
        "Yoast SEO",
        "each item's SEO title and description in Properties, and SEO > Site",
        "https://yoast.com/help/",
    ),
    (
        "rankmath/v1",
        "Rank Math",
        "each item's SEO title and description in Properties",
        "https://rankmath.com/kb/",
    ),
    (
        "gf/v2",
        "Gravity Forms",
        "each form's settings, confirmations and notifications in its Properties, and its feeds",
        "https://docs.gravityforms.com/",
    ),
    (
        "pmpro/v1",
        "Paid Memberships Pro",
        "membership levels, orders, subscriptions and discount codes, under Memberships",
        "https://www.paidmembershipspro.com/documentation/",
    ),
    (
        "jetpack/v4",
        "Jetpack",
        "Jetpack's facts about the site in Overview; its modules are set in Jetpack > Settings",
        "https://jetpack.com/support/",
    ),
)

_CHOICES = (
    ("Plain", "{base}/?p={id}"),
    ("Day and name", "{base}/{y}/{m}/{d}/{slug}/"),
    ("Month and name", "{base}/{y}/{m}/{slug}/"),
    ("Numeric", "{base}/archives/{id}"),
    ("Post name", "{base}/{slug}/"),
)


def _same(a: str, b: str) -> bool:
    return a.rstrip("/").casefold() == b.rstrip("/").casefold()


def permalink_lines(post: Mapping[str, Any], site_url: str) -> list[str]:
    """Each Permalinks choice, with what *post*'s address would become under it."""
    base = (site_url or "").rstrip("/")
    slug = str(post.get("slug", "") or "")
    date = str(post.get("date", "") or "")
    number = str(post.get("id", "") or "")
    if not (base and slug and number and len(date) >= 10):
        return []
    link = str(post.get("link", "") or "")
    y, m, d = date[0:4], date[5:7], date[8:10]
    lines = []
    for name, shape in _CHOICES:
        address = shape.format(base=base, id=number, y=y, m=m, d=d, slug=slug)
        now = ", the one this site uses now" if link and _same(address, link) else ""
        lines.append(f"{name}{now}: your newest post would be at {address}")
    return lines


def _links(comment: Mapping[str, Any]) -> int:
    content = comment.get("content")
    text = ""
    if isinstance(content, Mapping):
        text = str(content.get("raw") or content.get("rendered") or "")
    else:
        text = str(content or "")
    return text.count("<a ") + text.count("http")


def discussion_lines(comments: Sequence[Mapping[str, Any]], max_links: int = 2) -> list[str]:
    """For each Discussion rule, how many of *comments* it would have held or refused."""
    total = len(comments)
    if not total:
        return []
    ordered = sorted(comments, key=lambda c: str(c.get("date_gmt", "") or ""))
    approved: set[str] = set()
    first_timers = 0
    for comment in ordered:
        who = str(comment.get("author_email") or comment.get("author_name") or "").casefold()
        if who and who not in approved:
            first_timers += 1
        if str(comment.get("status", "")) in ("approved", "approve") and who:
            approved.add(who)
    linky = sum(1 for c in comments if _links(c) >= max_links)
    guests = sum(1 for c in comments if not int(c.get("author", 0) or 0))
    of = f"of your last {total} comment{'s' if total != 1 else ''}"
    return [
        f"Comment must be manually approved: would have held all {total} {of}.",
        "Comment author must have a previously approved comment: would have held "
        f"{first_timers} {of}, those from people with no earlier approved comment.",
        f"Hold a comment with {max_links} or more links (WordPress's default): would have held "
        f"{linky} {of}.",
        "Users must be registered and logged in to comment: would have refused "
        f"{guests} {of}, written by visitors who were not signed in.",
        "Comment moderation and disallowed words: the lists are not shared over WordPress's "
        "API, so QUILL cannot count them; Open in Dashboard goes to Settings > Discussion.",
    ]


def _row(site: str, index: int, name: str, text: str, *, link: str = "", screen: str = "") -> WbRow:
    return WbRow(
        "setting_help",
        site,
        f"more:{index}",
        {"setting": name, "value": text},
        f"{name}: {text}",
        link=link,
        subkind=screen,
        raw={"screen": screen},
    )


def more_rows(
    api: WordPressApi, site: str, site_url: str, namespaces: Iterable[str] = ()
) -> list[WbRow]:
    """The settings REST does not share, explained from the site's own posts and comments."""
    rows: list[WbRow] = []
    try:
        newest = api.get("wp/v2/posts", per_page=1, _fields="id,slug,date,link")
    except WordPressApiError:
        newest = []
    post = newest[0] if isinstance(newest, list) and newest else {}
    lines = permalink_lines(post if isinstance(post, Mapping) else {}, site_url)
    said = (
        " ".join(f"{line}." for line in lines)
        + " Changing the choice moves every post's address; WordPress sends most old addresses "
        "on by itself, and Redirects, under the site, can carry any address you have shared."
        if lines
        else "Choose how addresses look in Settings > Permalinks; the site has no post to "
        "show an example with yet."
    )
    rows.append(_row(site, 0, "Permalinks", said, screen="permalinks"))
    try:
        raw = api.get(
            "wp/v2/comments",
            per_page=100,
            status="all",
            context="edit",
            _fields="author,author_email,author_name,status,date_gmt,content",
        )
    except WordPressApiError:
        raw = []
    comments = [c for c in raw if isinstance(c, Mapping)] if isinstance(raw, list) else []
    rules = discussion_lines(comments)
    if not rules:
        rules = ["Discussion rules: no recent comments to count, so no example yet."]
    for index, rule in enumerate(rules, start=1):
        name, _sep, text = rule.partition(": ")
        rows.append(_row(site, index, name, text or rule, screen="discussion"))
    rows.append(
        _row(site, 10, "Search engine visibility", VISIBILITY.partition(": ")[2], screen="reading")
    )
    present = set(namespaces)
    for index, (namespace, plugin, reaches, docs) in enumerate(PLUGIN_DOCS, start=20):
        if namespace in present:
            text = f"The Workbench reaches {reaches}. Its own documentation: {docs}"
            rows.append(_row(site, index, f"{plugin} settings", text, link=docs))
    return rows
