"""What can go wrong with a cloud speech provider, as a sentence (D-31, GATE-EC).

Every failure a provider reports is one of these, and each carries the **name
of the field** to look at when there is one (``field="Key"``), so the Speech
Providers page can say "The key was refused. Check Key." and put the focus
there. The sentence (``args[0]``) never contains a key, a token or anything the
person typed into a secret field.

wx-free.
"""

from __future__ import annotations

from quill.core.error_codes import CodedError

__all__ = [
    "CloudAuthError",
    "CloudConsentError",
    "CloudFieldError",
    "CloudNetworkError",
    "CloudQuotaError",
    "CloudSpeechError",
    "CloudUnsupportedError",
    "said",
]


class CloudSpeechError(CodedError):
    """A cloud speech provider did not turn speech into text."""

    code = "QUILL-DICTATION-CLOUD-FAILED"
    user_hint = (
        "Check the provider in Dictation Settings, Speech Providers, or choose a "
        "built-in engine, which needs no internet connection."
    )

    def __init__(self, message: str, *, field: str = "") -> None:
        super().__init__(message)
        #: The label of the field to check ("Key", "Region"), or "".
        self.field = field

    @property
    def fatal(self) -> bool:
        """Whether dictation stops rather than trying the next phrase."""
        return True


class CloudAuthError(CloudSpeechError):
    """The provider refused the key, token or account."""

    code = "QUILL-DICTATION-CLOUD-AUTH"


class CloudFieldError(CloudSpeechError):
    """A field is missing or cannot be right (before anything is sent)."""

    code = "QUILL-DICTATION-CLOUD-FIELD"


class CloudNetworkError(CloudSpeechError):
    """The provider could not be reached, or the connection was lost."""

    code = "QUILL-DICTATION-CLOUD-NETWORK"

    @property
    def fatal(self) -> bool:
        # A hiccup costs one phrase; dictation keeps listening. It never moves
        # to another engine by itself (the sticky-model rule).
        return False


class CloudQuotaError(CloudSpeechError):
    """The account is out of credit, over its limit, or sending too fast."""

    code = "QUILL-DICTATION-CLOUD-QUOTA"


class CloudUnsupportedError(CloudSpeechError):
    """This copy of QUILL cannot talk to the provider that way (a missing part)."""

    code = "QUILL-DICTATION-CLOUD-UNSUPPORTED"


class CloudConsentError(CloudSpeechError):
    """The person has not agreed that their speech may go to this provider."""

    code = "QUILL-DICTATION-CLOUD-CONSENT"


def said(error: BaseException) -> str:
    """The sentence, without the error code in front."""
    return str(error.args[0]) if error.args else str(error)
