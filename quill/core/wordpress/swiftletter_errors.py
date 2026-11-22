"""SwiftLetter's refusals as QUILL coded errors, each saying SwiftLetter's own sentence.

SwiftLetter writes every refusal's ``message`` to be read aloud as it is
(Michael's answer 10, 2026-11-22), so QUILL says that sentence and never the
code. The code only decides which error class it becomes, and so what QUILL
offers next (:attr:`SwiftLetterError.next_step`). When a refusal carries no
sentence, the class's own :attr:`~SwiftLetterError.fallback` is said instead.

Nothing here ever retries a request. Wx-free and network-free.
"""

from __future__ import annotations

from typing import ClassVar

from quill.core.wordpress.api import WordPressApiError

__all__ = [
    "SwiftLetterArticleLocked",
    "SwiftLetterArticleUnavailable",
    "SwiftLetterConflict",
    "SwiftLetterError",
    "SwiftLetterForbidden",
    "SwiftLetterInvalidSave",
    "SwiftLetterInvalidVersion",
    "SwiftLetterSaveUnavailable",
    "SwiftLetterVersionError",
    "SwiftLetterVersionRequired",
    "coded_refusal",
]

_KEPT = "Your changes are still in QUILL."


class SwiftLetterError(WordPressApiError):
    """SwiftLetter refused a request, or answered in a shape QUILL cannot read."""

    code = "QUILL-SWIFTLETTER-API-REQUEST"
    fallback: ClassVar[str] = "SwiftLetter refused the request. Refresh and try again."
    #: What the editor offers after this refusal: "compare" (Compare with Site),
    #: "reopen" (open the article again before saving), or "" (nothing more).
    next_step: ClassVar[str] = ""


class SwiftLetterVersionError(SwiftLetterError):
    """The site's SwiftLetter speaks a connection version this QUILL does not know."""

    code = "QUILL-SWIFTLETTER-API-VERSION"


class SwiftLetterForbidden(SwiftLetterError):
    """The person's account may not do this in SwiftLetter (``swiftletter_forbidden``, 403)."""

    code = "QUILL-SWIFTLETTER-API-FORBIDDEN"
    fallback = "Your account is not allowed to edit this article in SwiftLetter."


class SwiftLetterVersionRequired(SwiftLetterError):
    """A save without the article's version (``swiftletter_version_required``, 428)."""

    code = "QUILL-SWIFTLETTER-API-VERSION-REQUIRED"
    fallback = f"SwiftLetter needs the article's version to save it. Reopen it first. {_KEPT}"
    next_step = "reopen"


class SwiftLetterInvalidVersion(SwiftLetterError):
    """A save whose version SwiftLetter cannot read (``swiftletter_invalid_version``, 400)."""

    code = "QUILL-SWIFTLETTER-API-INVALID-VERSION"
    fallback = f"SwiftLetter could not read the article's version. Reopen it first. {_KEPT}"
    next_step = "reopen"


class SwiftLetterInvalidSave(SwiftLetterError):
    """A save SwiftLetter will not take as sent (``swiftletter_invalid_save``, 400)."""

    code = "QUILL-SWIFTLETTER-API-INVALID-SAVE"
    fallback = f"SwiftLetter takes only an article's title and content. {_KEPT}"


class SwiftLetterArticleUnavailable(SwiftLetterError):
    """The article is gone or no longer editable (``swiftletter_article_unavailable``, 404)."""

    code = "QUILL-SWIFTLETTER-API-ARTICLE-UNAVAILABLE"
    fallback = f"This article is no longer available to edit in SwiftLetter. {_KEPT}"


class SwiftLetterConflict(SwiftLetterError):
    """The article changed on the site since it was opened (``swiftletter_precondition_failed``,
    412). The save was not sent; Compare with Site reads the current article."""

    code = "QUILL-SWIFTLETTER-API-CONFLICT"
    fallback = (
        "Someone changed this article on the site. Your local copy was not sent. "
        "Compare it with the current article before trying again."
    )
    next_step = "compare"


class SwiftLetterArticleLocked(SwiftLetterError):
    """Someone else has the article open in WordPress (409, ``swiftletter_article_locked``).

    Its sentence names who, in SwiftLetter's words. QUILL never retries by itself.
    """

    code = "QUILL-SWIFTLETTER-API-ARTICLE-LOCKED"
    fallback = f"Someone else is editing this article in WordPress, so it was not saved. {_KEPT}"


class SwiftLetterSaveUnavailable(SwiftLetterError):
    """The site cannot save safely just now (``swiftletter_save_unavailable``, 503)."""

    code = "QUILL-SWIFTLETTER-API-SAVE-UNAVAILABLE"
    fallback = f"This site could not save the article safely, so nothing changed. {_KEPT}"


#: SwiftLetter's code, without its ``swiftletter_`` prefix -> the QUILL error it becomes.
BY_CODE: dict[str, type[SwiftLetterError]] = {
    "version_required": SwiftLetterVersionRequired,
    "invalid_version": SwiftLetterInvalidVersion,
    "invalid_save": SwiftLetterInvalidSave,
    "article_unavailable": SwiftLetterArticleUnavailable,
    "forbidden": SwiftLetterForbidden,
    "precondition_failed": SwiftLetterConflict,
    "article_locked": SwiftLetterArticleLocked,
    "save_unavailable": SwiftLetterSaveUnavailable,
}

#: When a refusal sends no code QUILL knows, its HTTP status still says which it is.
_BY_STATUS: dict[int, type[SwiftLetterError]] = {
    409: SwiftLetterArticleLocked,
    412: SwiftLetterConflict,
    428: SwiftLetterVersionRequired,
}


def _said(body: object) -> str:
    """SwiftLetter's ``message``, exactly as written, or "" when it sent none."""
    if isinstance(body, dict):
        message = body.get("message")
        if isinstance(message, str):
            return message.strip()
    return ""


def coded_refusal(exc: WordPressApiError, *, saving: bool = False) -> WordPressApiError:
    """*exc* as the SwiftLetter error its code names, carrying SwiftLetter's sentence.

    A refusal whose code QUILL does not know stays WordPress's own error, with
    its plain sentence. *saving* lets a save's 409, 412 and 428 be known by
    status alone, for a site that sends no code.
    """
    if isinstance(exc, SwiftLetterError):
        return exc
    body = exc.body if isinstance(exc.body, dict) else None
    reason = (exc.wp_code or str((body or {}).get("code") or "")).removeprefix("swiftletter_")
    kind = BY_CODE.get(reason)
    if kind is None and saving and not reason.startswith("rest_"):
        kind = _BY_STATUS.get(exc.status)
    if kind is None:
        return exc
    return kind(_said(body) or kind.fallback, status=exc.status, wp_code=exc.wp_code, body=exc.body)
