"""Read a WordPress eXtended RSS file, from any WordPress site (wp_missing.md, Moving).

:func:`read_wxr` turns a WXR 1.0, 1.1 or 1.2 file into plain data
(:class:`WxrFile`): the channel's addresses, the authors, the terms, and each
item with its type, status, text, terms, custom fields and, for attachments,
the file's address. Parsing goes through :mod:`quill.core.safe_xml`, so a
file with a DTD or entity declarations is refused rather than expanded.
Files over :data:`MAX_FILE_BYTES` are refused, and past :data:`MAX_ITEMS`
items the rest are counted and named as left out, never silently dropped.

:func:`validate_wxr` is the check Export Site as WXR runs on its own file.
Wx-free and network-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError

__all__ = [
    "MAX_FILE_BYTES",
    "MAX_ITEMS",
    "WxrAuthor",
    "WxrError",
    "WxrFile",
    "WxrItem",
    "WxrTerm",
    "read_wxr",
    "validate_wxr",
]

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_ITEMS = 2000

_CONTENT = "http://purl.org/rss/1.0/modules/content/"
_DC = "http://purl.org/dc/elements/1.1/"
_EXPORT = "http://wordpress.org/export/"


class WxrError(CodedError):
    """A file that is not WXR, or one too large to read; its message is the sentence."""

    code = "QUILL-WP-WXR-UNREADABLE"

    @property
    def plain(self) -> str:
        """The sentence alone, without the support code in front."""
        return str(self.args[0]) if self.args else ""


@dataclass(frozen=True)
class WxrAuthor:
    login: str
    email: str
    name: str


@dataclass(frozen=True)
class WxrTerm:
    taxonomy: str  # category, post_tag, or the custom taxonomy's name
    slug: str
    name: str
    parent: str = ""
    description: str = ""


@dataclass
class WxrItem:
    post_id: int
    post_type: str
    title: str
    link: str
    status: str
    creator: str
    content: str
    excerpt: str
    slug: str
    date: str
    parent: int
    menu_order: int
    attachment_url: str = ""
    terms: list[tuple[str, str, str]] = field(default_factory=list)  # taxonomy, slug, name
    meta: dict[str, str] = field(default_factory=dict)
    comments: int = 0


@dataclass
class WxrFile:
    version: str
    title: str
    site_url: str
    blog_url: str
    authors: list[WxrAuthor] = field(default_factory=list)
    terms: list[WxrTerm] = field(default_factory=list)
    items: list[WxrItem] = field(default_factory=list)
    beyond_cap: int = 0


def _local(tag: str) -> str:
    """``{uri}name`` as ``prefix:name`` for the WXR namespaces; plain names unchanged."""
    if not tag.startswith("{"):
        return tag
    uri, _brace, name = tag[1:].partition("}")
    if uri == _CONTENT:
        return f"content:{name}"
    if uri == _DC:
        return f"dc:{name}"
    if uri.startswith(_EXPORT):
        return f"excerpt:{name}" if uri.rstrip("/").endswith("excerpt") else f"wp:{name}"
    return name


def _text(el: Any, name: str) -> str:
    for child in el:
        if _local(child.tag) == name:
            return (child.text or "").strip() if name != "content:encoded" else child.text or ""
    return ""


def _children(el: Any, name: str) -> list[Any]:
    return [child for child in el if _local(child.tag) == name]


def _int(value: str) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def _parse(data: bytes, name: str) -> Any:
    from quill.core.safe_xml import fromstring

    if len(data) > MAX_FILE_BYTES:
        raise WxrError(
            f"{name} is larger than {MAX_FILE_BYTES // 2**20} MB, which QUILL does not read. "
            "Export the site in parts, by date or by type, and import each."
        )
    try:
        root = fromstring(data)
    except Exception as exc:  # noqa: BLE001 - any parse failure is one sentence
        raise WxrError(f"{name} is not a readable XML file: {exc}") from exc
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise WxrError(f"{name} has no rss channel, so it is not a WordPress export file.")
    return channel


def _term(el: Any, kind: str) -> WxrTerm:
    if kind == "category":
        return WxrTerm(
            "category",
            _text(el, "wp:category_nicename"),
            _text(el, "wp:cat_name"),
            _text(el, "wp:category_parent"),
            _text(el, "wp:category_description"),
        )
    if kind == "tag":
        return WxrTerm(
            "post_tag",
            _text(el, "wp:tag_slug"),
            _text(el, "wp:tag_name"),
            "",
            _text(el, "wp:tag_description"),
        )
    return WxrTerm(
        _text(el, "wp:term_taxonomy"),
        _text(el, "wp:term_slug"),
        _text(el, "wp:term_name"),
        _text(el, "wp:term_parent"),
        _text(el, "wp:term_description"),
    )


def _item(el: Any) -> WxrItem:
    item = WxrItem(
        post_id=_int(_text(el, "wp:post_id")),
        post_type=_text(el, "wp:post_type") or "post",
        title=_text(el, "title"),
        link=_text(el, "link"),
        status=_text(el, "wp:status"),
        creator=_text(el, "dc:creator"),
        content=_text(el, "content:encoded"),
        excerpt=_text(el, "excerpt:encoded"),
        slug=_text(el, "wp:post_name"),
        date=_text(el, "wp:post_date"),
        parent=_int(_text(el, "wp:post_parent")),
        menu_order=_int(_text(el, "wp:menu_order")),
        attachment_url=_text(el, "wp:attachment_url"),
    )
    for cat in _children(el, "category"):
        domain = cat.get("domain", "category")
        item.terms.append((domain, cat.get("nicename", ""), (cat.text or "").strip()))
    for meta in _children(el, "wp:postmeta"):
        key = _text(meta, "wp:meta_key")
        if key:
            item.meta[key] = _text(meta, "wp:meta_value")
    item.comments = len(_children(el, "wp:comment"))
    return item


def read_wxr(data: bytes, name: str = "the file") -> WxrFile:
    """Parse WXR *data*; raises :class:`WxrError` with a sentence when it is not WXR."""
    channel = _parse(data, name)
    version = _text(channel, "wp:wxr_version")
    if not version:
        raise WxrError(f"{name} does not say which WXR version it is, so it is not one.")
    found = WxrFile(
        version,
        _text(channel, "title"),
        _text(channel, "wp:base_site_url"),
        _text(channel, "wp:base_blog_url") or _text(channel, "link"),
    )
    for el in channel:
        tag = _local(el.tag)
        if tag == "wp:author":
            found.authors.append(
                WxrAuthor(
                    _text(el, "wp:author_login"),
                    _text(el, "wp:author_email"),
                    _text(el, "wp:author_display_name"),
                )
            )
        elif tag in ("wp:category", "wp:tag", "wp:term"):
            found.terms.append(_term(el, tag.split(":", 1)[1]))
        elif tag == "item":
            if len(found.items) >= MAX_ITEMS:
                found.beyond_cap += 1
                continue
            found.items.append(_item(el))
    return found


def validate_wxr(path: Path) -> tuple[bool, str]:
    """Read *path* back and check its WXR shape: (good, one sentence)."""
    try:
        channel = _parse(path.read_bytes(), path.name)
    except WxrError as exc:
        return False, str(exc.args[0])
    if _text(channel, "wp:wxr_version") != "1.2":
        return False, f"{path.name} does not say it is WXR version 1.2."
    items = channel.findall("item")
    bad = [i for i in items if not _text(i, "wp:post_type") or not _text(i, "wp:post_id")]
    if bad:
        return False, f"{len(bad)} items in {path.name} have no post type or number."
    return True, f"{path.name} is a well-formed WXR 1.2 file with {len(items)} items."
