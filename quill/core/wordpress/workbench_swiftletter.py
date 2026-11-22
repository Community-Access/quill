"""Read-only SwiftLetter navigator nodes and rows for the native Workbench."""

from __future__ import annotations

import time
from collections import Counter

from quill.core.wordpress import swiftletter
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import friendly_date
from quill.core.wordpress.workbench_listing import pages_for
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
_discovered: dict[str, tuple[float, bool, swiftletter.Discovery | None]] = {}


def forget_discovery(site_url: str = "") -> None:
    """Read SwiftLetter's discovery again next time: for one site, or for every site."""
    if site_url:
        _discovered.pop(site_url, None)
    else:
        _discovered.clear()


def _discover(
    api: WordPressApi, namespaces: tuple[str, ...] | None
) -> tuple[bool, swiftletter.Discovery | None]:
    """Whether the site lists SwiftLetter at all, and what it offers QUILL if it does."""
    key = api.address.site_url
    now = time.monotonic()
    cached = _discovered.get(key)
    if cached is not None and now - cached[0] < DISCOVERY_SECONDS:
        return cached[1], cached[2]
    if api.address.is_wpcom:
        listed = False
    else:
        if namespaces is None:
            namespaces = swiftletter.index_namespaces(api)
        listed = swiftletter.lists_namespace(namespaces)
    found = swiftletter.discover(api, namespaces=namespaces) if listed else None
    _discovered[key] = (now, listed, found)
    return listed, found


def _count_words(count: int | None) -> str:
    if count is None:
        return ""
    return f"{count} article" + ("" if count == 1 else "s")


def tree_names(titles: list[tuple[str, str]]) -> dict[str, str]:
    """Each newsletter's name in the tree, by id: its title, with the id where titles repeat."""
    seen = Counter(title for _key, title in titles)
    return {
        key: f"{title} (newsletter {key})" if seen[title] > 1 else title for key, title in titles
    }


def load_newsletters(
    api: WordPressApi, site: str, namespaces: tuple[str, ...] | None
) -> list[WbRow]:
    listed, available = _discover(api, namespaces)
    if not listed:
        raise swiftletter.SwiftLetterError(
            f"SwiftLetter is not active on {site}, so there are no newsletters to list."
        )
    if available is None:
        raise swiftletter.SwiftLetterError(
            f"SwiftLetter on {site} does not offer the connection QUILL reads. "
            "Ask the site's administrator to update SwiftLetter."
        )
    if not available.can_browse:
        raise swiftletter.SwiftLetterForbidden(
            f"Your account on {site} is not allowed to browse SwiftLetter newsletters."
        )
    found = list(swiftletter.newsletters(api, max_pages=pages_for(3)))
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
                raw={"title": title, "article_count": newsletter.article_count},
            )
        )
    return rows


def load_articles(api: WordPressApi, site: str, newsletter_id: int) -> list[WbRow]:
    newsletter, articles = swiftletter.newsletter_detail(api, newsletter_id)
    named = newsletter.title or f"newsletter {newsletter_id}"
    rows = []
    for position, article in enumerate(articles, 1):
        title = article.title or "Untitled article"
        review = swiftletter.review_words(article.review_state)
        place = f"{position} of {len(articles)}"
        rows.append(
            WbRow(
                ARTICLE,
                site,
                str(article.id),
                {"title": title, "review": review, "position": place},
                f"{title}. {review}. Article {place} in {named}, on {site}.",
                raw={
                    "title": title,
                    "review": review,
                    "review_state": article.review_state,
                    "position": place,
                    "newsletter_id": newsletter_id,
                    "newsletter_title": newsletter.title,
                },
            )
        )
    return rows
