"""The Accessibility Assistant (PRD 21.5).

Pure heuristics -- no model -- that inspect a draft or an item and report
accessibility problems the author can still fix: missing alt text, filename-like
descriptions, ambiguous links, emoji-only meaning, unexplained acronyms, all-caps
passages, media without a transcript, images that likely carry substantial text,
unclear polls, and threads that lose context after splitting (PRD 21.5).

Each detector returns :class:`A11yIssue` records with a severity and a concrete
suggestion, and each fires on a crafted positive while staying quiet on clean
input. The entry points :func:`check_draft` and :func:`check_item` run every
applicable detector. Wx-free, no I/O, no randomness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill_social.model import Draft, Media, Poll, SocialItem
from quill_social.services.thread_splitter import split_thread

SEVERITIES = ("info", "warning", "error")

_FILENAME_RE = re.compile(
    r"^\s*(?:img|dsc|dscn|pxl|photo|image|screenshot|scan)[ _-]?\d+"
    r"|\.(?:jpe?g|png|gif|webp|heic|bmp|tiff?|mp4|mov|mp3|wav)\s*$",
    re.IGNORECASE,
)
_AMBIGUOUS_LINKS = (
    "click here",
    "read more",
    "here",
    "this link",
    "link",
    "more",
    "this",
    "learn more",
)
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,}(?:s)?\b")
_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U00002600-\U000027bf"
    "\U0001f1e6-\U0001f1ff"
    "←-⇿⬀-⯿"
    "]"
)
# Common acronyms most readers know -- not worth flagging (kept small on purpose).
_ACRONYM_ALLOWLIST = frozenset(
    "US USA UK EU UN AI ML API URL HTML CSS PDF FAQ CEO OK TV PM AM GIF HTTP "
    "HTTPS RSS DM ID OS PC IT HR OMG LOL".split()
)
# Words that, when a non-first thread segment starts with them, signal lost
# context after a split (a dangling pronoun or continuation).
_CONTINUATION_STARTS = frozenset(
    "it its they them this that these those which who and but so because however "
    "therefore also then he she his her their".split()
)


@dataclass
class A11yIssue:
    """One accessibility finding with a fix suggestion (PRD 21.5)."""

    kind: str
    severity: str
    message: str
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, d: dict) -> A11yIssue:
        return cls(
            kind=d.get("kind", ""),
            severity=d.get("severity", "warning"),
            message=d.get("message", ""),
            suggestion=d.get("suggestion", ""),
        )


# -- media detectors ----------------------------------------------------------


def check_media(media: list[Media]) -> list[A11yIssue]:
    issues: list[A11yIssue] = []
    for i, m in enumerate(media, start=1):
        where = f"attachment {i}"
        if m.kind in ("image", "gifv") and not m.has_alt:
            issues.append(
                A11yIssue(
                    "missing_alt_text",
                    "error",
                    f"{where} ({m.kind}) has no alt text.",
                    "Add a short description of what the image shows.",
                )
            )
        elif m.has_alt and _FILENAME_RE.search(m.alt_text.strip()):
            issues.append(
                A11yIssue(
                    "filename_like_description",
                    "warning",
                    f"{where} alt text looks like a filename: '{m.alt_text.strip()}'.",
                    "Describe the content, not the file name.",
                )
            )
        if m.kind in ("audio", "video") and not m.transcript.strip():
            issues.append(
                A11yIssue(
                    "media_without_transcript",
                    "error",
                    f"{where} ({m.kind}) has no transcript or captions.",
                    "Add a transcript so the content is available without sound.",
                )
            )
        if m.kind in ("image", "gifv") and _likely_text_image(m):
            issues.append(
                A11yIssue(
                    "image_with_text",
                    "warning",
                    f"{where} looks like it contains substantial text.",
                    "Put the text itself in the alt text or the post body.",
                )
            )
    return issues


def _likely_text_image(m: Media) -> bool:
    hints = ("screenshot", "screen shot", "scan", "chart", "graph", "diagram",
             "slide", "figure", "table", "infographic", "quote")
    hay = " ".join((m.uri, m.local_path, m.caption, m.alt_text)).lower()
    return any(h in hay for h in hints)


# -- text detectors -----------------------------------------------------------


def check_text(text: str) -> list[A11yIssue]:
    issues: list[A11yIssue] = []
    stripped = text.strip()
    if not stripped:
        return issues

    # Ambiguous link text: an anchor-like phrase near a URL, or a bare vague word.
    lower = stripped.lower()
    if _URL_RE.search(stripped):
        for phrase in _AMBIGUOUS_LINKS:
            if re.search(rf"\b{re.escape(phrase)}\b", lower):
                issues.append(
                    A11yIssue(
                        "ambiguous_link_text",
                        "warning",
                        f"Ambiguous link text: '{phrase}'.",
                        "Use link text that describes the destination.",
                    )
                )
                break

    # Emoji-only meaning: emoji present but no letters/digits to carry meaning.
    if _EMOJI_RE.search(stripped) and not _WORD_RE.search(stripped):
        issues.append(
            A11yIssue(
                "emoji_only_meaning",
                "warning",
                "The post relies on emoji alone to convey meaning.",
                "Add words; a screen reader announces emoji names, not intent.",
            )
        )

    # Unexplained acronyms: all-caps tokens not in the small allowlist.
    acronyms = [
        a for a in _ACRONYM_RE.findall(stripped)
        if a.rstrip("s") not in _ACRONYM_ALLOWLIST and a not in _ACRONYM_ALLOWLIST
    ]
    # Distinguish a genuine acronym from an all-caps passage handled below.
    unexplained = sorted({a for a in acronyms if len(a) <= 6})
    if unexplained and not _is_all_caps_passage(stripped):
        issues.append(
            A11yIssue(
                "unexplained_acronym",
                "info",
                f"Possibly unexplained acronym(s): {', '.join(unexplained)}.",
                "Spell out the acronym on first use.",
            )
        )

    # All-caps passages.
    if _is_all_caps_passage(stripped):
        issues.append(
            A11yIssue(
                "all_caps_passage",
                "warning",
                "A long passage is in all caps.",
                "Use sentence case; all caps reads as shouting and is harder to parse.",
            )
        )
    return issues


def _is_all_caps_passage(text: str) -> bool:
    words = [w for w in _WORD_RE.findall(text) if len(w) >= 2]
    caps = [w for w in words if w.isupper()]
    return len(caps) >= 4 and len(caps) >= len(words) * 0.6


# -- poll + thread detectors --------------------------------------------------


def check_poll(poll: Poll | None) -> list[A11yIssue]:
    if poll is None:
        return []
    titles = [o.title.strip() for o in poll.options]
    problems: list[str] = []
    if any(len(t) < 2 for t in titles):
        problems.append("an option is empty or too short to understand")
    if len({t.lower() for t in titles}) < len(titles):
        problems.append("two options are identical")
    if not problems:
        return []
    return [
        A11yIssue(
            "unclear_poll",
            "warning",
            "The poll options are unclear: " + "; ".join(problems) + ".",
            "Give each option a distinct, self-explanatory label.",
        )
    ]


def check_thread(text: str, limit: int = 500, counter=len) -> list[A11yIssue]:
    """Flag a thread that loses context once split into segments (PRD 21.5)."""
    split = split_thread(text, limit, counter=counter)
    if split.count < 2:
        return []
    issues: list[A11yIssue] = []
    for seg in split.segments[1:]:
        # Strip a leading "n/n" marker the splitter may have added.
        body = re.sub(r"\s*\d+/\d+\s*$", "", seg.text).strip()
        first = _WORD_RE.findall(body)
        if first and first[0].lower() in _CONTINUATION_STARTS:
            issues.append(
                A11yIssue(
                    "thread_loses_context",
                    "warning",
                    f"Segment {seg.index} starts with '{first[0]}', which may lose "
                    "context on its own.",
                    "Restate the subject so each post stands alone.",
                )
            )
    return issues


# -- entry points -------------------------------------------------------------


def check_draft(draft: Draft) -> list[A11yIssue]:
    """Run every applicable detector over a composed draft (PRD 21.5)."""
    issues = check_text(draft.text)
    issues += check_media(draft.media)
    issues += check_poll(draft.poll)
    if draft.thread_mode:
        issues += check_thread(draft.text)
    return issues


def check_item(item: SocialItem) -> list[A11yIssue]:
    """Run every applicable detector over a retrieved item (PRD 21.5)."""
    issues = check_text(item.text)
    issues += check_media(item.media)
    issues += check_poll(item.poll)
    return issues
