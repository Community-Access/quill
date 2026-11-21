"""The shared macOS and Windows client for SwiftLetter's editorial REST API."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

from quill.core.wordpress.api import WordPressApi, WordPressApiError

_NAMESPACE = "swiftletter/v1"
_ARTICLE_BASE = "swl-articles"
_VERSION = re.compile(r'"[0-9a-f]{64}"')


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
    reviewed: bool


@dataclass(frozen=True)
class Newsletter:
    id: int
    title: str


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


def discover(api: WordPressApi) -> Discovery | None:
    """Return None when a site lacks SwiftLetter or only has the dashboard API."""
    if api.address.is_wpcom:
        return None
    index = _object(api.get(""))
    namespaces = index.get("namespaces")
    if not isinstance(namespaces, list) or _NAMESPACE not in namespaces:
        return None
    metadata = _object(api.get(_NAMESPACE)).get("swiftletter")
    if metadata is None:
        return None
    data = _object(metadata)
    version = data.get("api_version")
    if not isinstance(version, str) or not re.fullmatch(r"1\.\d+", version):
        raise WordPressApiError(
            "This site uses a SwiftLetter API version that QUILL does not support."
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


def newsletters(api: WordPressApi) -> Iterator[Newsletter]:
    for item in api.iter_collection(f"{_NAMESPACE}/newsletters"):
        row = _object(item)
        yield Newsletter(_id(row.get("id")), _text(row.get("title")))


def articles(api: WordPressApi, newsletter_id: int) -> tuple[ArticleRow, ...]:
    data = _object(api.get(f"{_NAMESPACE}/newsletters/{_id(newsletter_id)}"))
    rows = (_object(item) for item in _list(data.get("articles")))
    return tuple(
        ArticleRow(_id(row.get("id")), _text(row.get("title")), row.get("review_confirmed") is True)
        for row in rows
    )


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
