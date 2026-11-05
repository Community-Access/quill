"""Send This Document, Publish to Another Site, and Duplicate (wordpress.md 9.16).

Three ways a draft comes from something that already exists:

* **Send This Document to WordPress:** any ordinary document becomes a new
  draft. Its first heading becomes the title, its headings become heading
  blocks (the Markdown conversion does that), and its pictures on this
  computer go to the Media Library on the send (:func:`local_pictures`).
* **Publish to Another Site:** a post copied to another connected site as a
  draft there. Pictures are uploaded again; categories and tags are matched
  by name (:func:`match_terms`), and the missing ones created after asking.
* **Duplicate:** a new draft from any page or post, on the same site (same
  pictures, same terms) or another (as above), with everything but the date
  and the status.

Pictures are fetched only from the source site's own address, and without the
sign-in: they are its public uploads.

Wx-free.
"""

from __future__ import annotations

import html
import json
import mimetypes
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import Item, Term
from quill.core.wordpress.site_media import MediaItem, upload_media

# --------------------------------------------------------------------------- #
# Send This Document


_MD_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.M)
_HTML_H = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.I | re.S)


def title_and_body(text: str, text_format: str, fallback: str) -> tuple[str, str]:
    """The first heading as the title, and the text without it."""
    pattern = _HTML_H if text_format == "html" else _MD_HEADING
    match = pattern.search(text)
    if match is None:
        return fallback, text
    title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
    body = (text[: match.start()] + text[match.end() :]).lstrip("\r\n")
    return html.unescape(title) or fallback, body


def document_format(path: Path | None) -> str:
    """``html`` for a web page, ``markdown`` for everything else (Markdown is plain text)."""
    if path is not None and path.suffix.lower() in {".html", ".htm"}:
        return "html"
    return "markdown"


@dataclass(frozen=True)
class LocalPicture:
    reference: str  # the address as the document writes it
    path: Path
    alt: str


_MD_IMAGE = re.compile(r"!\[((?:\\.|[^\]\\])*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_IMG = re.compile(r"<img\b[^>]*>", re.I)
_ATTR = re.compile(r"\b(src|alt)\s*=\s*([\"'])(.*?)\2", re.I | re.S)


def _local(reference: str, base: Path | None) -> Path | None:
    ref = reference.strip()
    if re.match(r"^[a-z][a-z0-9+.-]*://", ref, re.I) and not ref.lower().startswith("file:"):
        return None
    if ref.lower().startswith("file:"):
        local = unquote(urlparse(ref).path)
        candidate = Path(local[1:] if re.match(r"^/[A-Za-z]:", local) else local)
    else:
        candidate = Path(unquote(ref))
        if not candidate.is_absolute() and base is not None:
            candidate = base / candidate
    try:
        return candidate if candidate.is_file() else None
    except OSError:
        return None


def local_pictures(text: str, base: Path | None) -> list[LocalPicture]:
    """Pictures the document shows from this computer, each once."""
    found: dict[str, LocalPicture] = {}
    for m in _MD_IMAGE.finditer(text):
        path = _local(m.group(2), base)
        if path is not None:
            found.setdefault(m.group(2), LocalPicture(m.group(2), path, m.group(1)))
    for m in _IMG.finditer(text):
        attrs = {k.lower(): v for k, _q, v in _ATTR.findall(m.group(0))}
        src = attrs.get("src", "")
        path = _local(src, base) if src else None
        if path is not None:
            found.setdefault(src, LocalPicture(src, path, html.unescape(attrs.get("alt", ""))))
    return list(found.values())


def with_file_addresses(text: str, pictures: list[LocalPicture]) -> str:
    """Point each picture at its file address, which the send swaps for the library's."""
    for picture in pictures:
        uri = picture.path.resolve().as_uri()
        text = text.replace(f"]({picture.reference})", f"]({uri})")
        for quote in ('"', "'"):
            text = re.sub(
                r"(src\s*=\s*)" + quote + re.escape(picture.reference) + quote,
                r"\g<1>" + quote + uri.replace("\\", "\\\\") + quote,
                text,
            )
    return text


# --------------------------------------------------------------------------- #
# Copying an item between sites


def match_terms(source: list[Term], target: list[Term]) -> tuple[dict[int, int], list[Term]]:
    """Source term id -> target term id, by name (any case), and the names with no match."""
    by_name = {t.name.casefold(): t.id for t in target}
    mapping: dict[int, int] = {}
    missing: list[Term] = []
    for term in source:
        found = by_name.get(term.name.casefold())
        if found is None:
            missing.append(term)
        else:
            mapping[term.id] = found
    return mapping, missing


def as_new_draft(item: Item, *, same_site: bool, terms: dict[int, int] | None = None) -> Item:
    """A copy with everything but its id, date and status (a draft)."""
    terms = terms or {}
    keep = same_site
    return replace(
        item,
        id=0,
        status="draft",
        slug="",
        link="",
        modified_gmt="",
        date_gmt="",
        title=item.title if not same_site else f"{item.title} (copy)",
        categories=item.categories if keep else [terms[c] for c in item.categories if c in terms],
        tags=item.tags if keep else [terms[t] for t in item.tags if t in terms],
        featured_media=item.featured_media if keep else 0,
        parent=item.parent if keep else 0,
        author=item.author if keep else 0,
        password=item.password,
    )


_SRC = re.compile(r"(\bsrc\s*=\s*[\"'])([^\"']+)([\"'])", re.I)


def site_pictures(content: str, site_url: str) -> list[str]:
    """Picture addresses in *content* that live on the site at *site_url*."""
    host = (urlparse(site_url).hostname or "").lower()
    seen: dict[str, None] = {}
    for m in _SRC.finditer(content):
        url = html.unescape(m.group(2))
        if (urlparse(url).hostname or "").lower() == host and host:
            seen.setdefault(url, None)
    return list(seen)


def fetch_picture(api: WordPressApi, url: str) -> bytes:
    """A public upload from the source site, through the site's own opener, unsigned."""
    request = Request(url, headers={"User-Agent": "QUILL"}, method="GET")
    try:
        with api._opener(request, timeout=max(api.timeout, 60.0)) as response:
            return bytes(response.read())
    except Exception as exc:  # noqa: BLE001 - said as one sentence
        raise WordPressApiError(
            f"QUILL could not fetch a picture from {api.site_name}: {url}."
        ) from exc


def move_pictures(
    source: WordPressApi,
    target: WordPressApi,
    content: str,
    source_url: str,
    progress: Callable[[int, int], None] | None = None,
) -> tuple[str, list[MediaItem]]:
    """Upload every picture of *content* again, to *target*, and point the content at them.

    A WordPress image block names its library item (``"id":12``); the copy's
    id is the new one, so the block still opens in the editor.
    """
    urls = site_pictures(content, source_url)
    uploaded: list[MediaItem] = []
    for number, url in enumerate(urls, 1):
        name = Path(unquote(urlparse(url).path)).name or "picture"
        kind = mimetypes.guess_type(name)[0] or "application/octet-stream"
        media = upload_media(target, name, fetch_picture(source, url), kind)
        uploaded.append(media)
        content = content.replace(url, media.source_url)
        content = content.replace(html.escape(url, quote=True), media.source_url)
        if progress is not None:
            progress(number, len(urls))
    return content, uploaded


def strip_image_ids(content: str) -> str:
    """Image blocks without the source site's library ids, which mean nothing elsewhere.

    The picture itself is the new upload (its address is in the block); the
    editor on the other site treats it as a picture by address.
    """

    def block(m: re.Match[str]) -> str:
        try:
            attrs = json.loads(m.group(1))
        except ValueError:
            return m.group(0)
        if not isinstance(attrs, dict):
            return m.group(0)
        attrs.pop("id", None)
        encoded = json.dumps(attrs, separators=(",", ":")) if attrs else ""
        return f"<!-- wp:image {encoded} {m.group(2)}-->".replace("  ", " ")

    content = re.sub(r"<!-- wp:image (\{.*?\}) (/?)-->", block, content)
    return re.sub(r"\s?wp-image-\d+", "", content)
