"""Fix in Bulk, Site-wide Find and Replace, and Undo Site Fix (wordpress.md 9.5).

Only **safe** fixes are made in bulk: ones that need nobody's words and leave
every block valid. Each one changes a page's raw content and nothing else:

- a link that opens a new tab gets "(opens in a new tab)" in its text;
- a video stops playing by itself (``autoplay`` is an HTML attribute of the
  video block, never in its settings comment);
- an image's alt text loses a leading "Image of" (also an HTML attribute);
- a Heading 1 in the body becomes a Heading 2, with the heading block's
  ``"level":1`` setting removed so the block stays valid.

Find and Replace never touches a block's settings comment (``<!-- wp:... -->``)
unless asked, because a word replaced there can break the block.

Every change keeps the content it replaced in a :class:`SiteFix` record, on
this computer, per site, so Undo Site Fix can put it all back.

Stdlib only, no wx.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.error_codes import CodedError
from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.local import now_stamp
from quill.core.wordpress.site import kind_route, raw_text

if TYPE_CHECKING:
    from quill.core.wordpress.api import WordPressApi

__all__ = [
    "SAFE_FIXES",
    "FindOptions",
    "FixRecordStore",
    "FixedItem",
    "Match",
    "PatternError",
    "SiteFix",
    "apply_fix",
    "SitePage",
    "apply_matches",
    "fetch_items",
    "find_matches",
    "batch_outcomes",
    "update_requests",
]

#: Finding kind -> what the fix is called, for the preview and the history.
SAFE_FIXES: dict[str, str] = {
    "link-new-tab-unsaid": 'Add "(opens in a new tab)" to links that open a new tab',
    "video-autoplay": "Stop videos playing by themselves",
    "alt-says-image": 'Take "Image of" off the start of alt text',
    "heading-1-in-body": "Make Heading 1s in the body Heading 2s",
}

_NEW_TAB_TEXT = " (opens in a new tab)"
_NEW_TAB_PHRASES = ("opens in a new tab", "opens in a new window")
_LINK_RE = re.compile(r"(<a\b[^>]*>)(.*?)(</a\s*>)", re.IGNORECASE | re.DOTALL)
_TARGET_BLANK_RE = re.compile(r"""\btarget\s*=\s*["']?_blank\b""", re.IGNORECASE)
_ARIA_LABEL_RE = re.compile(r"\baria-label\s*=", re.IGNORECASE)
_VIDEO_TAG_RE = re.compile(r"<video\b[^>]*>", re.IGNORECASE)
_AUTOPLAY_RE = re.compile(
    r"""\s+autoplay(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?(?=[\s/>])""", re.IGNORECASE
)
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_ALT_RE = re.compile(r"""(\balt\s*=\s*)(["'])(.*?)\2""", re.IGNORECASE | re.DOTALL)
_REDUNDANT_ALT_RE = re.compile(
    r"^(?:an?\s+)?(?:image|picture|photo|photograph|graphic)\s+of\s+", re.IGNORECASE
)
_H1_BLOCK_RE = re.compile(r"<!--\s*wp:heading\s+(\{.*?\})\s*-->", re.DOTALL)
_H1_OPEN_RE = re.compile(r"<h1\b", re.IGNORECASE)
_H1_CLOSE_RE = re.compile(r"</h1\s*>", re.IGNORECASE)
_LEVEL_ONE_RE = re.compile(r'"level"\s*:\s*1\s*(,\s*)?')
_TAGS_RE = re.compile(r"<[^>]+>")
_BLOCK_COMMENT_RE = re.compile(r"<!--\s*/?wp:.*?-->", re.DOTALL)


class PatternError(CodedError, ValueError):
    """The Find and Replace pattern is not a valid regular expression."""

    code = "QUILL-WP-SITEFIX-BAD-PATTERN"


# --------------------------------------------------------------------------- #
# Reading and writing many pages at once

#: Everything an editor can see, never the Trash.
ALL_STATUSES = ("publish", "draft", "pending", "future", "private")


@dataclass(frozen=True)
class SitePage:
    """A page or post with its raw content, as the whole-site tools read it."""

    kind: str
    item_id: int
    title: str
    content: str
    link: str = ""
    modified_gmt: str = ""


def fetch_items(
    api: WordPressApi,
    kinds: tuple[str, ...] = ("page", "post"),
    *,
    statuses: tuple[str, ...] = ("publish",),
    search: str = "",
    ids: dict[str, list[int]] | None = None,
) -> list[SitePage]:
    """Pages and posts with their raw content (``context=edit``), page after page."""
    pages: list[SitePage] = []
    for kind in kinds:
        params: dict[str, object] = {
            "context": "edit",
            "status": list(statuses),
            "_fields": "id,type,title,content,link,modified_gmt",
        }
        if search:
            params["search"] = search
        if ids is not None:
            wanted = ids.get(kind, [])
            if not wanted:
                continue
            params["include"] = wanted
        for raw in api.iter_collection(kind_route(kind), params):
            pages.append(
                SitePage(
                    kind=kind,
                    item_id=int(raw.get("id", 0) or 0),
                    title=raw_text(raw.get("title")),
                    content=raw_text(raw.get("content")),
                    link=str(raw.get("link", "") or ""),
                    modified_gmt=str(raw.get("modified_gmt", "") or ""),
                )
            )
    return pages


def update_requests(changes: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    """``batch/v1`` entries that set each ``(kind, id, content)``."""
    return [
        {"method": "POST", "path": f"/{kind_route(kind)}/{item_id}", "body": {"content": html}}
        for kind, item_id, html in changes
    ]


def batch_outcomes(answers: list[dict[str, Any]], count: int) -> list[str]:
    """Each request's new ``modified_gmt``, or "" where it failed."""
    stamps: list[str] = []
    for index in range(count):
        answer = answers[index] if index < len(answers) else {}
        status = int(answer.get("status", 0) or 0)
        body = answer.get("body", {})
        ok = 200 <= status < 300 and isinstance(body, dict)
        stamps.append(str(body.get("modified_gmt", "") or "?") if ok else "")
    return stamps


# --------------------------------------------------------------------------- #
# The safe fixes


def _fix_new_tab(html: str) -> tuple[str, int]:
    count = 0

    def one(match: re.Match[str]) -> str:
        nonlocal count
        opening, inner, closing = match.groups()
        if not _TARGET_BLANK_RE.search(opening) or _ARIA_LABEL_RE.search(opening):
            return match.group(0)
        text = _TAGS_RE.sub("", inner).casefold()
        if any(p in text for p in _NEW_TAB_PHRASES):
            return match.group(0)
        count += 1
        return f"{opening}{inner}{_NEW_TAB_TEXT}{closing}"

    return _LINK_RE.sub(one, html), count


def _fix_autoplay(html: str) -> tuple[str, int]:
    count = 0

    def one(match: re.Match[str]) -> str:
        nonlocal count
        tag, n = _AUTOPLAY_RE.subn("", match.group(0))
        count += 1 if n else 0
        return tag

    return _VIDEO_TAG_RE.sub(one, html), count


def _fix_alt_says_image(html: str) -> tuple[str, int]:
    count = 0

    def alt(match: re.Match[str]) -> str:
        nonlocal count
        prefix, quote, value = match.groups()
        trimmed = _REDUNDANT_ALT_RE.sub("", value, count=1)
        if trimmed == value or not trimmed.strip():
            return match.group(0)
        count += 1
        return f"{prefix}{quote}{trimmed[:1].upper()}{trimmed[1:]}{quote}"

    def one(match: re.Match[str]) -> str:
        return _ALT_RE.sub(alt, match.group(0), count=1)

    return _IMG_TAG_RE.sub(one, html), count


def _fix_heading_one(html: str) -> tuple[str, int]:
    count = 0

    def settings(match: re.Match[str]) -> str:
        raw = match.group(1)
        if not re.search(r'"level"\s*:\s*1\b', raw):
            return match.group(0)
        cleaned = _LEVEL_ONE_RE.sub("", raw)
        cleaned = re.sub(r",\s*}", "}", cleaned)
        if re.fullmatch(r"\{\s*\}", cleaned):
            return "<!-- wp:heading -->"
        return f"<!-- wp:heading {cleaned} -->"

    html = _H1_BLOCK_RE.sub(settings, html)
    html, count = _H1_OPEN_RE.subn("<h2", html)
    html = _H1_CLOSE_RE.sub("</h2>", html)
    return html, count


_FIXERS = {
    "link-new-tab-unsaid": _fix_new_tab,
    "video-autoplay": _fix_autoplay,
    "alt-says-image": _fix_alt_says_image,
    "heading-1-in-body": _fix_heading_one,
}


def apply_fix(kind: str, html: str) -> tuple[str, int]:
    """The content with one safe fix made everywhere, and how many places changed."""
    fixer = _FIXERS.get(kind)
    if fixer is None:
        return html, 0
    return fixer(html)


# --------------------------------------------------------------------------- #
# Find and Replace


@dataclass(frozen=True)
class FindOptions:
    find: str
    replace: str
    regex: bool = False
    match_case: bool = False
    include_block_settings: bool = False

    def compiled(self) -> re.Pattern[str]:
        flags = 0 if self.match_case else re.IGNORECASE
        try:
            return re.compile(self.find if self.regex else re.escape(self.find), flags)
        except re.error as exc:
            raise PatternError(f"That pattern does not work: {exc}.") from exc


@dataclass(frozen=True)
class Match:
    """One place a word was found, with its sentence."""

    start: int
    end: int
    found: str
    replacement: str
    context: str


def _protected_spans(html: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _BLOCK_COMMENT_RE.finditer(html)]


def _inside(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(a <= start < b or a < end <= b for a, b in spans)


def _context(html: str, start: int, end: int, found: str) -> str:
    before = _TAGS_RE.sub(" ", html[max(0, start - 80) : start])
    after = _TAGS_RE.sub(" ", html[end : end + 80])
    before = " ".join(_BLOCK_COMMENT_RE.sub(" ", before).split())[-50:]
    after = " ".join(after.split())[:50]
    return f"...{before} [{found}] {after}...".replace("  ", " ")


def find_matches(html: str, options: FindOptions) -> tuple[list[Match], int]:
    """Every match in *html*, and how many more were left alone in block settings."""
    pattern = options.compiled()
    protected = [] if options.include_block_settings else _protected_spans(html)
    found: list[Match] = []
    hidden = 0
    for match in pattern.finditer(html):
        if match.start() == match.end():
            continue
        if _inside(protected, match.start(), match.end()):
            hidden += 1
            continue
        replacement = match.expand(options.replace) if options.regex else options.replace
        found.append(
            Match(
                match.start(),
                match.end(),
                match.group(0),
                replacement,
                _context(html, match.start(), match.end(), match.group(0)),
            )
        )
    return found, hidden


def apply_matches(html: str, matches: list[Match]) -> str:
    """*html* with each chosen match replaced, working from the end."""
    for match in sorted(matches, key=lambda m: m.start, reverse=True):
        if html[match.start : match.end] == match.found:
            html = html[: match.start] + match.replacement + html[match.end :]
    return html


# --------------------------------------------------------------------------- #
# What was changed, kept so it can be put back


@dataclass
class FixedItem:
    kind: str
    item_id: int
    title: str
    before: str
    after_modified_gmt: str = ""


@dataclass
class SiteFix:
    id: str
    site_id: str
    made: str
    label: str
    items: list[FixedItem] = field(default_factory=list)
    undone: str = ""

    def spoken(self) -> str:
        from quill.core.wordpress.site import friendly_date

        pages = len(self.items)
        what = f"{pages} page" + ("" if pages == 1 else "s")
        state = ", put back" if self.undone else ""
        return f"{friendly_date(self.made)}: {self.label}, {what}{state}"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SiteFix:
        items = [
            FixedItem(**{k: v for k, v in i.items() if k in FixedItem.__dataclass_fields__})
            for i in raw.get("items", []) or []
            if isinstance(i, dict)
        ]
        known = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__ and k != "items"}
        return cls(items=items, **known)


class FixRecordStore:
    """Site fixes, newest first, under ``<data>/wordpress/site_fixes/<site>.json``."""

    LIMIT = 30

    def __init__(self, root: Path) -> None:
        self.root = root / "site_fixes"

    def _path(self, site_id: str) -> Path:
        return self.root / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', site_id)}.json"

    def load(self, site_id: str) -> list[SiteFix]:
        raw = read_json(self._path(site_id), default=[])
        return (
            [SiteFix.from_dict(r) for r in raw if isinstance(r, dict)]
            if isinstance(raw, list)
            else []
        )

    def _write(self, site_id: str, fixes: list[SiteFix]) -> None:
        write_json_atomic(self._path(site_id), [asdict(f) for f in fixes[: self.LIMIT]])

    def add(self, fix: SiteFix) -> None:
        self._write(fix.site_id, [fix, *self.load(fix.site_id)])

    def mark_undone(self, site_id: str, fix_id: str) -> None:
        fixes = self.load(site_id)
        for fix in fixes:
            if fix.id == fix_id:
                fix.undone = now_stamp()
        self._write(site_id, fixes)
