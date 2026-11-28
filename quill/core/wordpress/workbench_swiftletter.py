"""Read-only SwiftLetter navigator nodes and rows for the native Workbench."""

from __future__ import annotations

import time
from collections import Counter

from quill.core.wordpress import swiftletter
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import friendly_date
from quill.core.wordpress.workbench_listing import MORE_PAGES, pages_for
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.tree import NodeSpec

ROOT = "swiftletter"
NEWSLETTER = "swiftletter_newsletter"
ARTICLE = "swiftletter_article"

NODES = (
    NodeSpec(
        ROOT,
        "SwiftLetter",
        "site",
        loader="swiftletter:newsletters",
        columns=("title", "articles", "changed"),
        row_type=NEWSLETTER,
    ),
    NodeSpec(
        NEWSLETTER,
        "Newsletter",
        ROOT,
        loader="swiftletter:articles",
        columns=("title", "review", "position"),
        row_type=ARTICLE,
        dynamic=True,
    ),
)

#: How long one site's SwiftLetter discovery is trusted before it is read again.
#: The list reloads on every visit and after a tree rebuild; discovery need not.
DISCOVERY_SECONDS = 300.0
_discovered: dict[str, tuple[float, bool, swiftletter.Discovery | Exception | None]] = {}

#: Said, once, when SwiftLetter is asked for on a WordPress.com connection (answer 14).
WPCOM_WORDS = (
    "{site} is connected through WordPress.com, and QUILL offers SwiftLetter only on "
    "self-hosted WordPress sites."
)


def forget_discovery(site_url: str = "") -> None:
    """Read SwiftLetter's discovery again next time: for one site, or for every site."""
    if site_url:
        _discovered.pop(site_url, None)
    else:
        _discovered.clear()


def discovered(site_url: str) -> swiftletter.Discovery | None:
    """What this site's SwiftLetter offered when the Workbench last read it, without
    asking again; None when it has not been read (SwiftLetter still checks every request)."""
    cached = _discovered.get(site_url)
    found = cached[2] if cached is not None else None
    return found if isinstance(found, swiftletter.Discovery) else None


def _discover(
    api: WordPressApi, namespaces: tuple[str, ...] | None
) -> tuple[bool, swiftletter.Discovery | None]:
    """Whether the site lists SwiftLetter at all, and what it offers QUILL if it does."""
    key = api.address.site_url
    now = time.monotonic()
    cached = _discovered.get(key)
    if cached is None or now - cached[0] >= DISCOVERY_SECONDS:
        if namespaces is None:
            namespaces = swiftletter.index_namespaces(api)
        listed = swiftletter.lists_namespace(namespaces)
        found: swiftletter.Discovery | Exception | None = None
        if listed:
            # A version QUILL cannot speak is kept too, so it is explained, not re-read.
            try:
                found = swiftletter.discover(api, namespaces=namespaces)
            except swiftletter.SwiftLetterVersionError as exc:
                found = exc
        cached = (now, listed, found)
        _discovered[key] = cached
    if isinstance(cached[2], Exception):
        raise cached[2]
    return cached[1], cached[2]


def _count_words(count: int | None) -> str:
    if count is None:
        return ""
    return f"{count} article" + ("" if count == 1 else "s")


def changed_words(gmt: str, by: str | None) -> str:
    """ "Last changed 20 November 2026, 3:04 PM by Pat Reyes.", or "... Editor unknown."

    SwiftLetter sends ``modified_by`` null when it cannot verify who made the last
    edit, and QUILL never guesses from the byline. A row with neither says nothing.
    """
    if not gmt and not by:
        return ""
    when = f" {friendly_date(gmt)}" if gmt else ""
    who = f" by {by}." if by else f". {swiftletter.EDITOR_UNKNOWN}."
    return f"Last changed{when}{who}"


def left_words(shown: int, total: int | None) -> str:
    """How many newsletters remain past the ones listed, said once after the count."""
    if total is None or total <= shown:
        return ""
    left = total - shown
    return (
        f"{left} more of the site's {total} newsletters are not listed yet. View > Load More "
        f"reads {MORE_PAGES * 100} more; Load All reads every one."
    )


def tree_names(titles: list[tuple[str, str]]) -> dict[str, str]:
    """Each newsletter's name in the tree, by id: its title, with the id where titles repeat."""
    seen = Counter(title for _key, title in titles)
    return {
        key: f"{title} (newsletter {key})" if seen[title] > 1 else title for key, title in titles
    }


def load_newsletters(
    api: WordPressApi, site: str, namespaces: tuple[str, ...] | None
) -> list[WbRow]:
    if api.address.is_wpcom:
        raise swiftletter.SwiftLetterError(WPCOM_WORDS.format(site=site))
    listed, available = _discover(api, namespaces)
    if not listed:
        raise swiftletter.SwiftLetterError(
            f"SwiftLetter is not active on {site}, so there are no newsletters to list."
        )
    if not isinstance(available, swiftletter.Discovery):
        raise swiftletter.SwiftLetterError(
            f"SwiftLetter on {site} does not offer the connection QUILL reads. "
            "Ask the site's administrator to update SwiftLetter."
        )
    if not available.can_browse:
        raise swiftletter.SwiftLetterForbidden(
            f"Your account on {site} is not allowed to browse SwiftLetter newsletters."
        )
    listing = swiftletter.newsletter_list(api, max_pages=pages_for(3))
    found = list(listing.items)
    names = tree_names([(str(n.id), n.title or "Untitled newsletter") for n in found])
    rows = []
    for newsletter in found:
        title = names[str(newsletter.id)]
        count = _count_words(newsletter.article_count)
        changed = friendly_date(newsletter.modified_gmt) if newsletter.modified_gmt else ""
        detail = f"{title}."
        if count:
            detail += f" {count}."
        if changed:
            detail += f" Last changed {changed}."
        rows.append(
            WbRow(
                NEWSLETTER,
                site,
                str(newsletter.id),
                {
                    "title": title,
                    "articles": ""
                    if newsletter.article_count is None
                    else str(newsletter.article_count),
                    "changed": changed,
                },
                detail,
                modified_gmt=newsletter.modified_gmt,
                raw={
                    "title": title,
                    "article_count": newsletter.article_count,
                    "left": left_words(len(found), listing.total),
                },
            )
        )
    return rows


def load_articles(api: WordPressApi, site: str, newsletter_id: int) -> list[WbRow]:
    if api.address.is_wpcom:
        raise swiftletter.SwiftLetterError(WPCOM_WORDS.format(site=site))
    newsletter, articles = swiftletter.newsletter_detail(api, newsletter_id)
    named = newsletter.title or f"newsletter {newsletter_id}"
    rows = []
    for position, article in enumerate(articles, 1):
        title = article.title or "Untitled article"
        review = swiftletter.review_words(article.review_state)
        place = f"{position} of {len(articles)}"
        detail = f"{title}. {review}. Article {place} in {named}, on {site}."
        changed = changed_words(article.modified_gmt, article.modified_by)
        if changed:
            detail += f" {changed}"
        if article.can_edit is False:
            detail += " Your account cannot edit this article."
        rows.append(
            WbRow(
                ARTICLE,
                site,
                str(article.id),
                {"title": title, "review": review, "position": place},
                detail,
                modified_gmt=article.modified_gmt,
                raw={
                    "title": title,
                    "review": review,
                    "review_state": article.review_state,
                    "position": place,
                    "newsletter_id": newsletter_id,
                    "newsletter_title": newsletter.title,
                    "can_edit": article.can_edit,
                    "can_review": article.can_review,
                    "modified_by": article.modified_by,
                },
            )
        )
    return rows
