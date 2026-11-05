"""Check the Whole Site's report, its history, and the writing helpers (wordpress.md 9.5-9.12).

- :func:`group_problems` turns every page's findings into the report "by
  problem": "Images with no alt text: 41, on 17 pages".
- :class:`CheckHistory` keeps each run's date and counts, per site, on this
  computer, so a writer can say "41 problems in March, 6 now".
- :func:`accessibility_statement` writes the plain statement draft (9.12).
- :func:`palette_from_global_styles` reads the theme's palette for the
  Palette Report (9.7).
- :func:`mark_language` and :func:`insert_in_short` are Mark Language and the
  In Short block (9.11), in the form each document format needs.

Stdlib only, no wx.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.checks import Finding
from quill.core.wordpress.site_fixes import SAFE_FIXES

__all__ = [
    "CheckHistory",
    "HistoryEntry",
    "PageRef",
    "SiteProblem",
    "accessibility_statement",
    "group_problems",
    "insert_in_short",
    "language_name",
    "mark_language",
    "palette_from_global_styles",
    "site_summary",
    "valid_language",
]

#: Finding kind -> the report's group label.
_GROUP_LABELS: dict[str, str] = {
    "title-empty": "Pages with no title",
    "image-no-alt": "Images with no alt text",
    "image-empty-alt": "Images with empty alt text not marked decorative",
    "alt-is-filename": "Alt text that is a file name",
    "alt-says-image": 'Alt text that starts "Image of"',
    "animated-gif": "GIFs that may move",
    "video-autoplay": "Videos that play by themselves",
    "linked-image-no-alt": "Linked images with no alt text",
    "link-no-text": "Links with no text",
    "link-text-is-address": "Links whose text is the web address",
    "link-vague-text": 'Links that say only "click here" or "read more"',
    "link-new-tab-unsaid": "Links that open a new tab without saying so",
    "link-has-emoji": "Links with emoji or symbols",
    "heading-1-in-body": "Heading 1s in the body",
    "heading-skips-level": "Headings that skip a level",
    "heading-has-emoji": "Headings with emoji or symbols",
    "table-no-header": "Tables with no header row",
    "table-no-caption": "Tables with no caption",
    "colour-alone": "Words set apart only by colour",
}

_SKIP_KINDS = frozenset({"site-not-default"})


@dataclass(frozen=True)
class PageRef:
    kind: str
    item_id: int
    title: str
    link: str = ""


@dataclass
class SiteProblem:
    key: str
    label: str
    owner: str  # "content" or "theme"
    count: int = 0
    pages: list[PageRef] = field(default_factory=list)

    @property
    def fixable(self) -> bool:
        return self.key in SAFE_FIXES

    def row(self) -> str:
        pages = len(self.pages)
        on = f"on {pages} page" + ("" if pages == 1 else "s")
        owner = "" if self.owner == "content" else ", in the theme or a plugin"
        fix = ", can be fixed in bulk" if self.fixable else ""
        return f"{self.label}: {self.count}, {on}{owner}{fix}"


def group_problems(
    content: Iterable[tuple[PageRef, list[Finding]]],
    visitor: Iterable[tuple[PageRef, list[tuple[str, str, str, int]]]] = (),
) -> list[SiteProblem]:
    """The report by problem, most frequent first.

    *visitor* carries what axe-core found on each page as
    ``(rule, label, owner, places)``; a rule is one group per owner.
    """
    groups: dict[str, SiteProblem] = {}

    def add(key: str, label: str, owner: str, page: PageRef, places: int) -> None:
        group = groups.setdefault(key, SiteProblem(key, label, owner))
        group.count += places
        if page not in group.pages:
            group.pages.append(page)

    for page, findings in content:
        for finding in findings:
            if finding.kind in _SKIP_KINDS:
                continue
            label = _GROUP_LABELS.get(finding.kind, finding.message.rstrip("."))
            add(finding.kind, label, "content", page, 1)
    for page, rules in visitor:
        for rule, label, owner, places in rules:
            add(f"axe:{rule}:{owner}", label, owner, page, places)
    return sorted(groups.values(), key=lambda g: (-g.count, g.label))


# --------------------------------------------------------------------------- #
# History


@dataclass
class HistoryEntry:
    date: str
    pages: int
    problems: int
    groups: dict[str, int] = field(default_factory=dict)
    theme_problems: list[str] = field(default_factory=list)
    visitor_checked: bool = False

    @property
    def month(self) -> str:
        try:
            return datetime.fromisoformat(self.date).strftime("%B %Y")
        except ValueError:
            return self.date


class CheckHistory:
    """Each Check the Whole Site run, per site, newest first."""

    LIMIT = 60

    def __init__(self, root: Path) -> None:
        self.root = root / "site_checks"

    def _path(self, site_id: str) -> Path:
        return self.root / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', site_id)}.json"

    def load(self, site_id: str) -> list[HistoryEntry]:
        raw = read_json(self._path(site_id), default=[])
        entries: list[HistoryEntry] = []
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, dict):
                known = {k: v for k, v in item.items() if k in HistoryEntry.__dataclass_fields__}
                entries.append(HistoryEntry(**known))
        return entries

    def latest(self, site_id: str) -> HistoryEntry | None:
        entries = self.load(site_id)
        return entries[0] if entries else None

    def add(self, site_id: str, entry: HistoryEntry) -> None:
        entries = [entry, *self.load(site_id)][: self.LIMIT]
        write_json_atomic(self._path(site_id), [asdict(e) for e in entries])


def history_entry(
    problems: list[SiteProblem], pages: int, *, visitor_checked: bool, now: datetime | None = None
) -> HistoryEntry:
    when = (now or datetime.now(UTC)).replace(microsecond=0)
    return HistoryEntry(
        date=when.isoformat(),
        pages=pages,
        problems=sum(p.count for p in problems),
        groups={p.label: p.count for p in problems},
        theme_problems=[p.label for p in problems if p.owner != "content"],
        visitor_checked=visitor_checked,
    )


def site_summary(
    site_name: str, problems: list[SiteProblem], pages: int, previous: HistoryEntry | None
) -> str:
    """ "Community Radio: 47 problems on 17 of 42 pages. 52 in October 2026." """
    total = sum(p.count for p in problems)
    if not total:
        line = f"{site_name}: no problems found on {pages} pages"
    else:
        affected = len({ref for p in problems for ref in p.pages})
        line = f"{site_name}: {total} problem" + ("" if total == 1 else "s")
        line += f" on {affected} of {pages} pages"
    if previous is not None:
        line += f". {previous.problems} in {previous.month}"
    return line + "."


# --------------------------------------------------------------------------- #
# An accessibility statement (9.12)


def accessibility_statement(
    site_name: str,
    *,
    contact: str,
    last: HistoryEntry | None,
    today: datetime | None = None,
    html: bool = False,
) -> tuple[str, str]:
    """The title and text of a plain statement draft, for the writer to edit."""
    date = (today or datetime.now(UTC)).strftime("%d %B %Y").lstrip("0")
    title = "Accessibility Statement"
    paras: list[str] = [
        f"We want everyone to be able to use {site_name}, including people who use a screen "
        "reader, magnification, voice control or a keyboard alone.",
        "We aim to meet the Web Content Accessibility Guidelines (WCAG) 2.2 at level AA.",
    ]
    if last is not None:
        checked = last.month
        if last.problems:
            paras.append(
                f"We last checked every page and post in {checked}. That check found "
                f"{last.problems} things to fix across {last.pages} pages, and we are working "
                "through them."
            )
        else:
            paras.append(
                f"We last checked every page and post in {checked}, and that check found no "
                "problems."
            )
    else:
        paras.append("We check our pages for accessibility problems as we write them.")
    known = (last.theme_problems if last else [])[:10]
    if known:
        paras.append(
            "Some problems come from our site's theme or plugins rather than our own writing. "
            "We have told their authors, and these are the ones we know about:"
        )
    contact_line = (
        f"If something on this site does not work for you, please tell us: {contact}. We will "
        "reply, and we will find another way to get you what you need."
        if contact.strip()
        else "If something on this site does not work for you, please tell us. We will reply."
    )
    closing = [contact_line, f"This statement was written on {date}."]
    if not html:
        body = "\n\n".join(paras)
        if known:
            body += "\n\n" + "\n".join(f"- {k}" for k in known)
        return title, body + "\n\n" + "\n\n".join(closing) + "\n"
    blocks = [_paragraph_block(p) for p in paras]
    if known:
        items = "".join(f"<li>{_escape(k)}</li>" for k in known)
        blocks.append(f"<!-- wp:list -->\n<ul>{items}</ul>\n<!-- /wp:list -->")
    blocks += [_paragraph_block(p) for p in closing]
    return title, "\n\n".join(blocks) + "\n"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _paragraph_block(text: str, css: str = "") -> str:
    if css:
        return (
            f'<!-- wp:paragraph {{"className":"{css}"}} -->\n'
            f'<p class="{css}">{text}</p>\n<!-- /wp:paragraph -->'
        )
    return f"<!-- wp:paragraph -->\n<p>{_escape(text)}</p>\n<!-- /wp:paragraph -->"


# --------------------------------------------------------------------------- #
# The Palette Report's colours (9.7)

_VAR_RE = re.compile(r"var(?::preset\|color\||\(--wp--preset--color--)([\w-]+)\)?")


def palette_from_global_styles(raw: Any) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """``(palette, backgrounds)`` from a ``global-styles`` answer.

    The palette is the theme's and the site's own colours. Backgrounds are the
    page background first, then every palette colour, because any of them can
    sit behind text in a block.
    """
    settings = raw.get("settings", {}) if isinstance(raw, dict) else {}
    colour = settings.get("color", {}) if isinstance(settings, dict) else {}
    palette_raw = colour.get("palette", []) if isinstance(colour, dict) else []
    entries: list[Any] = []
    if isinstance(palette_raw, dict):
        for origin in ("theme", "custom"):
            entries += palette_raw.get(origin, []) or []
        if not entries:
            entries = palette_raw.get("default", []) or []
    elif isinstance(palette_raw, list):
        entries = palette_raw
    palette: list[tuple[str, str]] = []
    by_slug: dict[str, str] = {}
    for entry in entries:
        if isinstance(entry, dict) and entry.get("color"):
            name = str(entry.get("name") or entry.get("slug") or "")
            palette.append((name, str(entry["color"])))
            by_slug[str(entry.get("slug", ""))] = str(entry["color"])
    backgrounds = list(palette)
    styles = raw.get("styles", {}) if isinstance(raw, dict) else {}
    page = styles.get("color", {}).get("background", "") if isinstance(styles, dict) else ""
    if isinstance(page, str) and page:
        match = _VAR_RE.search(page)
        value = by_slug.get(match.group(1), "") if match else page
        if value and all(value != c for _n, c in backgrounds):
            backgrounds.insert(0, ("Page background", value))
        elif value:
            index = next(i for i, (_n, c) in enumerate(backgrounds) if c == value)
            backgrounds.insert(0, backgrounds.pop(index))
    return palette, backgrounds


# --------------------------------------------------------------------------- #
# Mark Language and In Short (9.11)

_LANG_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_LANGUAGE_NAMES = {
    "ar": "Arabic",
    "cy": "Welsh",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "ga": "Irish",
    "he": "Hebrew",
    "hi": "Hindi",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "la": "Latin",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "sv": "Swedish",
    "uk": "Ukrainian",
    "zh": "Chinese",
}
_NAME_TO_CODE = {name.casefold(): code for code, name in _LANGUAGE_NAMES.items()}
_BLOCK_ELEMENT_RE = re.compile(
    r"(<(p|h[1-6]|li|figcaption|td|th|cite|dt|dd)\b[^>]*>)(.*?)(</\2\s*>)",
    re.IGNORECASE | re.DOTALL,
)
# Markdown lines that are not prose: raw HTML and block islands, fences,
# tables and rules. A span there would break them.
_MD_LEAVE_ALONE = ("<", "```", "~~~", ":::", "|", "---", "***")
_MD_LEAD_RE = re.compile(r"^(\s*(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+|>\s*)*)(.*)$")


def valid_language(answer: str) -> str:
    """A language tag from what the person typed ("fr", "French", "pt-BR"), or ""."""
    text = answer.strip()
    if text.casefold() in _NAME_TO_CODE:
        return _NAME_TO_CODE[text.casefold()]
    return text if _LANG_RE.match(text) else ""


def language_name(tag: str) -> str:
    return _LANGUAGE_NAMES.get(tag.split("-", 1)[0].lower(), tag)


def _span(tag: str, text: str) -> str:
    return f'<span lang="{tag}">{text}</span>'


def mark_language(text: str, tag: str, *, html: bool, whole: bool = False) -> str:
    """*text* marked as language *tag*, in the form WordPress keeps.

    A span is what the block editor's own Language format writes, so it lives
    inside a block's text and never breaks the block. A single line becomes
    one span; several lines or a whole page get one span inside each paragraph,
    heading or list item (HTML), or after each line's Markdown markers.
    """
    if "\n" not in text.strip() and not whole:
        return _span(tag, text) if text.strip() else text
    if html:
        if _BLOCK_ELEMENT_RE.search(text) is None:
            return text if whole else _span(tag, text)
        return _BLOCK_ELEMENT_RE.sub(
            lambda m: (
                f"{m.group(1)}{_span(tag, m.group(3))}{m.group(4)}"
                if m.group(3).strip()
                else m.group(0)
            ),
            text,
        )
    lines = []
    for line in text.split("\n"):
        match = _MD_LEAD_RE.match(line)
        lead, rest = (match.group(1), match.group(2)) if match else ("", line)
        if not rest.strip() or rest.lstrip().startswith(_MD_LEAVE_ALONE):
            lines.append(line)
            continue
        lines.append(f"{lead}{_span(tag, rest)}")
    return "\n".join(lines)


IN_SHORT_CLASS = "quill-in-short"
_IN_SHORT_BLOCK_RE = re.compile(
    r"\A\s*<!--\s*wp:paragraph\s*\{[^}]*" + IN_SHORT_CLASS + r"[^}]*\}\s*-->.*?"
    r"<!--\s*/wp:paragraph\s*-->\s*",
    re.DOTALL,
)
_IN_SHORT_MD_RE = re.compile(r"\A\s*\*\*In short:\*\*[^\n]*(?:\n(?!\n)[^\n]*)*\n*")


def insert_in_short(text: str, summary: str, *, html: bool) -> str:
    """*text* with an "In short" paragraph at the top, replacing an earlier one."""
    words = " ".join(summary.split())
    if html:
        block = _paragraph_block(f"<strong>In short:</strong> {_escape(words)}", IN_SHORT_CLASS)
        rest = _IN_SHORT_BLOCK_RE.sub("", text, count=1)
        return f"{block}\n\n{rest.lstrip()}"
    rest = _IN_SHORT_MD_RE.sub("", text, count=1)
    return f"**In short:** {words}\n\n{rest.lstrip()}"


def in_short_prompt(title: str, text: str) -> str:
    return (
        "Summarise this web page in two or three short, plain sentences for a reader in a "
        "hurry or one who finds long text hard. Use everyday words. Return only the "
        f"sentences, with no heading and no list.\n\nTitle: {title}\n\n{text}"
    )
