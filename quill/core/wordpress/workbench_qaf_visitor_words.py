"""The words visitors read on QUILL Accessible Forms' forms, per site (PRD D5, 13a; WP-R-050).

What a visitor reads when a form is sent, when it needs another look, when a
text challenge is asked, answered wrongly or replaced, and when a form the
checks doubted is held for a person to read (the Held as Spam confirmation),
editable for each site and for each language the site offers.

**The route.** QAF's own settings route for spam (``qaf/v1/spam``) takes only
its listed settings, and no route of QAF's carries these words yet, so QUILL
asks for one, named for what it holds: ``qaf/v1/visitor-words``.

- ``GET qaf/v1/visitor-words?language=fr_FR``: ``{"language", "languages",
  "words": {key: text}, "defaults": {key: text}, "revision", "can_edit"}``;
  a word the site has not changed comes back as its default.
- ``POST qaf/v1/visitor-words``: ``{"language", "words": {key: text},
  "if_revision"}``. Only the words sent change; an empty text puts QAF's own
  words back; a stale ``if_revision`` answers 409.

A QAF without the route answers 404 (``rest_no_route``), and
:func:`read_words` says so in a sentence rather than failing. Every save is
read again first (the conflict check), sent, and read back (the verify).
Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.workbench.actions import ActionRow, Tier

__all__ = [
    "MAX_CHARS",
    "QAF_WORDS_ROWS",
    "ROUTE",
    "WORDS",
    "VisitorWords",
    "WordsConflict",
    "check_text",
    "no_route_sentence",
    "read_words",
    "save_words",
    "word_line",
    "words_preview",
]

ROUTE = "visitor-words"
MAX_CHARS = 300


@dataclass(frozen=True)
class Word:
    """One thing a visitor reads: its key on the site, its name here, and QUILL's suggestion."""

    key: str
    label: str
    suggestion: str


#: In the order a visitor meets them.
WORDS: tuple[Word, ...] = (
    Word("form_success", "After a form is sent", "Thank you. Your answers were sent."),
    Word(
        "form_errors",
        "When answers need another look",
        "Some answers need another look. Each one is listed below with what to change.",
    ),
    Word("form_required", "A question left empty", "Please answer this question."),
    Word(
        "form_failed",
        "When sending fails",
        "Your answers were not sent, because something went wrong. Please try again.",
    ),
    Word("challenge_intro", "Before a text challenge", "One more question before this is sent."),
    Word(
        "challenge_send_anyway",
        "Offering Send Anyway",
        "You can also send it as it is: a person will read it first.",
    ),
    Word(
        "challenge_wrong",
        "A challenge answered wrongly",
        "That answer did not match. Here is another question; take as long as you like.",
    ),
    Word("challenge_empty", "A challenge left empty", "Please answer the question below."),
    Word(
        "challenge_expired",
        "A challenge replaced",
        "That question was replaced to keep the form safe. Here is a new one.",
    ),
    Word(
        "held_confirmation",
        "Held as Spam confirmation",
        "Thank you. Your message was kept for a person to read before it goes any further. "
        "There is nothing more you need to do.",
    ),
)
_BY_KEY = {w.key: w for w in WORDS}

QAF_WORDS_ROWS: tuple[ActionRow, ...] = (
    ActionRow(
        "wordpress.workbench.visitor_words",
        "Visitor Words for Forms...",
        Tier.WRITE,
        "",
        "What visitors read on QUILL Accessible Forms' forms on this site: after sending, "
        "when an answer needs another look, around a text challenge, and when a form is held "
        "for a person to read. Change one, in any language the site offers, after a preview.",
    ),
)


class WordsConflict(WordPressApiError):
    """The visitor words changed on the site after they were read; nothing was sent."""

    code = "QUILL-WORDPRESS-QAF-WORDS-CONFLICT"


@dataclass(frozen=True)
class VisitorWords:
    """The words as the site holds them, in one language."""

    language: str
    languages: tuple[str, ...]
    words: Mapping[str, str]
    defaults: Mapping[str, str]
    revision: str
    can_edit: bool

    def text(self, key: str) -> str:
        return self.words.get(key) or self.defaults.get(key, "")

    def changed(self, key: str) -> bool:
        return bool(self.words.get(key)) and self.words.get(key) != self.defaults.get(key)


def no_route_sentence() -> str:
    return (
        "This site's QUILL Accessible Forms has no route for visitor words yet "
        "(qaf/v1/visitor-words), so they cannot be changed from QUILL. They come with the "
        "plugin until it is updated."
    )


def _strings(raw: Any) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        return {}
    return {str(k): str(v) for k, v in raw.items() if isinstance(v, str)}


def read_words(api: Any, namespace: str, language: str = "") -> VisitorWords | None:
    """The words in *language* (the site's own when empty); None when QAF has no such route."""
    params = {"language": language} if language else {}
    try:
        found = api.get(f"{namespace}/{ROUTE}", **params)
    except WordPressApiError as exc:
        if exc.status == 404:
            return None
        raise
    if not isinstance(found, Mapping):
        return None
    languages = found.get("languages")
    return VisitorWords(
        language=str(found.get("language", language) or language),
        languages=tuple(str(n) for n in languages) if isinstance(languages, list) else (),
        words=_strings(found.get("words")),
        defaults=_strings(found.get("defaults")),
        revision=str(found.get("revision", "")),
        can_edit=bool(found.get("can_edit", False)),
    )


def word_line(held: VisitorWords, key: str) -> str:
    word = _BY_KEY[key]
    own = "" if held.changed(key) else " (the plugin's own words)"
    return f"{word.label}: {held.text(key)}{own}"


def check_text(text: str) -> str:
    """Why *text* cannot be a visitor's words ("" when it can): plain words, not too long."""
    if "<" in text or ">" in text:
        return "Visitor words are plain text, so they cannot hold < or >."
    if len(text) > MAX_CHARS:
        return f"That is {len(text)} characters; visitor words are kept to {MAX_CHARS}."
    return ""


def words_preview(held: VisitorWords, key: str, text: str, site: str) -> list[str]:
    word = _BY_KEY[key]
    becomes = text or f"the plugin's own words again: {held.defaults.get(key, '')}"
    return [
        f"On {site}, in {held.language or 'the site language'}: {word.label}.",
        f"Was: {held.text(key)}",
        f"Becomes: {becomes}",
    ]


def save_words(api: Any, namespace: str, held: VisitorWords, key: str, text: str) -> str:
    """Read again, send, read back; the sentence to say. :class:`WordsConflict` sends nothing."""
    now = read_words(api, namespace, held.language)
    if now is None or now.revision != held.revision:
        raise WordsConflict(
            "The visitor words were changed on the site since they were read, so nothing was "
            "sent. Open Visitor Words for Forms again to see them as they are now.",
            status=409,
        )
    body = {"language": held.language, "words": {key: text}, "if_revision": held.revision}
    try:
        api.post(f"{namespace}/{ROUTE}", body)
    except WordPressApiError as exc:
        if exc.status == 409:
            raise WordsConflict(
                "Somebody changed the visitor words at the same moment, so nothing was saved.",
                status=409,
            ) from None
        raise
    after = read_words(api, namespace, held.language)
    wanted = text or held.defaults.get(key, "")
    label = _BY_KEY[key].label
    if after is None or after.text(key) != wanted:
        return f"The site took the change to {label}, but reading it back, it does not show it."
    if not text:
        return f"{label} is back to the plugin's own words, and read back from the site."
    return f"Saved {label}, and read it back from the site."
