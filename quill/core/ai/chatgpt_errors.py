"""What can go wrong with a ChatGPT subscription, each with its own code.

Six branches, because the six need five different next steps and a person
hearing the sentence cannot open the failing request to see which one it was.
Each carries a ``user_hint`` naming the concrete thing to do, in the same
shape as :mod:`quill.core.ai.gateway_errors` (GATE-EC).

wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.error_codes import CodedError

__all__ = [
    "ChatGptBusyError",
    "ChatGptError",
    "ChatGptLimitError",
    "ChatGptSignInError",
    "ChatGptSignedOutError",
    "ChatGptUnavailableError",
    "ChatGptUnsupportedError",
    "ChatGptUsageUnavailableError",
]


class ChatGptError(CodedError):
    """A request on the ChatGPT subscription did not produce an answer."""

    code = "QUILL-AI-CHATGPT-FAILED"
    user_hint = (
        "Check the model in Use My ChatGPT Subscription, or sign in again there. "
        "Your ChatGPT plan's own usage page says whether the plan is available."
    )


class ChatGptSignInError(ChatGptError):
    """Continue with ChatGPT did not finish: refused, timed out, or the answer
    from OpenAI was not one QUILL can trust."""

    code = "QUILL-AI-CHATGPT-SIGNIN"
    user_hint = "Choose Continue with ChatGPT again, and finish in the browser this time."


class ChatGptSignedOutError(ChatGptError):
    """OpenAI no longer accepts this computer's sign-in.

    The refresh token was revoked, expired, or the plan changed under it.
    Locally the account is forgotten the moment this is raised, so the next
    sign-in starts clean rather than retrying a dead credential.
    """

    code = "QUILL-AI-CHATGPT-SIGNED-OUT"
    user_hint = (
        "Choose Use My ChatGPT Subscription in the AI menu and Continue with "
        "ChatGPT to sign in again."
    )


class ChatGptLimitError(ChatGptError):
    """The ChatGPT plan's usage for this period is used up."""

    code = "QUILL-AI-CHATGPT-LIMIT"
    user_hint = (
        "Your ChatGPT plan's usage limit has been reached for now. Open ChatGPT "
        "Usage in Use My ChatGPT Subscription to see when it resets, or wait and "
        "try again later."
    )


class ChatGptBusyError(ChatGptLimitError):
    """A plain 429 with no plan code: OpenAI asking for a moment, not a used-up plan.

    A subclass of the limit error so every caller that already handles a limit
    still does; Choose Your AI tells the two apart, because only the plan's
    own limit is "your limit is reached" (codex.md 10A.5)."""

    code = "QUILL-AI-CHATGPT-BUSY"
    user_hint = "OpenAI asked QUILL to wait a moment. Try again shortly."


class ChatGptUnavailableError(ChatGptError):
    """OpenAI says plan usage from other apps is not available right now."""

    code = "QUILL-AI-CHATGPT-UNAVAILABLE"
    user_hint = (
        "Using a ChatGPT plan from other apps is not available on this account "
        "just now. Try again later, or use QUILL's free AI or your own API key."
    )


class ChatGptUsageUnavailableError(ChatGptUnavailableError):
    """``subscription_sharing_usage_unavailable``: the plan's usage could not be
    checked. Retried within the shared ladder, then said like a limit (10A.5)."""

    code = "QUILL-AI-CHATGPT-USAGE-UNAVAILABLE"


class ChatGptUnsupportedError(ChatGptError):
    """The plan does not take something in the request: an input, a tool or a model.

    OpenAI's guidance is to remove the item rather than resend the same body, so
    this is final: nothing retries it and nothing routes it elsewhere."""

    code = "QUILL-AI-CHATGPT-UNSUPPORTED"
    user_hint = (
        "ChatGPT plans used from other apps do not take this kind of request. "
        "Nothing was retried; use an AI provider with your own key for it instead."
    )
