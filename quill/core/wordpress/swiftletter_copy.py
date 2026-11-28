"""A SwiftLetter article as an editor working copy, and what is said about it.

The editor's WordPress documents are :class:`~quill.core.wordpress.local.WorkingCopy`
files (wordpress.md 5.1); a SwiftLetter article is one more, of kind
:data:`KIND`, whose ``properties["swiftletter"]`` holds what SwiftLetter's save
needs: the ``edit_version`` for ``If-Match`` and the title and content the site
holds, so the next save describes text QUILL really has (Michael's answer 4).

The round trip (Michael's answer 13): an article opens as HTML exactly as the
site has it, or as Markdown through :mod:`quill.core.wordpress.fences`, which
converts nothing on trust and keeps every block it cannot write back exactly.
Before a Markdown save, anything that cannot be turned back into blocks stops
the save, says why, and leaves the Markdown draft as it is.

Nothing here publishes: a SwiftLetter save is always a draft. Wx-free and
network-free; the editor side is :mod:`quill.ui.wordpress_swiftletter_commands`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress import fences
from quill.core.wordpress import local as lc
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.swiftletter import Article, SavedArticle, review_words
from quill.core.wordpress.swiftletter_errors import SwiftLetterError

__all__ = [
    "COMPARE",
    "KEPT",
    "KIND",
    "NEVER_PUBLISHES",
    "REOPEN",
    "Outgoing",
    "Refusal",
    "adopt_site",
    "article_of",
    "can_save",
    "compare_report",
    "copy_for",
    "is_article",
    "markdown_problem",
    "nothing_changed",
    "opened_words",
    "outgoing",
    "record_saved",
    "refusal",
    "reopened_words",
    "saved_words",
    "set_can_edit",
    "tidied_only",
    "with_kept",
    "wordpress_void_tags",
]

#: The working copy's kind. Not a REST base, so the editor's generic post commands
#: (Properties, Trash, Publish) can never write to the article behind SwiftLetter's back.
KIND = "swiftletter"
_STATE = "swiftletter"

KEPT = "Your copy in QUILL is unchanged."

NEVER_PUBLISHES = (
    "QUILL saves SwiftLetter articles as drafts only, and never publishes them. Save Draft to "
    "Site sends your changes; the newsletter is published from SwiftLetter."
)

#: kses writes a void element's close as `` />``; the block editor writes ``/>``.
_VOID_CLOSE = re.compile(r"(<(?:img|hr|br|input|source|wbr)\b[^<>]*?)\s+/>", re.I)


def wordpress_void_tags(content: str) -> str:
    """*content* with void tags closed the way the block editor writes them.

    WordPress's kses tidies ``"/>`` into ``" />`` when it stores a contributor's
    text (the contract's ``reopen-shows-saved-draft-changed-since-review``). The two
    mean the same, but only the first is one :mod:`fences` can show as Markdown, so
    a picture saved once would otherwise open as an opaque ``::: block`` line,
    its alt text out of reach.
    """
    return _VOID_CLOSE.sub(r"\1/>", content)


def tidied_only(sent: str, stored: str) -> bool:
    """Whether the stored text differs from what was sent only in kses's void-tag spacing."""
    return sent != stored and wordpress_void_tags(sent) == wordpress_void_tags(stored)


def is_article(copy: lc.WorkingCopy | None) -> bool:
    return copy is not None and copy.kind == KIND


def _state(copy: lc.WorkingCopy) -> dict[str, Any]:
    state = copy.properties.get(_STATE)
    return state if isinstance(state, dict) else {}


def markdown_problem(content: str) -> str:
    """Why *content* cannot open as Markdown, or "" when it can.

    Opening converts it and converts the result straight back: anything that does
    not come back byte for byte is a reason to open it as HTML only, so a save
    from Markdown can never change a block nobody edited.
    """
    markdown, islands = fences.post_to_markdown(content)
    result = fences.convert_markdown(markdown, islands)
    if result.problems:
        return f"Line {result.problems[0].line}: {result.problems[0].message}"
    if result.html.strip() != content.strip():
        return "QUILL could not turn every block into Markdown and back without changing it."
    return ""


def copy_for(
    site_id: str,
    article: Article,
    *,
    text_format: str,
    can_edit: bool,
    newsletter_title: str = "",
) -> lc.WorkingCopy:
    """The working copy for *article*, opened as ``"html"`` or ``"markdown"``."""
    content = wordpress_void_tags(article.content)
    text, islands = content, dict[str, str]()
    if text_format == "markdown":
        text, islands = fences.post_to_markdown(content)
    return lc.WorkingCopy(
        site_id=site_id,
        kind=KIND,
        local_id=lc.new_local_id(),
        remote_id=article.id,
        title=article.title,
        text=text,
        text_format=text_format,
        properties={
            "islands": islands,
            _STATE: {
                "site_url": article.site_url,
                "edit_version": article.edit_version,
                "review_state": article.review_state,
                "newsletter_ids": list(article.newsletter_ids),
                "newsletter_title": newsletter_title,
                "can_edit": can_edit,
                "title": article.title,
                "content": article.content,
            },
        },
        status="draft",
    )


def can_save(copy: lc.WorkingCopy) -> bool:
    return _state(copy).get("can_edit") is not False


def set_can_edit(copy: lc.WorkingCopy, allowed: bool) -> None:
    """Follow the site's latest hint about whether this account may edit the article."""
    copy.properties[_STATE] = {**_state(copy), "can_edit": allowed}


def adopt_site(copy: lc.WorkingCopy, fresh: lc.WorkingCopy) -> None:
    """Reopen: *copy* takes *fresh*'s text, islands and baseline (the site's article),
    keeping every other property it had and what it knew beside the baseline."""
    copy.properties = {
        **copy.properties,
        "islands": fresh.properties.get("islands") or {},
        _STATE: {
            **_state(copy),
            **{k: v for k, v in _state(fresh).items() if k != "newsletter_title"},
            "can_edit": can_save(copy),
        },
    }
    copy.title = fresh.title
    copy.text = fresh.text


def article_of(copy: lc.WorkingCopy) -> Article:
    """The article as the site last held it: what the next save's ``If-Match`` describes."""
    state = _state(copy)
    version = state.get("edit_version")
    return Article(
        site_url=str(state.get("site_url") or ""),
        id=copy.remote_id,
        title=str(state.get("title") or ""),
        content=str(state.get("content") or ""),
        newsletter_ids=tuple(int(i) for i in state.get("newsletter_ids") or ()),
        review_state=str(state.get("review_state") or "not_reviewed"),
        edit_version=version if isinstance(version, str) else None,
    )


@dataclass(frozen=True)
class Outgoing:
    """What a save would send, or why it must not be sent."""

    html: str
    problems: tuple[str, ...] = ()

    @property
    def blocked(self) -> str:
        """The sentence that stops the save, or "" when it may go."""
        if not self.problems:
            return ""
        count = len(self.problems)
        lines = "line" if count == 1 else "lines"
        return (
            f"Not saved to SwiftLetter: {count} {lines} could not be turned into WordPress "
            f"blocks without losing something. {self.problems[0]} Your Markdown draft is "
            "unchanged; fix the line, or open the article as HTML."
        )


def outgoing(copy: lc.WorkingCopy) -> Outgoing:
    """The block markup a save sends: the HTML as written, or the Markdown converted."""
    if copy.text_format == "html":
        return Outgoing(copy.text)
    result = fences.convert_markdown(copy.text, copy.properties.get("islands") or {})
    return Outgoing(result.html, tuple(f"Line {p.line}: {p.message}" for p in result.problems))


def nothing_changed(copy: lc.WorkingCopy, html: str) -> bool:
    """Whether a save would send what the site already has (kses spacing aside)."""
    base = article_of(copy)
    return copy.title == base.title and wordpress_void_tags(html.strip()) == wordpress_void_tags(
        base.content.strip()
    )


def record_saved(copy: lc.WorkingCopy, saved: SavedArticle) -> None:
    """After a save: the stored text becomes the baseline, and the person's copy stays.

    A reviewed article whose title or body changed reads Changed since review
    (Michael's answers 5 and 6); SwiftLetter does not write a save that changes nothing.
    """
    state = dict(_state(copy))
    before = article_of(copy)
    after = saved.baseline(before)
    if state.get("review_state") == "reviewed":
        state["review_state"] = "changed"
    state.update(
        edit_version=after.edit_version, title=after.title, content=after.content, saved_before=True
    )
    if saved.stored_differs and tidied_only(saved.sent_content, saved.stored_content or ""):
        state["tidy_said"] = True
    copy.properties[_STATE] = state


def opened_words(article: Article, site: str, *, can_edit: bool, can_save_here: bool) -> str:
    """Said once the article is in the editor: its title, its review state, and any limit."""
    title = article.title or "Untitled article"
    words = f"Opened {title} from SwiftLetter on {site}. {review_words(article.review_state)}."
    if not can_edit:
        words += " Your account cannot edit this article, so it opened read-only."
    elif not can_save_here:
        words += " This site's SwiftLetter does not take saves from QUILL, so it opened read-only."
    return words


def reopened_words(copy: lc.WorkingCopy) -> str:
    """Said when a working copy already on this computer opens instead of the site's."""
    state = _state(copy)
    review = review_words(str(state.get("review_state") or "not_reviewed"))
    return (
        f"Opened your working copy of {copy.title or 'this article'} on this computer, not the "
        f"site's copy. It was {review.lower()} when you last opened or saved it. Compare with "
        "Site, on the WordPress menu, shows what changed on the site since."
    )


def saved_words(copy: lc.WorkingCopy, saved: SavedArticle, site: str) -> str:
    """One outcome for a save, naming the site; built before :func:`record_saved`.

    The part that needs the person comes first: when WordPress kept something other
    than what was sent, it says so and keeps their copy. A difference that is only
    kses's tidying of a tag is said the first time for this working copy, not after
    every save (it would be every save, and it changes nothing a reader sees).
    "It is not published" is said on the first save of a working copy only.
    """
    state = _state(copy)
    tidy = tidied_only(saved.sent_content, saved.stored_content or "") and not saved.title_changed
    if saved.stored_differs and not tidy:
        words = (
            f"Draft saved to SwiftLetter on {site}, but WordPress changed the text as it saved "
            "it; Compare with Site shows how. Your copy in QUILL is unchanged."
        )
    else:
        words = f"Draft saved to SwiftLetter on {site}."
        if not state.get("saved_before"):
            words += " It is not published."
    if state.get("review_state") == "reviewed":
        words += " Its review state is now Changed since review."
    if saved.stored_differs and tidy and not state.get("tidy_said"):
        words += (
            " WordPress tidied the markup as it saved it, such as the spacing in an image tag. "
            "Nothing a reader sees changed, and your copy in QUILL is unchanged."
        )
    return words


@dataclass(frozen=True)
class Refusal:
    """SwiftLetter's refusal as the editor says it, and what it offers next."""

    words: str
    offers: tuple[str, ...] = ()


COMPARE = "Compare with Site"
REOPEN = "Reopen"


def refusal(exc: BaseException, *, site: str = "the site") -> Refusal:
    """SwiftLetter's own sentence, and the offers its ``next_step`` names.

    412 (stale) offers Compare with Site and Reopen; a refusal that needs the
    article read again offers Reopen; a lock, and everything else, offers nothing,
    because QUILL never retries by itself (Michael's answers 2, 3 and 10). A
    failure that is not WordPress's answer at all is one plain sentence, never a
    Python exception's text.
    """
    if isinstance(exc, SwiftLetterError):
        said = exc.plain
        step = exc.next_step
        if step == "compare":
            return Refusal(said, (COMPARE, REOPEN))
        if step == "reopen":
            return Refusal(said, (REOPEN,))
        return Refusal(said)
    if isinstance(exc, WordPressApiError) and exc.plain:
        return Refusal(exc.plain)
    return Refusal(f"QUILL could not reach SwiftLetter on {site}, so nothing was saved.")


def with_kept(words: str) -> str:
    """*words*, then that the person's copy is safe, unless they already say so
    (SwiftLetter's own sentences often end "Your changes are still in QUILL.")."""
    if "still in QUILL" in words or "unchanged" in words:
        return words
    return f"{words} {KEPT}"


def compare_report(site: Article, copy: lc.WorkingCopy, mine: str, render: Any) -> str:
    """The title line, then *render* (the editor's Diff Line Marks compare) of the content."""
    if site.title == copy.title:
        title = f"Title: the same on the site and in your copy ({site.title or 'untitled'})."
    else:
        title = (
            f"Title on the site: {site.title or 'untitled'}. "
            f"Your title: {copy.title or 'untitled'}."
        )
    review = f"On the site it is {review_words(site.review_state).lower()}."
    site_text = wordpress_void_tags(site.content)
    return f"{title}\n{review}\n\n{render(site_text, wordpress_void_tags(mine))}"
