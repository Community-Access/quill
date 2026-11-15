"""A static copy of a site for an archive: pages and posts as HTML, with their media (15.11).

PRD 15.11, "Moving out and archiving": a complete export is Export Site as
WXR; this is the other half, a copy anyone can open in a browser years from
now with no WordPress at all. :func:`archive_site` reads the site's
**published** pages and posts over its own REST client and writes, into a
folder the person chose:

- ``index.html``: the site's name, then every page and every post (newest
  first) as a list of links;
- ``pages/<slug>.html`` and ``posts/<date>-<slug>.html``: each one plain,
  accessible HTML (a language, a title, one heading, the date, the content
  as WordPress renders it, a link back to the index);
- ``media/...``: each picture, sound, video or file the content uses, fetched
  **only from the connected site's own host** through the injected fetcher
  (the UI passes Media and Files' capped HTTPS download through the site's own
  opener). An address on any other host is not fetched; it stays as it was
  and is named in :attr:`ArchiveReport.left_out`.

Addresses are rewritten to the local copies: media to ``media/...``, and links
between archived pages and posts to each other's files, so the copy works
offline. ``srcset`` and ``sizes`` are dropped, because they name sizes that
were not fetched. Drafts, private items and anything that needs a password
are never read. Wx-free.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import rendered

__all__ = ["MAX_FILES", "MAX_ITEMS", "ArchiveReport", "archive_site", "same_host"]

MAX_ITEMS = 2000
"""At most this many pages and posts each; the rest are named as left out."""
MAX_FILES = 1000
"""At most this many media files are fetched in one archive."""

_FIELDS = "id,title,content,link,slug,date,type"
_ATTR = re.compile(r"""(\b(?:src|href|poster|data-src)\s*=\s*)(["'])([^"']+)\2""", re.I)
_SRCSET = re.compile(r"""\s(?:srcset|sizes)\s*=\s*(["']).*?\1""", re.I | re.S)
_MEDIA_SUFFIX = re.compile(
    r"\.(?:jpe?g|png|gif|webp|avif|svg|ico|bmp|tiff?|mp3|m4a|ogg|oga|wav|flac|mp4|m4v|webm|"
    r"mov|ogv|vtt|srt|pdf|docx?|xlsx?|pptx?|odt|ods|odp|rtf|txt|csv|zip|epub)$",
    re.I,
)
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class ArchiveReport:
    """What went into the folder, and what did not, each with its reason."""

    pages: int = 0
    posts: int = 0
    files: int = 0
    left_out: list[str] = field(default_factory=list)

    def sentence(self, folder: str) -> str:
        said = (
            f"Archived {self.pages} pages, {self.posts} posts and {self.files} files into "
            f"{folder}. Open index.html there in a browser."
        )
        if self.left_out:
            said += f" {len(self.left_out)} things were left out; the report names each."
        return said


def same_host(url: str, site_url: str) -> bool:
    """Whether *url* is on the connected site's own host."""
    return (
        bool(url)
        and (urlparse(url).hostname or "").lower() == (urlparse(site_url).hostname or "").lower()
    )


def _slug(raw: Mapping[str, Any]) -> str:
    slug = _SAFE.sub("-", str(raw.get("slug") or "")).strip("-.")
    return slug or f"item-{int(raw.get('id', 0) or 0)}"


def _item_path(raw: Mapping[str, Any]) -> str:
    if raw.get("type") == "page":
        return f"pages/{_slug(raw)}.html"
    day = str(raw.get("date") or "")[:10]
    return f"posts/{day + '-' if re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) else ''}{_slug(raw)}.html"


def _media_path(url: str) -> str:
    """Where a fetched file goes: ``media/`` plus its path under uploads, made safe."""
    path = unquote(urlparse(url).path)
    _before, marker, after = path.partition("/wp-content/uploads/")
    tail = after if marker else path.lstrip("/")
    parts = [_SAFE.sub("-", p).strip(".") for p in tail.split("/") if p not in ("", ".", "..")]
    parts = [p for p in parts if p] or ["file"]
    return "media/" + "/".join(parts)


def _key(url: str) -> str:
    got = urlparse(url)
    return f"{(got.hostname or '').lower()}{got.path.rstrip('/')}"


def _read_all(api: Any, route: str, report: ArchiveReport) -> list[dict[str, Any]]:
    params = {"status": "publish", "_fields": _FIELDS, "orderby": "date", "order": "desc"}
    found: list[dict[str, Any]] = []
    try:
        for raw in api.iter_collection(route, params, per_page=100, max_pages=40):
            if isinstance(raw, dict):
                if len(found) >= MAX_ITEMS:
                    report.left_out.append(
                        f"{route}: past the first {MAX_ITEMS}, the rest were not read."
                    )
                    break
                found.append(raw)
    except WordPressApiError as exc:
        report.left_out.append(f"{route}: not read, {exc.plain or exc}")
    return found


def _page(title: str, body: str, *, lang: str, up: str, site: str, when: str = "") -> str:
    dated = f"<p>Published {html.escape(when[:10])}.</p>\n" if when else ""
    back = f'<p><a href="{up}index.html">{html.escape(site)}: all pages and posts</a></p>\n'
    return (
        "<!doctype html>\n"
        f'<html lang="{html.escape(lang)}">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n</head>\n<body>\n"
        f"<header>\n{back}</header>\n<main>\n<h1>{html.escape(title)}</h1>\n{dated}"
        f"{body}\n</main>\n</body>\n</html>\n"
    )


def _write(folder: Path, relative: str, data: bytes) -> Path:
    target = (folder / relative).resolve()
    if not target.is_relative_to(folder.resolve()):
        raise ValueError(f"{relative} would be written outside the archive folder")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def archive_site(
    api: Any,
    folder: Path,
    *,
    site_url: str,
    site_name: str,
    fetch: Callable[[str], bytes] | None,
    lang: str = "en",
) -> ArchiveReport:
    """Write the static copy of the site into *folder*; returns what went in and what did not.

    *fetch* reads one address from the site's own host (``None`` archives the
    text alone and names every file as left out).
    """
    report = ArchiveReport()
    items = [
        *_read_all(api, "wp/v2/pages", report),
        *_read_all(api, "wp/v2/posts", report),
    ]
    by_link = {
        _key(str(raw.get("link") or "")): _item_path(raw) for raw in items if raw.get("link")
    }
    fetched: dict[str, str] = {}  # url -> local path, or "" when it was not fetched
    folder.mkdir(parents=True, exist_ok=True)

    def local_file(url: str) -> str:
        if url in fetched:
            return fetched[url]
        fetched[url] = ""
        if not same_host(url, site_url):
            report.left_out.append(f"Not fetched, on another host: {url}")
        elif fetch is None:
            report.left_out.append(f"Not fetched, files were not asked for: {url}")
        elif report.files >= MAX_FILES:
            report.left_out.append(f"Not fetched, past the first {MAX_FILES} files: {url}")
        else:
            try:
                data = fetch(url)
                relative = _media_path(url)
                _write(folder, relative, data)
                report.files += 1
                fetched[url] = relative
            except Exception as exc:  # noqa: BLE001 - one file's failure is one line
                report.left_out.append(f"Not fetched, {getattr(exc, 'plain', '') or exc}: {url}")
        return fetched[url]

    def rewrite(content: str, up: str) -> str:
        content = _SRCSET.sub("", content)

        def one(match: re.Match[str]) -> str:
            lead, quote, value = match.groups()
            url = urljoin(site_url.rstrip("/") + "/", html.unescape(value))
            path = urlparse(url).path
            if _key(url) in by_link:
                return f"{lead}{quote}{up}{by_link[_key(url)]}{quote}"
            if _MEDIA_SUFFIX.search(path) and (
                "/wp-content/" in path or lead.lower().startswith(("src", "poster", "data-src"))
            ):
                local = local_file(url)
                if local:
                    return f"{lead}{quote}{up}{local}{quote}"
            return match.group(0)

        return _ATTR.sub(one, content)

    listing: dict[str, list[str]] = {"page": [], "post": []}
    for raw in items:
        relative = _item_path(raw)
        title = rendered(raw.get("title")) or f"Untitled {raw.get('type', 'item')}"
        content = raw.get("content")
        markup = str(content.get("rendered", "") if isinstance(content, dict) else content or "")
        when = "" if raw.get("type") == "page" else str(raw.get("date") or "")
        text = _page(title, rewrite(markup, "../"), lang=lang, up="../", site=site_name, when=when)
        _write(folder, relative, text.encode("utf-8"))
        kind = "page" if raw.get("type") == "page" else "post"
        listing[kind].append(f'<li><a href="{relative}">{html.escape(title)}</a></li>')
        if kind == "page":
            report.pages += 1
        else:
            report.posts += 1
    sections = []
    for kind, heading in (("page", "Pages"), ("post", "Posts")):
        rows = listing[kind] or ["<li>None were published.</li>"]
        sections.append(f"<h2>{heading}</h2>\n<ul>\n" + "\n".join(rows) + "\n</ul>")
    index = _page(
        f"{site_name}: an archive",
        f"<p>A static copy of {html.escape(site_url)}, made by QUILL.</p>\n" + "\n".join(sections),
        lang=lang,
        up="",
        site=site_name,
    )
    _write(folder, "index.html", index.encode("utf-8"))
    return report
