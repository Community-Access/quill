"""The shared macOS and Windows client for SwiftLetter's editorial REST API.

Self-hosted WordPress only: a WordPress.com connection never looks for
SwiftLetter (Michael's answer 14). Refusals become the coded errors in
:mod:`~quill.core.wordpress.swiftletter_errors`, each saying SwiftLetter's own
sentence. Nothing here retries a request, and nothing writes except
:func:`save_article_stored` (and its shorter :func:`save_article`).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.swiftletter_errors import (
    SwiftLetterArticleLocked,
    SwiftLetterConflict,
    SwiftLetterError,
    SwiftLetterForbidden,
    SwiftLetterVersionError,
    coded_refusal,
)

__all__ = [
    "Article",
    "ArticleRow",
    "Discovery",
    "Newsletter",
    "NewsletterList",
    "SavedArticle",
    "SwiftLetterArticleLocked",
    "SwiftLetterConflict",
    "SwiftLetterError",
    "SwiftLetterForbidden",
    "SwiftLetterVersionError",
    "articles",
    "current_article",
    "discover",
    "index_namespaces",
    "lists_namespace",
    "newsletter_detail",
    "newsletter_list",
    "newsletters",
    "open_article",
    "review_words",
    "save_article",
    "save_article_stored",
]

_NAMESPACE = "swiftletter/v1"
_ARTICLE_BASE = "swl-articles"
_VERSION = re.compile(r'"[0-9a-f]{64}"')
_API_VERSION = re.compile(r"(\d+)(?:\.\d+)*")
_PER_PAGE = 100

#: Review states as words, so the state never rests on colour or a check mark alone.
#: ``changed`` (Changed since review) is SwiftLetter's confirmed slug; the 1.1.0 test
#: build sends only ``review_confirmed``, which still reads as the other two.
REVIEW_WORDS = {
    "reviewed": "Reviewed",
    "not_reviewed": "Not reviewed",
    "changed": "Changed since review",
}

#: Said when SwiftLetter cannot say who last changed an article (``modified_by`` null).
EDITOR_UNKNOWN = "Editor unknown"


def review_words(state: str) -> str:
    """The words for a review state; an unknown state is said as it came."""
    return REVIEW_WORDS.get(state, state.replace("_", " ").capitalize() or "Not reviewed")


@dataclass(frozen=True)
class Discovery:
    """What this site's SwiftLetter offers this account. A missing feature flag is off."""

    can_browse: bool
    can_save: bool
    can_open: bool = False
    features: frozenset[str] = field(default=frozenset(), compare=False)

    def offers(self, flag: str) -> bool:
        """Whether SwiftLetter sent *flag* as on; a QUILL command shows only then."""
        return flag in self.features


@dataclass(frozen=True)
class Article:
    site_url: str
    id: int
    title: str
    content: str
    newsletter_ids: tuple[int, ...]
    review_state: str
    edit_version: str | None


@dataclass(frozen=True)
class SavedArticle:
    """What a save answered: the new version and, when sent, what WordPress stored.

    WordPress may sanitise content, so the stored text can differ from what QUILL
    sent. ``stored_title`` and ``stored_content`` are None when the site did not
    return them (the 1.1.0 test build), and then nothing is known to differ.
    """

    id: int
    edit_version: str
    sent_title: str
    sent_content: str
    stored_title: str | None = None
    stored_content: str | None = None

    @property
    def returned_stored(self) -> bool:
        return self.stored_title is not None or self.stored_content is not None

    @property
    def title_changed(self) -> bool:
        return self.stored_title is not None and self.stored_title != self.sent_title

    @property
    def content_changed(self) -> bool:
        return self.stored_content is not None and self.stored_content != self.sent_content

    @property
    def stored_differs(self) -> bool:
        """Whether the site kept something other than what was sent: tell the person, offer
        Compare, and never replace their local copy silently."""
        return self.title_changed or self.content_changed

    def baseline(self, opened: Article) -> Article:
        """The article as the site now holds it, for the next save's ``If-Match``."""
        return replace(
            opened,
            title=self.sent_title if self.stored_title is None else self.stored_title,
            content=self.sent_content if self.stored_content is None else self.stored_content,
            edit_version=self.edit_version,
        )


@dataclass(frozen=True)
class ArticleRow:
    """One article in a newsletter's detail. The permission hints are for the interface
    only; SwiftLetter still checks every request. None means the site did not say."""

    id: int
    title: str
    review_state: str = "not_reviewed"
    can_edit: bool | None = None
    can_review: bool | None = None
    modified_gmt: str = ""
    modified_by: str | None = None

    @property
    def reviewed(self) -> bool:
        return self.review_state == "reviewed"

    @property
    def editor_words(self) -> str:
        """Who last changed the title or body, or "Editor unknown"."""
        return self.modified_by or EDITOR_UNKNOWN


@dataclass(frozen=True)
class Newsletter:
    id: int
    title: str
    article_count: int | None = None
    modified_gmt: str = ""


@dataclass(frozen=True)
class NewsletterList:
    """The newsletters read so far, and how many the site has (``X-WP-Total``) if it said."""

    items: tuple[Newsletter, ...]
    total: int | None = None

    @property
    def remaining(self) -> int:
        return max(0, self.total - len(self.items)) if self.total is not None else 0


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WordPressApiError(
            "SwiftLetter returned an unexpected response. Refresh and try again."
        )
    return value


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise WordPressApiError(
            "SwiftLetter did not return the expected text. Refresh and try again."
        )
    return value


def _id(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise WordPressApiError("SwiftLetter returned an invalid item number.")
    return value


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise WordPressApiError(
            "SwiftLetter did not return the expected list. Refresh and try again."
        )
    return value


def _flag(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _stored(value: object) -> str | None:
    """A stored field as WordPress returns it: plain text, or ``{"raw": ...}``."""
    if isinstance(value, dict):
        value = value.get("raw")
    return value if isinstance(value, str) else None


def _edit_version(value: object) -> str:
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        raise WordPressApiError(
            "SwiftLetter could not verify this article version. Reopen it before saving."
        )
    return value


def _get(api: WordPressApi, route: str, **params: object) -> object:
    """A read, with SwiftLetter's refusals turned into its coded errors."""
    try:
        return api.get(route, **params)
    except WordPressApiError as exc:
        raise coded_refusal(exc) from exc


def lists_namespace(namespaces: Iterable[str]) -> bool:
    """Whether a REST index's *namespaces* include SwiftLetter's, slashes ignored."""
    return _NAMESPACE in {str(name).strip("/") for name in namespaces}


def index_namespaces(api: WordPressApi) -> tuple[str, ...]:
    """The namespaces the site's REST index lists, read once."""
    reported = _object(api.get("")).get("namespaces")
    return tuple(str(name) for name in reported) if isinstance(reported, list) else ()


def _check_version(version: object) -> None:
    """Any 1.x is spoken; a later major version, or none, is refused in one sentence."""
    found = _API_VERSION.fullmatch(version) if isinstance(version, str) else None
    if found is not None and found.group(1) == "1":
        return
    said = f"version {version}" if isinstance(version, str) and version else "a version"
    raise SwiftLetterVersionError(
        f"SwiftLetter on this site uses {said} of its connection, which needs a newer QUILL."
    )


def discover(api: WordPressApi, *, namespaces: Iterable[str] | None = None) -> Discovery | None:
    """Return None when a site lacks SwiftLetter, only has the dashboard API, or is on
    WordPress.com, where QUILL does not offer SwiftLetter."""
    if api.address.is_wpcom:
        return None
    if namespaces is None:
        namespaces = index_namespaces(api)
    # The same comparison as the Workbench's plugin branches, so the two never disagree.
    if not lists_namespace(namespaces):
        return None
    metadata = _object(_get(api, _NAMESPACE)).get("swiftletter")
    if metadata is None:
        return None
    data = _object(metadata)
    _check_version(data.get("api_version"))
    if data.get("article_rest_base") != _ARTICLE_BASE:
        raise SwiftLetterError("This site's SwiftLetter article address is not supported by QUILL.")
    flags = data.get("features")
    rights = data.get("capabilities")
    on = frozenset(
        str(name) for name, value in (flags.items() if isinstance(flags, dict) else ()) if value
    )
    readable = isinstance(rights, dict) and rights.get("read") is True
    browse = readable and "browse" in on
    return Discovery(
        browse, browse and "article_save" in on, readable and "article_context" in on, on
    )


def _newsletter(row: dict[str, object]) -> Newsletter:
    count = row.get("article_count")
    modified = row.get("modified_gmt")
    return Newsletter(
        _id(row.get("id")),
        _text(row.get("title")),
        count if isinstance(count, int) and not isinstance(count, bool) and count >= 0 else None,
        modified if isinstance(modified, str) else "",
    )


def _review_state(row: dict[str, object]) -> str:
    """A row's review state: the API's own word when it sends one, else its yes or no."""
    state = row.get("review_state")
    if isinstance(state, str) and state:
        return state
    return "reviewed" if row.get("review_confirmed") is True else "not_reviewed"


def _article_row(row: dict[str, object]) -> ArticleRow:
    modified = row.get("modified_gmt")
    by = row.get("modified_by")
    if isinstance(by, dict):  # a {"id", "name"} object, should SwiftLetter send one
        by = by.get("name")
    return ArticleRow(
        _id(row.get("id")),
        _text(row.get("title")),
        _review_state(row),
        can_edit=_flag(row.get("can_edit")),
        can_review=_flag(row.get("can_review")),
        modified_gmt=modified if isinstance(modified, str) else "",
        modified_by=by.strip() or None if isinstance(by, str) else None,
    )


def newsletter_list(api: WordPressApi, *, max_pages: int = 3) -> NewsletterList:
    """Up to *max_pages* pages of newsletters, and the site's total when it sends one.

    The Workbench keeps its usual three pages and More (Michael's answer 12); the
    total lets the list say how many remain rather than look complete.
    """
    found: list[Newsletter] = []
    total: int | None = None
    page = 1
    while page <= max_pages:
        try:
            response = api.request(
                "GET", f"{_NAMESPACE}/newsletters", params={"per_page": _PER_PAGE, "page": page}
            )
        except WordPressApiError as exc:
            if exc.wp_code == "rest_post_invalid_page_number" and page > 1:
                break
            raise coded_refusal(exc) from exc
        items = _list(response.payload) if response.payload is not None else []
        found.extend(_newsletter(_object(item)) for item in items)
        if response.total is not None:
            total = response.total
        pages = response.total_pages
        if (pages is not None and page >= pages) or (pages is None and len(items) < _PER_PAGE):
            break
        page += 1
    return NewsletterList(tuple(found), total)


def newsletters(api: WordPressApi, *, max_pages: int = 3) -> Iterator[Newsletter]:
    yield from newsletter_list(api, max_pages=max_pages).items


def newsletter_detail(
    api: WordPressApi, newsletter_id: int
) -> tuple[Newsletter, tuple[ArticleRow, ...]]:
    """One newsletter and its articles, in the newsletter's order (the server sorts them)."""
    data = _object(_get(api, f"{_NAMESPACE}/newsletters/{_id(newsletter_id)}"))
    found = tuple(_article_row(_object(item)) for item in _list(data.get("articles")))
    title = data.get("title")
    count = data.get("article_count")
    modified = data.get("modified_gmt")
    newsletter = Newsletter(
        newsletter_id,
        title if isinstance(title, str) else "",
        count if isinstance(count, int) and not isinstance(count, bool) else len(found),
        modified if isinstance(modified, str) else "",
    )
    return newsletter, found


def articles(api: WordPressApi, newsletter_id: int) -> tuple[ArticleRow, ...]:
    return newsletter_detail(api, newsletter_id)[1]


def open_article(api: WordPressApi, article_id: int) -> Article:
    data = _object(_get(api, f"wp/v2/{_ARTICLE_BASE}/{_id(article_id)}", context="edit"))
    context = _object(data.get("swiftletter"))
    version = context.get("edit_version")
    if _id(data.get("id")) != article_id:
        raise WordPressApiError("WordPress returned a different article. Reopen it before saving.")
    parents = tuple(_id(_object(item).get("id")) for item in _list(context.get("newsletters")))
    return Article(
        site_url=api.address.site_url,
        id=article_id,
        title=_text(_object(data.get("title")).get("raw")),
        content=_text(_object(data.get("content")).get("raw")),
        newsletter_ids=parents,
        review_state=_text(context.get("review_state")),
        edit_version=None if version is None else _edit_version(version),
    )


def current_article(api: WordPressApi, article: Article) -> Article:
    """The article as the site holds it now, for Compare with Site (Michael's answer 3).

    A read through the same authenticated edit route; it never touches the local copy
    and never retries a save.
    """
    if api.address.is_wpcom or api.address.site_url != article.site_url:
        raise WordPressApiError("Open this article from its original WordPress site to compare.")
    return open_article(api, article.id)


def save_article_stored(
    api: WordPressApi, article: Article, *, title: str, content: str
) -> SavedArticle:
    """Explicit remote save only, sent once. A conflict or a lock is refused, never retried."""
    if api.address.is_wpcom or api.address.site_url != article.site_url:
        raise WordPressApiError("Open this article from its original WordPress site before saving.")
    try:
        response = api.request(
            "POST",
            f"{_NAMESPACE}/articles/{_id(article.id)}/save",
            headers={"If-Match": _edit_version(article.edit_version)},
            json_body={"title": title, "content": content},
        )
    except WordPressApiError as exc:
        raise coded_refusal(exc, saving=True) from exc
    saved = _object(response.payload)
    if _id(saved.get("id")) != article.id:
        raise WordPressApiError(
            "SwiftLetter returned a different article. Reopen it before saving."
        )
    return SavedArticle(
        article.id,
        _edit_version(saved.get("edit_version")),
        title,
        content,
        _stored(saved.get("title")),
        _stored(saved.get("content")),
    )


def save_article(api: WordPressApi, article: Article, *, title: str, content: str) -> str:
    """:func:`save_article_stored`, answering only the new ``edit_version``."""
    return save_article_stored(api, article, title=title, content=content).edit_version
