"""Coded errors for QUILL's free hosted AI (the Gateway client).

Every failure carries a stable ``QUILL-AI-GATEWAY-*`` code so a pasted message
names the exact branch, and every one of them carries a ``user_hint`` saying
what to do next. That second half matters more here than almost anywhere else
in the tree: a sighted user who runs out of free AI can see a number on a screen
and work out what happened, and a screen-reader user hears only the sentence we
wrote. "Something went wrong" is not a sentence they can act on.

Two rules run through the whole family and are worth stating before the classes:

**Never a dead end.** The free tier is a convenience on top of a product that
already works without it. Every message that refuses something points at what
still works -- a smaller passage, tomorrow, or the user's own API key.

**Never blame the user's computer for our limits.** A sign-up throttle, an
exhausted allowance and a paused service are all *our* state. A message that
reads like a fault on their machine sends somebody to reinstall QUILL over a
number we chose.
"""

from __future__ import annotations

from quill.core.error_codes import CodedError

__all__ = [
    "GatewayAuthError",
    "GatewayCertificateError",
    "GatewayError",
    "GatewayOfflineError",
    "GatewayPausedError",
    "GatewayQuotaError",
    "GatewayServiceError",
    "GatewayTooLargeError",
    "GatewayUnreachableError",
]


class GatewayError(CodedError):
    """Base for every hosted-AI failure."""

    code = "QUILL-AI-GATEWAY-FAILED"
    user_hint = (
        "Try again in a moment. If it keeps happening you can still use your own "
        "API key, or QUILL Lite works exactly as before without AI."
    )


class GatewayOfflineError(GatewayError):
    """QUILL could not reach the internet at all.

    Deliberately distinct from :class:`GatewayServiceError`: "your connection is
    down" and "our service is down" need different actions from the user, and
    guessing wrong wastes their time in opposite directions.
    """

    code = "QUILL-AI-GATEWAY-OFFLINE"
    user_hint = (
        "Check your internet connection and try again. Nothing was sent and nothing was used."
    )


class GatewayCertificateError(GatewayOfflineError):
    """The connection was made, and the service's certificate could not be verified.

    Reported as "could not reach the internet" until 2026-09-25, which sent a
    user whose internet was fine to check their internet. It is a different fact
    with different cures: a certificate authority Windows has not downloaded
    yet, or security software or a proxy that inspects HTTPS. A subclass of the
    offline error, because for every caller it means the same thing -- nothing
    was sent -- and only the sentence needs to differ.
    """

    code = "QUILL-AI-GATEWAY-CERTIFICATE"
    user_hint = (
        "If your antivirus or a work network inspects secure connections, allow "
        "QUILL through it. Otherwise run Windows Update and try again. Nothing was "
        "sent and nothing was used."
    )


class GatewayUnreachableError(GatewayOfflineError):
    """The internet may be fine; this particular service could not be reached.

    A name lookup that failed, a connection refused or reset, or no answer in
    time. Each is said separately, with the system's own reason attached,
    because "check your internet" is the wrong advice for most of them and a
    screen-reader user has no network icon to glance at instead.
    """

    code = "QUILL-AI-GATEWAY-UNREACHABLE"
    user_hint = (
        "Try again in a minute. If other sites work and this keeps happening, a "
        "firewall, VPN or proxy may be blocking the connection. Nothing was sent "
        "and nothing was used."
    )


class GatewayAuthError(GatewayError):
    """The stored token is missing, unknown or revoked.

    Raised for a 401. The cure is always the same -- connect this computer
    again -- and it is cheap, so the message says so plainly rather than
    implying something is broken.
    """

    code = "QUILL-AI-GATEWAY-SIGNED-OUT"
    user_hint = "Choose Tools, AI, Sign In to connect this computer again."


class GatewayQuotaError(GatewayError):
    """An allowance is used up: this hour's, today's, this month's, or a cost
    ceiling.

    Carries ``scope`` and ``reset_at`` so the caller can say *which* limit and
    *when* it lifts. A limit message without a time is a message that reads as
    "never", and somebody who hears "never" stops using the feature.
    """

    code = "QUILL-AI-GATEWAY-QUOTA"
    user_hint = (
        "The allowance starts again by itself. You can also add your own API key "
        "in Preferences to keep going now."
    )

    def __init__(self, message: str, *, scope: str = "", reset_at: str = "") -> None:
        super().__init__(message)
        self.scope = scope
        self.reset_at = reset_at


class GatewayTooLargeError(GatewayError):
    """The passage is bigger than the free tier accepts.

    Nothing was sent, so nothing was spent -- and the message must say so. The
    user cannot see the counter, so "this was refused" and "this cost you one of
    your hundred" are indistinguishable to them unless we distinguish them.
    """

    code = "QUILL-AI-GATEWAY-TOO-LARGE"
    user_hint = (
        "Select a shorter passage, or use your own API key for whole documents. "
        "Nothing was sent and nothing was used."
    )

    def __init__(self, message: str, *, words: int = 0, limit_words: int = 0) -> None:
        super().__init__(message)
        self.words = words
        self.limit_words = limit_words


class GatewayPausedError(GatewayError):
    """Hosted AI is switched off -- globally, or for this one feature.

    The server supplies the sentence (it knows whether this is an incident, a
    budget cap, or a feature that was never built), so this class carries it
    through rather than inventing its own.
    """

    code = "QUILL-AI-GATEWAY-PAUSED"
    user_hint = "Your own API key still works if you have one set up."


class GatewayServiceError(GatewayError):
    """The service answered, and the answer was a failure.

    A 5xx, an unparseable body, or an empty answer. Always transient from the
    user's point of view, and always free: the server refunds anything it could
    not deliver, so the message is allowed to promise that.
    """

    code = "QUILL-AI-GATEWAY-SERVICE"
    user_hint = "Try again in a moment. Nothing was used."
