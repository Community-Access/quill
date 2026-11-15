"""Every setting in Settings, explained with the site's own example (PRD D2, WP-R-047).

wp-admin labels a field and leaves the rest to you. Each row of a site's
Settings list says what the setting does *on this site*, built from what the
Settings list already read: "Posts page: News, so visitors see your latest
posts at https://radio.example/news/." The only extra request is for the
two pages a site names as its front and posts pages (their titles and
addresses), made by :func:`page_names` when either is set; a site that will
not say leaves the page by number.

The settings REST does not share (Permalinks, the Discussion rules, search
engine visibility, and plugins' own settings) are explained beside these by
:mod:`quill.core.wordpress.workbench_settings_more`, with the newest post's
address under each Permalinks choice and how many recent comments each
Discussion rule would have held.

Wx-free and network-free apart from :func:`page_names`.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError

__all__ = ["EXPLAINED", "explain", "page_names"]

Page = tuple[str, str]  # (title, address)
Pages = Mapping[int, Page]

_DAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")

_PHP_DATE = {
    "d": "%d", "j": "%-d", "D": "%a", "l": "%A", "N": "%u", "w": "%w", "m": "%m", "n": "%-m",
    "F": "%B", "M": "%b", "Y": "%Y", "y": "%y", "a": "%p", "A": "%p", "g": "%-I", "G": "%-H",
    "h": "%I", "H": "%H", "i": "%M", "s": "%S",
}  # fmt: skip

#: A fixed moment, so an example reads the same every time: 9 November 2026, 14:05.
_SAMPLE = time.struct_time((2026, 11, 9, 14, 5, 0, 0, 313, 0))


def _sample(php: str) -> str:
    """*php* (WordPress's date format) applied to a fixed day, so a person hears the result."""
    out = []
    for char in php:
        code = _PHP_DATE.get(char)
        if code is None:
            out.append(char)
            continue
        text = time.strftime(code.replace("%-", "%"), _SAMPLE)
        text = text.lower() if char == "a" else text
        out.append(text.lstrip("0") if code.startswith("%-") and text != "0" else text)
    return "".join(out)


def _page(value: Any, pages: Pages) -> tuple[str, str]:
    number = int(value or 0)
    if not number:
        return "", ""
    title, link = pages.get(number, ("", ""))
    return title or f"page {number}", link


def _show_on_front(v: Any, s: Mapping[str, Any], p: Pages, url: str) -> str:
    if v == "page":
        title, link = _page(s.get("page_on_front"), p)
        where = f" ({link})" if link else ""
        return f"Your home page is a page you chose, {title or 'not yet chosen'}{where}."
    return f"Your home page, {url or 'the site address'}, lists your latest posts."


def _front(v: Any, s: Mapping[str, Any], p: Pages, url: str) -> str:
    title, link = _page(v, p)
    if not title:
        return "No page is chosen for the home page, so it lists your latest posts."
    if s.get("show_on_front") != "page":
        return (
            f"{title} is chosen, but Front page shows is set to your latest posts, so it is unused."
        )
    return f"{title}, so visitors arriving at {url or 'the site address'} see it first."


def _posts(v: Any, s: Mapping[str, Any], p: Pages, url: str) -> str:
    title, link = _page(v, p)
    if not title:
        return "No posts page is chosen; your posts are listed on the home page."
    return f"{title}, so visitors see your latest posts at {link or 'that page'}."


def _open(word: str) -> Callable[[Any, Mapping[str, Any], Pages, str], str]:
    def said(v: Any, _s: Mapping[str, Any], _p: Pages, _u: str) -> str:
        if v == "open":
            return f"New posts take {word} unless you turn them off on the post."
        return f"New posts take no {word} unless you turn them on on the post."

    return said


EXPLAINED: dict[str, Callable[[Any, Mapping[str, Any], Pages, str], str]] = {
    "title": lambda v, _s, _p, _u: (
        f"{v or '(none)'}: the name in the browser tab, search results and feeds."
    ),
    "description": lambda v, _s, _p, _u: (
        f"{v or 'Empty'}: the tagline many themes show under the site's name."
        if v
        else "Empty, so themes that show a tagline show nothing there."
    ),
    "language": lambda v, _s, _p, _u: (
        f"{v or 'en_US'}: the language of wp-admin and of the words WordPress writes, "
        "such as Read more."
    ),
    "timezone": lambda v, _s, _p, _u: (
        f"{v or 'UTC'}: scheduled posts go out, and dates are shown, by this clock."
    ),
    "date_format": lambda v, _s, _p, _u: f"{v}: a date reads {_sample(str(v or 'F j, Y'))}.",
    "time_format": lambda v, _s, _p, _u: f"{v}: a time reads {_sample(str(v or 'g:i a'))}.",
    "start_of_week": lambda v, _s, _p, _u: (
        f"Calendars start their week on {_DAYS[int(v or 0) % 7]}."
    ),
    "email": lambda v, _s, _p, _u: (
        f"{v}: where WordPress sends notices meant for whoever runs the site. Changing it "
        "sends a confirmation there first."
    ),
    "show_on_front": _show_on_front,
    "page_on_front": _front,
    "page_for_posts": _posts,
    "posts_per_page": lambda v, _s, _p, _u: (
        f"{v}: the posts page and archives show {v} posts, then a link to older ones."
    ),
    "default_comment_status": _open("comments"),
    "default_ping_status": _open("pingbacks from other blogs"),
    "use_smilies": lambda v, _s, _p, _u: (
        "Typed :-) becomes a picture, which a screen reader names by its alt text."
        if v
        else "Typed :-) stays as text, the way a screen reader reads it best."
    ),
    "default_post_format": lambda v, _s, _p, _u: (
        f"New posts start as the {v or 'standard'} format, which some themes style differently."
    ),
    "site_icon": lambda v, _s, _p, _u: (
        f"Picture {v} is the small icon in browser tabs and bookmarks."
        if v
        else "No site icon, so browser tabs show their default."
    ),
}
"""One explanation per setting the Settings list shows (``site_admin.SETTINGS_FIELDS``)."""


def explain(
    key: str,
    settings: Mapping[str, Any],
    *,
    pages: Pages | None = None,
    site_url: str = "",
) -> str:
    """What *key* does on this site, with its own value as the example ("" if unknown)."""
    said = EXPLAINED.get(key)
    if said is None:
        return ""
    return said(settings.get(key), settings, pages or {}, site_url.rstrip("/"))


def page_names(api: WordPressApi, settings: Mapping[str, Any]) -> dict[int, Page]:
    """The titles and addresses of the front and posts pages; ``{}`` if neither is set."""
    ids = sorted({int(settings.get(k) or 0) for k in ("page_on_front", "page_for_posts")} - {0})
    if not ids:
        return {}
    try:
        raw = api.get("wp/v2/pages", include=ids, _fields="id,title,link")
    except WordPressApiError:
        return {}
    found: dict[int, Page] = {}
    for page in raw if isinstance(raw, list) else []:
        if isinstance(page, dict):
            title = page.get("title")
            text = title.get("rendered", "") if isinstance(title, dict) else str(title or "")
            found[int(page.get("id", 0) or 0)] = (str(text), str(page.get("link", "") or ""))
    return found
