"""What can go wrong with a ChatGPT subscription, each with its own code.

Five branches, because the five need five different next steps and a person
hearing the sentence cannot open the failing request to see which one it was.
Each carries a ``user_hint`` naming the concrete thing to do, in the same
shape as :mod:`quill.core.ai.gateway_errors` (GATE-EC).

wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.error_codes import CodedError

__all__ = [
    "ChatGptError",
    "ChatGptLimitError",
    "ChatGptSignInError",
    "ChatGptSignedOutError",
    "ChatGptUnavailableError",
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


class ChatGptUnavailableError(ChatGptError):
    """OpenAI says plan usage from other apps is not available right now."""

    code = "QUILL-AI-CHATGPT-UNAVAILABLE"
    user_hint = (
        "Using a ChatGPT plan from other apps is not available on this account "
        "just now. Try again later, or use QUILL's free AI or your own OpenAI key."
    )
