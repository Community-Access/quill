"""The shared macOS and Windows client for SwiftLetter's editorial REST API."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from quill.core.wordpress.api import WordPressApi, WordPressApiError

_NAMESPACE = "swiftletter/v1"
_ARTICLE_BASE = "swl-articles"
_VERSION = re.compile(r'"[0-9a-f]{64}"')

#: Review states as words, so the state never rests on colour or a check mark alone.
#: ``changed`` is for a reviewed article edited since; SwiftLetter 1.1.0 reports only
#: ``review_confirmed``, so it appears once the API sends ``review_state`` on a row.
REVIEW_WORDS = {
    "reviewed": "Reviewed",
    "not_reviewed": "Not reviewed",
    "changed": "Changed since review",
}


class SwiftLetterError(WordPressApiError):
    """SwiftLetter refused a request, or answered in a shape QUILL cannot read."""

    code = "QUILL-SWIFTLETTER-API-REQUEST"


class SwiftLetterVersionError(SwiftLetterError):
    """The site's SwiftLetter speaks a connection version this QUILL does not know."""

    code = "QUILL-SWIFTLETTER-API-VERSION"


class SwiftLetterForbidden(SwiftLetterError):
    """The person's account may not do this in SwiftLetter."""

    code = "QUILL-SWIFTLETTER-API-FORBIDDEN"


def review_words(state: str) -> str:
    """The words for a review state; an unknown state is said as it came."""
    return REVIEW_WORDS.get(state, state.replace("_", " ").capitalize() or "Not reviewed")


@dataclass(frozen=True)
class Discovery:
    can_browse: bool
    can_save: bool


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
class ArticleRow:
    id: int
    title: str
    review_state: str = "not_reviewed"

    @property
    def reviewed(self) -> bool:
        return self.review_state == "reviewed"


@dataclass(frozen=True)
class Newsletter:
    id: int
    title: str
    article_count: int | None = None
    modified_gmt: str = ""


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


def _edit_version(value: object) -> str:
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        raise WordPressApiError(
            "SwiftLetter could not verify this article version. Reopen it before saving."
        )
    return value


def lists_namespace(namespaces: Iterable[str]) -> bool:
    """Whether a REST index's *namespaces* include SwiftLetter's, slashes ignored."""
    return _NAMESPACE in {str(name).strip("/") for name in namespaces}


def index_namespaces(api: WordPressApi) -> tuple[str, ...]:
    """The namespaces the site's REST index lists, read once."""
    reported = _object(api.get("")).get("namespaces")
    return tuple(str(name) for name in reported) if isinstance(reported, list) else ()


def discover(api: WordPressApi, *, namespaces: Iterable[str] | None = None) -> Discovery | None:
    """Return None when a site lacks SwiftLetter or only has the dashboard API."""
    if api.address.is_wpcom:
        return None
    if namespaces is None:
        namespaces = index_namespaces(api)
    # The same comparison as the Workbench's plugin branches, so the two never disagree.
    if not lists_namespace(namespaces):
        return None
    metadata = _object(api.get(_NAMESPACE)).get("swiftletter")
    if metadata is None:
        return None
    data = _object(metadata)
    version = data.get("api_version")
    if not isinstance(version, str) or not re.fullmatch(r"1\.\d+", version):
        said = version if isinstance(version, str) and version else "an unknown version"
        raise SwiftLetterVersionError(
            f"SwiftLetter on this site speaks version {said} of its connection, and this "
            "QUILL knows version 1. Update QUILL, or ask the site's administrator."
        )
    if data.get("article_rest_base") != _ARTICLE_BASE:
        raise WordPressApiError(
            "This site's SwiftLetter article address is not supported by QUILL."
        )
    features = _object(data.get("features"))
    browse = (
        _object(data.get("capabilities")).get("read") is True and features.get("browse") is True
    )
    return Discovery(browse, browse and features.get("article_save") is True)


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


def newsletters(api: WordPressApi, *, max_pages: int = 3) -> Iterator[Newsletter]:
    for item in api.iter_collection(f"{_NAMESPACE}/newsletters", max_pages=max_pages):
        yield _newsletter(_object(item))


def newsletter_detail(
    api: WordPressApi, newsletter_id: int
) -> tuple[Newsletter, tuple[ArticleRow, ...]]:
    """One newsletter and its articles, in the newsletter's order (the server sorts them)."""
    data = _object(api.get(f"{_NAMESPACE}/newsletters/{_id(newsletter_id)}"))
    rows = (_object(item) for item in _list(data.get("articles")))
    found = tuple(
        ArticleRow(_id(row.get("id")), _text(row.get("title")), _review_state(row)) for row in rows
    )
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
    data = _object(api.get(f"wp/v2/{_ARTICLE_BASE}/{_id(article_id)}", context="edit"))
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


def save_article(api: WordPressApi, article: Article, *, title: str, content: str) -> str:
    """Explicit remote save only. Do not refresh and retry on a conflict."""
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
        if exc.status == 412:
            raise WordPressApiError(
                "Someone changed this article on the site. Your local copy was not sent. "
                "Compare it with the current article before trying again.",
                status=exc.status,
                wp_code=exc.wp_code,
            ) from exc
        raise
    saved = _object(response.payload)
    if _id(saved.get("id")) != article.id:
        raise WordPressApiError(
            "SwiftLetter returned a different article. Reopen it before saving."
        )
    return _edit_version(saved.get("edit_version"))
