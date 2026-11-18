"""Writing a GitHub comment well, by ear (GH-C, GitHub PRD section 22).

The Workbench's comment composer uses these. Nothing here shows a picture of
the comment; everything is said:

* :func:`mention_candidates` and :func:`reference_candidates` are the people
  and the issues and pull requests the composer offers to insert, so an
  ``@login`` or ``#42`` is chosen from a list rather than typed from memory;
* :func:`saved_replies` are the account's own saved replies on GitHub;
* :func:`spoken_preview` reads the comment as GitHub will show it, line by
  line, saying what each line is (a heading, a task, a quote, code) and what
  an image or a link stands for, so a listener knows the layout without a
  browser;
* :func:`accessibility_findings` is the optional check before posting: an
  image without a description, a link that says "click here", a heading that
  skips a level, a long run of capital letters, and a comment that is only an
  emoji;
* GitHub has no API for attaching a file to a comment, so the composer says
  so (:data:`ATTACHMENTS_SENTENCE`) instead of offering a button that cannot
  work.

wx-free and strict-typed; every request goes through the Workbench's
:class:`~quill.core.github.workbench_api.GitHubApi`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "ATTACHMENTS_SENTENCE",
    "Reference",
    "SavedReply",
    "accessibility_findings",
    "mention_candidates",
    "reference_candidates",
    "saved_replies",
    "spoken_preview",
]

ATTACHMENTS_SENTENCE = (
    "GitHub has no way for another program to attach a file to a comment. Put "
    "the file somewhere people can reach, such as a release or a gist, and "
    "paste its link; or attach it on github.com."
)


# -- people, issues and saved replies -------------------------------------------


def mention_candidates(
    api: GitHubApi, repository: str, *, already: Iterable[str] = (), limit: int = 100
) -> list[str]:
    """Logins worth mentioning: the conversation's people first, then who may be assigned."""
    found: list[str] = []
    for login in already:
        if login and login not in found:
            found.append(login)
    try:
        answer = api.rest(
            "GET", f"/repos/{repository}/assignees", query={"per_page": str(limit)}
        ).data
    except Exception:  # noqa: BLE001 - the conversation's own people still help
        answer = []
    for row in answer if isinstance(answer, list) else []:
        login = str((row or {}).get("login") or "")
        if login and login not in found:
            found.append(login)
    return found[:limit]


@dataclass(frozen=True)
class Reference:
    number: int
    title: str
    is_pull: bool
    state: str

    @property
    def label(self) -> str:
        kind = "pull request" if self.is_pull else "issue"
        return f"#{self.number}, {self.title} ({self.state} {kind})"


def reference_candidates(api: GitHubApi, repository: str, words: str) -> list[Reference]:
    """Issues and pull requests in *repository* whose title has *words*, or #number itself."""
    words = words.strip().lstrip("#")
    query = f"repo:{repository} {words} in:title" if not words.isdigit() else ""
    if words.isdigit():
        try:
            row = api.rest("GET", f"/repos/{repository}/issues/{int(words)}").data
        except Exception:  # noqa: BLE001 - no such number is an empty list
            return []
        rows = [row] if isinstance(row, dict) else []
    else:
        data = api.rest("GET", "/search/issues", query={"q": query, "per_page": "30"}).data
        rows = list((data or {}).get("items") or []) if isinstance(data, dict) else []
    return [
        Reference(
            int(row.get("number") or 0),
            str(row.get("title") or ""),
            "pull_request" in row,
            str(row.get("state") or ""),
        )
        for row in rows
        if row.get("number")
    ]


@dataclass(frozen=True)
class SavedReply:
    title: str
    body: str


_SAVED_REPLIES = "query{viewer{savedReplies(first:100){nodes{title body}}}}"


def saved_replies(api: GitHubApi) -> list[SavedReply]:
    """The account's saved replies, as GitHub keeps them (Settings > Saved replies)."""
    data = api.graphql(_SAVED_REPLIES, {})
    nodes = ((data.get("viewer") or {}).get("savedReplies") or {}).get("nodes") or []
    return [
        SavedReply(str(node.get("title") or ""), str(node.get("body") or ""))
        for node in nodes
        if node
    ]


# -- reading it before it is sent ---------------------------------------------------

_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]*)[^)]*\)")
_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]*)[^)]*\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_TASK = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s+(.*)$")
_BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
_NUMBERED = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
_QUOTE = re.compile(r"^\s*>\s?(.*)$")
_EMPHASIS = re.compile(r"(\*\*|__|\*|_|~~)(?=\S)(.+?)(?<=\S)\1")
_CODE_SPAN = re.compile(r"`([^`]+)`")
_MENTION = re.compile(r"(?<![\w@])@([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))")
_ISSUE_REF = re.compile(r"(?<![\w&/])((?:[\w.-]+/[\w.-]+)?#\d+)\b")


def _inline(text: str) -> str:
    """One line's inline markup in words: images and links said, emphasis dropped."""
    text = _IMAGE.sub(
        lambda m: f"[image: {m[1].strip()}]" if m[1].strip() else "[image with no description]",
        text,
    )
    text = _LINK.sub(lambda m: f"{m[1]} [link]", text)
    text = _CODE_SPAN.sub(lambda m: m[1], text)
    text = _EMPHASIS.sub(lambda m: m[2], text)
    return text


def spoken_preview(text: str) -> list[str]:
    """The comment as lines to read: what each line is, then its words."""
    lines: list[str] = []
    fence: list[str] | None = None
    for raw in text.replace("\r\n", "\n").split("\n"):
        stripped = raw.strip()
        if stripped.startswith(("```", "~~~")):
            if fence is None:
                fence = []
                language = stripped.strip("`~").strip()
                lines.append(f"Code block{', ' + language if language else ''}:")
            else:
                lines.append(f"End of code, {len(fence)} lines.")
                fence = None
            continue
        if fence is not None:
            fence.append(raw)
            lines.append(raw)
            continue
        if not stripped:
            continue
        if match := _HEADING.match(stripped):
            lines.append(f"Heading {len(match[1])}: {_inline(match[2])}")
        elif match := _TASK.match(raw):
            lines.append(f"{'Done' if match[1] != ' ' else 'Not done'}: {_inline(match[2])}")
        elif match := _BULLET.match(raw):
            lines.append(f"Bullet: {_inline(match[1])}")
        elif match := _NUMBERED.match(raw):
            lines.append(f"{match[1]}. {_inline(match[2])}")
        elif match := _QUOTE.match(raw):
            lines.append(f"Quote: {_inline(match[1])}")
        elif set(stripped) <= {"-", "*", "_", " "} and len(stripped.replace(" ", "")) >= 3:
            lines.append("Line across.")
        else:
            lines.append(_inline(stripped))
    if fence is not None:
        lines.append("The code block is never closed: GitHub shows the rest as code.")
    mentions = sorted(set(_MENTION.findall(_without_code(text))), key=str.casefold)
    refs = sorted(set(_ISSUE_REF.findall(_without_code(text))))
    if mentions:
        lines.append("Mentions, who GitHub will notify: " + ", ".join(f"@{m}" for m in mentions))
    if refs:
        lines.append("Refers to: " + ", ".join(refs))
    return lines


def _without_code(text: str) -> str:
    kept: list[str] = []
    fenced = False
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.strip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(_CODE_SPAN.sub("", line))
    return "\n".join(kept)


_VAGUE_LINKS = {"here", "click here", "this", "link", "this link", "more", "read more"}
_VAGUE_ALT = {"image", "picture", "photo", "screenshot", "img", "graphic"}
_SHOUTING = re.compile(r"\b(?:[A-Z]{2,}\b[\s,.!?]*){4,}")
_EMOJI_ONLY = re.compile(r"^[\s:\w+-]*$")


def accessibility_findings(text: str) -> list[str]:
    """What might trip a reader, each as a sentence; empty when nothing did."""
    plain = _without_code(text)
    found: list[str] = []
    for alt, url in _IMAGE.findall(plain):
        name = url.rsplit("/", 1)[-1] or url
        description = alt.strip()
        if not description:
            found.append(f"The image {name} has no description; put one between the [ ].")
        elif description.casefold() in _VAGUE_ALT or description == name:
            found.append(
                f"The image described as {description!r} needs words saying what it shows."
            )
    for words, _url in _LINK.findall(plain):
        if words.strip().casefold() in _VAGUE_LINKS:
            found.append(f"A link says {words.strip()!r}; say where it goes instead.")
    level = 0
    for line in plain.split("\n"):
        match = _HEADING.match(line.strip())
        if match:
            new = len(match[1])
            if level and new > level + 1:
                found.append(
                    f"The heading {match[2]!r} jumps from level {level} to {new}; "
                    "a screen reader's list of headings will look like something is missing."
                )
            level = new
    if _SHOUTING.search(plain):
        found.append(
            "A long run of capital letters is read letter by letter by some screen readers."
        )
    stripped = plain.strip()
    if stripped and _is_only_emoji(stripped):
        found.append(
            "The comment is only an emoji; a screen reader says its name, "
            "which may not be what you mean."
        )
    return found


def _is_only_emoji(text: str) -> bool:
    without_shortcodes = re.sub(r":[a-z0-9_+-]+:", "", text)
    letters = [ch for ch in without_shortcodes if not ch.isspace()]
    if not letters and text != without_shortcodes:
        return True
    return bool(letters) and all(not ch.isascii() and not ch.isalnum() for ch in letters)


def joined(lines: Sequence[str]) -> str:
    """The preview as one block of text for a read-only box."""
    return "\n".join(lines)
