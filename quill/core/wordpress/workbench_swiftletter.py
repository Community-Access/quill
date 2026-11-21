"""Read-only SwiftLetter navigator nodes and rows for the native Workbench."""

from __future__ import annotations

from quill.core.wordpress import swiftletter
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.workbench_listing import pages_for
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.tree import NodeSpec

ROOT = "swiftletter"
NEWSLETTER = "swiftletter_newsletter"

NODES = (
    NodeSpec(
        ROOT,
        "SwiftLetter",
        "site",
        loader="swiftletter:newsletters",
        columns=("title",),
        row_type=NEWSLETTER,
    ),
    NodeSpec(
        NEWSLETTER,
        "Newsletter",
        ROOT,
        loader="swiftletter:articles",
        columns=("title", "review", "position"),
        row_type="swiftletter_article",
        dynamic=True,
    ),
)


def load_newsletters(
    api: WordPressApi, site: str, namespaces: tuple[str, ...] | None
) -> list[WbRow]:
    available = swiftletter.discover(api, namespaces=namespaces)
    if available is None:
        raise WordPressApiError("This site does not offer SwiftLetter editing in QUILL yet.")
    if not available.can_browse:
        raise WordPressApiError("Your WordPress account cannot browse SwiftLetter newsletters.")
    rows = []
    for newsletter in swiftletter.newsletters(api, max_pages=pages_for(3)):
        title = newsletter.title or "Untitled newsletter"
        rows.append(
            WbRow(
                NEWSLETTER,
                site,
                str(newsletter.id),
                {"title": title},
                f"{title}. Open Newsletter lists its articles.",
                raw={"title": title},
            )
        )
    return rows


def load_articles(api: WordPressApi, site: str, newsletter_id: int) -> list[WbRow]:
    articles = swiftletter.articles(api, newsletter_id)
    rows = []
    for position, article in enumerate(articles, 1):
        title = article.title or "Untitled article"
        review = "Reviewed" if article.reviewed else "Not reviewed"
        place = f"{position} of {len(articles)}"
        rows.append(
            WbRow(
                "swiftletter_article",
                site,
                str(article.id),
                {"title": title, "review": review, "position": place},
                f"{title}. {review}. Article {place}.",
                raw={
                    "title": title,
                    "review": review,
                    "position": place,
                    "newsletter_id": newsletter_id,
                },
            )
        )
    return rows
