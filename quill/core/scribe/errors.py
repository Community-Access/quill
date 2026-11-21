"""Every way Scribe for Documents can fail, as coded errors (PRD section 11).

Each error keeps the server's own sentence in :attr:`ScribeError.message`,
because Scribe writes its messages for people to read and in the language the
client asked for. ``str(error)`` adds the QUILL code in brackets (the
:class:`~quill.core.error_codes.CodedError` contract); that form belongs in
Copy Details and the log, never in speech -- the sentences in
:mod:`quill.core.scribe.sentences` speak :attr:`message`.

wx-free.
"""

from __future__ import annotations

from quill.core.error_codes import CodedError

#: Said when the server answered with something that is not its JSON envelope.
GENERIC_MESSAGE = "Something went wrong. Please try again."


class ScribeError(CodedError):
    """A Scribe failure with a sentence fit to show (``server_error`` and others)."""

    code = "QUILL-SCRIBE-FAILED"

    def __init__(self, message: str = GENERIC_MESSAGE, *, reason: str = "") -> None:
        super().__init__(message)
        self.message = message or GENERIC_MESSAGE
        #: The server's own code (``needs_purchase``, ``rate_limited``...), for logs.
        self.reason = reason


class ScribeSignInError(ScribeError):
    """The sign-in has ended (``unauthenticated``, ``invalid_grant``, refresh failed)."""

    code = "QUILL-SCRIBE-SIGNIN"


class ScribeSignInLocalError(ScribeError):
    """The browser did not open or the loopback port could not be used."""

    code = "QUILL-SCRIBE-SIGNIN-LOCAL"


class ScribePagesError(ScribeError):
    """The account is out of pages (``needs_purchase``)."""

    code = "QUILL-SCRIBE-PAGES"

    def __init__(
        self, message: str = GENERIC_MESSAGE, *, reason: str = "", purchase_url: str = ""
    ) -> None:
        super().__init__(message, reason=reason)
        self.purchase_url = purchase_url


class ScribePasswordError(ScribeError):
    """The document needs its password, or the one given was refused."""

    code = "QUILL-SCRIBE-PASSWORD"


class ScribeBusyError(ScribeError):
    """Scribe asked the app to slow down (``rate_limited``)."""

    code = "QUILL-SCRIBE-BUSY"


class ScribeGoneError(ScribeError):
    """The document is no longer in the account (``not_found``, ``forbidden``)."""

    code = "QUILL-SCRIBE-GONE"


class ScribeNotDocumentError(ScribeError):
    """Not a type Scribe takes: a web page or another kind of file (``not_a_document``).

    Normally caught before upload (:mod:`quill.core.scribe.inputs`)."""

    code = "QUILL-SCRIBE-NOTDOC"


class ScribeTooBigError(ScribeError):
    """Over Scribe's 500 MB upload limit; checked before upload, nothing is sent."""

    code = "QUILL-SCRIBE-TOOBIG"


class ScribeOfflineError(ScribeError):
    """The network dropped, or Scribe could not be reached."""

    code = "QUILL-SCRIBE-OFFLINE"


class ScribeSaveError(ScribeError):
    """A download could not be written: disk full, or the folder is not writable."""

    code = "QUILL-SCRIBE-SAVE"


class ScribeOffError(ScribeError):
    """Safe Mode, or no client ID: a Scribe command was chosen and nothing is queued."""

    code = "QUILL-SCRIBE-OFF"


class ScribeInProgressError(ScribeError):
    """Another conversion of this document is running: wait, never shown as an error."""

    code = "QUILL-SCRIBE-IN-PROGRESS"


class ScribeNotCompleteError(ScribeError):
    """A download was asked for before its format finished converting."""

    code = "QUILL-SCRIBE-NOT-COMPLETE"


class ScribeCancelled(ScribeError):
    """The person stopped QUILL waiting (Cancel Waiting, Cancel in a dialog)."""

    code = "QUILL-SCRIBE-CANCELLED"


def error_from_server(
    reason: str, message: str | None = None, *, purchase_url: str = "", status: int = 0
) -> ScribeError:
    """The coded error for a server ``reason`` (REST ``error.code`` or channel reason)."""
    text = (message or "").strip() or GENERIC_MESSAGE
    key = (reason or "").strip()
    if key in {"unauthenticated", "invalid_grant", "invalid_token"} or status == 401:
        return ScribeSignInError(text, reason=key)
    if key == "needs_purchase":
        return ScribePagesError(text, reason=key, purchase_url=purchase_url)
    if key in {"password_required", "invalid_password"}:
        return ScribePasswordError(text, reason=key)
    if key == "rate_limited" or status == 429:
        return ScribeBusyError(text, reason=key)
    if key in {"not_found", "forbidden"} or status in {403, 404}:
        return ScribeGoneError(text, reason=key)
    if key == "not_a_document":
        return ScribeNotDocumentError(text, reason=key)
    if key == "conversion_in_progress":
        return ScribeInProgressError(text, reason=key)
    if key == "conversion_not_complete":
        return ScribeNotCompleteError(text, reason=key)
    return ScribeError(text, reason=key or "server_error")


__all__ = [
    "GENERIC_MESSAGE",
    "ScribeBusyError",
    "ScribeCancelled",
    "ScribeError",
    "ScribeGoneError",
    "ScribeInProgressError",
    "ScribeNotCompleteError",
    "ScribeNotDocumentError",
    "ScribeOffError",
    "ScribeOfflineError",
    "ScribePagesError",
    "ScribePasswordError",
    "ScribeSaveError",
    "ScribeSignInError",
    "ScribeSignInLocalError",
    "ScribeTooBigError",
    "error_from_server",
]
