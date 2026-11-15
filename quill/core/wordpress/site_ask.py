"""Ask About This Site: a question answered from the site's own content (PRD 15.11).

Ask the Site first used a site's abilities (:mod:`quill.core.wordpress.abilities`),
which only WordPress 6.9 sites with abilities turned on have. Any site can
instead be asked about what it says: :func:`read_content` reads its recent
posts and pages, :func:`content_digest` turns them into plain text under a
cap, and :func:`ask_prompt` puts the question and that text to the chosen AI.

Consent is in two steps, both the person's: published content is sent only
after a confirm naming the site, how many items, and the AI it goes to
(:func:`consent_message`); drafts, pending and private items are read only
when the person checks that they may be included, because they are not
public and the AI provider will see them.

Wx-free; reads go through the site's own client, off the UI thread.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import raw_text, rendered

__all__ = [
    "MAX_CHARS",
    "MAX_ITEMS",
    "PER_ITEM",
    "Digest",
    "ask_prompt",
    "consent_message",
    "content_digest",
    "read_content",
]

MAX_ITEMS = 60
"""At most this many posts and pages are read, newest first."""
MAX_CHARS = 60_000
"""The whole digest is kept under this many characters."""
PER_ITEM = 2_500
"""Each item's text is cut to this many characters."""

_PUBLIC = "publish"
_NOT_PUBLIC = "draft,pending,private,future"


@dataclass
class Digest:
    """The text sent, and how many items went in and were left out."""

    text: str
    included: int
    left_out: int
    private: int = 0
    unread: list[str] = field(default_factory=list)


def read_content(
    api: WordPressApi, *, include_private: bool, limit: int = MAX_ITEMS
) -> tuple[list[Mapping[str, Any]], list[str]]:
    """Recent posts and pages, newest first, and the lists the site would not give."""
    statuses = f"{_PUBLIC},{_NOT_PUBLIC}" if include_private else _PUBLIC
    params: dict[str, Any] = {
        "status": statuses,
        "orderby": "modified",
        "order": "desc",
        "_fields": "id,type,title,status,link,modified,content,excerpt",
    }
    if include_private:
        params["context"] = "edit"
    found: list[Mapping[str, Any]] = []
    unread: list[str] = []
    for route in ("wp/v2/posts", "wp/v2/pages"):
        try:
            found += list(api.iter_collection(route, params, per_page=min(limit, 100), max_pages=1))
        except WordPressApiError as exc:
            unread.append(f"{route}: {exc.plain or exc}")
    found.sort(key=lambda r: str(r.get("modified", "")), reverse=True)
    return found[:limit], unread


def _text(raw: Mapping[str, Any]) -> str:
    content = raw.get("content")
    text = rendered(content) if isinstance(content, Mapping) else str(content or "")
    if not text.strip() and isinstance(content, Mapping) and content.get("raw"):
        text = rendered({"rendered": content["raw"]})
    return " ".join(text.split())


def content_digest(
    items: Sequence[Mapping[str, Any]],
    *,
    max_chars: int = MAX_CHARS,
    per_item: int = PER_ITEM,
    unread: Sequence[str] = (),
) -> Digest:
    """Each item as a titled block of plain text, newest first, within the caps."""
    blocks: list[str] = []
    used = 0
    private = 0
    for raw in items:
        title = raw_text(raw.get("title")) or rendered(raw.get("title")) or f"#{raw.get('id')}"
        status = str(raw.get("status", "") or "")
        kind = "page" if raw.get("type") == "page" else "post"
        body = _text(raw)
        if len(body) > per_item:
            body = body[:per_item].rsplit(" ", 1)[0] + " (cut short)"
        head = f"## {title} ({kind}, {status or 'publish'}"
        if raw.get("link"):
            head += f", {raw['link']}"
        head += ")"
        block = f"{head}\n{body}"
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block) + 2
        if status and status != _PUBLIC:
            private += 1
    return Digest("\n\n".join(blocks), len(blocks), len(items) - len(blocks), private, list(unread))


def ask_prompt(site: str, question: str, digest: Digest) -> str:
    """The question, grounded in the digest, asking for an answer that names its pages."""
    left = (
        f" {digest.left_out} more items were not included, so say when the answer may be "
        "incomplete."
        if digest.left_out
        else ""
    )
    return (
        f"You are answering a question about the WordPress site {site}, using only the site "
        f"content below: its {digest.included} most recently changed posts and pages, as "
        f"plain text.{left} Name the post or page each part of your answer comes from. If the "
        "content does not answer the question, say so plainly; do not guess.\n\n"
        f"Question: {question.strip()}\n\nSite content:\n\n{digest.text}"
    )


def consent_message(site: str, ai_name: str, digest: Digest) -> str:
    """What the confirm says before anything is sent."""
    said = (
        f"Send the text of {digest.included} posts and pages from {site} with your question to "
        f"{ai_name}?"
    )
    if digest.private:
        said += (
            f" {digest.private} of them are not public (drafts, pending, scheduled or private), "
            "and the AI provider will see them."
        )
    else:
        said += " Only published content is included."
    if digest.unread:
        said += f" Not read: {'; '.join(digest.unread)}."
    return said
