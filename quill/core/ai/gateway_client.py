"""The one place QUILL talks to its own hosted-AI service.

Four calls, and nothing else reaches the network: ask what the limits are, ask
what is left, sign a computer in, and ask a question. Everything that decides
*whether* a request should happen -- which passage, how big, which feature --
happens before this module is reached (:mod:`quill.core.ai.gateway_context`),
and everything that decides whether it is *allowed* happens on the server, which
re-checks every limit regardless of what the client believes.

**No provider key ever passes through here.** The client holds a QUILL-issued
device token and nothing else; the real OpenAI key lives only on the gateway.
That is the entire reason the gateway exists, and it is what makes it safe for
this code to ship in an open-source client.

**One egress site** (:func:`_urlopen_json`), recorded in
:mod:`quill.tools.network_egress_entries` under GATE-9. Every call is either an
AI command the user pressed or a sign-in they started; nothing here polls, and
nothing here runs on a timer.

The device-code flow reuses :mod:`quill.core.ai.device_login` -- QUILL's
existing, already-tested RFC 8628 state machine -- rather than growing a second
one. The gateway speaks a slightly different dialect of the same flow (a
``status`` field and HTTP codes, where OAuth uses an ``error`` string), so
:func:`device_flow_poster` translates. Twenty lines of adapter against a
hundred-odd lines of polling, back-off and expiry logic that is already proven
and already has tests.
"""

from __future__ import annotations

import json
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from quill.core.ai.gateway_errors import (
    GatewayAuthError,
    GatewayCertificateError,
    GatewayError,
    GatewayOfflineError,
    GatewayPausedError,
    GatewayQuotaError,
    GatewayServiceError,
    GatewayTooLargeError,
    GatewayUnreachableError,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "Opener",
    "Poster",
    "GatewayClient",
    "GatewayLimits",
    "GatewayQuota",
    "device_flow_poster",
]

#: Where the hosted service lives. Overridable per install so a fork, a staging
#: deployment or a self-hoster needs no code change -- see
#: :func:`quill.core.ai.gateway_session.base_url`.
DEFAULT_BASE_URL = "https://ai.community-access.org"

_TIMEOUT_SECONDS = 60.0
_USER_AGENT = "QUILL"


class Opener(Protocol):
    """How this client reaches the network.

    A Protocol rather than a bare ``Callable`` because the call is
    keyword-shaped, and getting one of those keywords wrong in a test double
    would otherwise only show up at runtime. The default is the reviewed
    egress site; every test in the suite passes its own and touches no socket.
    """

    def __call__(
        self,
        url: str,
        *,
        token: str = "",
        body: dict[str, Any] | None = None,
        method: str = "",
    ) -> dict[str, Any]: ...


#: What :mod:`quill.core.ai.device_login` calls to exchange one form POST.
Poster = Callable[[str, "dict[str, str]"], "dict[str, Any]"]


@dataclass(frozen=True, slots=True)
class GatewayLimits:
    """What the service currently allows, read once per session.

    Read from the server rather than compiled in, so an operator raising a limit
    reaches every installed copy without a release. Defaults are the shipped
    values, used only when the service cannot be reached before a first sign-in.
    """

    max_input_tokens: int = 1500
    max_output_tokens: int = 500
    max_chunks_per_request: int = 3
    hosted_ai_enabled: bool = True
    feature_flags: dict[str, bool] = field(default_factory=dict)

    def feature_available(self, feature: str) -> bool:
        """Whether *feature* is on. Unknown features are treated as **off**.

        Erring that way on purpose: an unknown id is either a feature this build
        predates or one that was removed, and offering a button for something
        that answers with an error is worse than not offering it.
        """
        if not self.hosted_ai_enabled:
            return False
        return bool(self.feature_flags.get(feature, False))

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> GatewayLimits:
        flags = data.get("feature_flags")
        return cls(
            max_input_tokens=int(data.get("max_input_tokens", 1500)),
            max_output_tokens=int(data.get("max_output_tokens", 500)),
            max_chunks_per_request=int(data.get("max_chunks_per_request", 3)),
            hosted_ai_enabled=bool(data.get("hosted_ai_enabled", True)),
            feature_flags={str(k): bool(v) for k, v in (flags or {}).items()},
        )


@dataclass(frozen=True, slots=True)
class GatewayQuota:
    """What is left, for display only.

    The client never enforces anything with these numbers -- the server re-checks
    every limit on the next real request. They exist so somebody can *see* their
    allowance being spent, because a free allowance nobody can watch is one they
    are surprised to run out of.
    """

    monthly_cap: int = 0
    monthly_used: int = 0
    daily_cap: int = 0
    daily_used: int = 0
    reset_at: str = ""
    status: str = "active"
    #: When a new connection's smaller first allowance ends (ISO 8601), or ""
    #: when it does not apply. Sent by the server, like every number here.
    starter_until: str = ""
    #: The monthly allowance everybody gets once the starter one ends.
    standard_monthly_cap: int = 0

    @property
    def monthly_left(self) -> int:
        return max(0, self.monthly_cap - self.monthly_used)

    @property
    def daily_left(self) -> int:
        """What is left today -- never more than is left this month.

        The two caps are independent dials on the server and either can be
        raised or lowered at any time, so neither is assumed here -- both come
        from the server every time the numbers are shown. When the monthly one is
        the smaller (a new connection's first allowance is), today's cannot be
        more than it: reported as it came, the Usage window said "15 of 15 left
        this month" and "20 of 20 left today" in the same breath.
        """
        return max(0, min(self.daily_cap - self.daily_used, self.monthly_left))

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> GatewayQuota:
        return cls(
            monthly_cap=int(data.get("monthly_request_cap", 0)),
            monthly_used=int(data.get("monthly_requests_used", 0)),
            daily_cap=int(data.get("daily_request_cap", 0)),
            daily_used=int(data.get("daily_requests_used", 0)),
            reset_at=str(data.get("reset_at", "")),
            status=str(data.get("status", "active")),
            starter_until=str(data.get("starter_until") or ""),
            standard_monthly_cap=int(data.get("standard_monthly_request_cap") or 0),
        )


# --------------------------------------------------------------------------- #
# The one egress site
# --------------------------------------------------------------------------- #


def _verified_context() -> ssl.SSLContext:
    """A TLS context that verifies. Never relaxed, for any host.

    What travels on this connection is a bearer token and the user's own
    writing, so there is no deployment convenience worth an unverified
    certificate.

    It trusts **Windows' own root store and certifi's bundle together**. The
    store alone was the whole trust list until 2026-09-25, and it failed on a
    Windows 10 machine whose internet was fine: Windows downloads most root
    certificates only when its own networking first needs one, so a machine
    whose browsers carry their own root stores may never have fetched the one
    this service's certificate chains to -- and Python reads the store without
    triggering that download. certifi ships the roots, so the chain verifies
    anyway; the store is kept because it is where a work network's or an
    antivirus's inspecting root lives, and dropping it would break those users
    instead. Adding trust anchors never weakens verification: every
    certificate is still checked, against a longer list of authorities.
    """
    context = ssl.create_default_context()
    try:
        import certifi

        context.load_verify_locations(cafile=certifi.where())
    except Exception:  # noqa: BLE001 - certifi missing leaves the system store
        pass
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def _unreachable(url: str, error: BaseException) -> GatewayError:
    """The sentence for a connection that never produced an answer.

    Said precisely, because the old single sentence -- "could not reach the
    internet" -- was wrong for most of the ways this fails and sent a user
    whose internet worked to go and check it. The system's own reason goes on
    the end: it is what a support conversation needs, and it costs a listener
    one clause.
    """
    host = urllib.parse.urlsplit(url).hostname or "the AI service"
    reason = getattr(error, "reason", error)
    detail = str(reason).strip() or type(reason).__name__
    nothing = "Nothing was sent and nothing was used."
    if isinstance(reason, ssl.SSLCertVerificationError):
        return GatewayCertificateError(
            f"QUILL reached {host} but could not verify its security certificate, "
            f"so it stopped before sending anything ({detail}). {nothing}"
        )
    if isinstance(reason, ssl.SSLError):
        return GatewayCertificateError(
            f"QUILL reached {host} but the secure connection failed ({detail}). {nothing}"
        )
    if isinstance(reason, socket.gaierror):
        return GatewayOfflineError(
            f"QUILL could not look up the address {host}, which usually means this "
            f"computer is offline or its DNS is not answering ({detail}). {nothing}"
        )
    if isinstance(reason, TimeoutError):
        return GatewayUnreachableError(f"{host} did not answer in time ({detail}). {nothing}")
    if isinstance(reason, (ConnectionRefusedError, ConnectionResetError, ConnectionAbortedError)):
        return GatewayUnreachableError(
            f"The connection to {host} was refused or cut off ({detail}). {nothing}"
        )
    return GatewayUnreachableError(f"QUILL could not connect to {host} ({detail}). {nothing}")


def _urlopen_json(
    url: str,
    *,
    token: str = "",
    body: dict[str, Any] | None = None,
    method: str = "",
    answers: tuple[int, ...] = (),
) -> dict[str, Any]:
    """The single outbound call. Returns the parsed JSON body.

    Raises the coded errors in :mod:`quill.core.ai.gateway_errors` -- never a
    bare ``URLError`` or ``HTTPError``, so that every caller and every surface
    above gets a sentence written for a person rather than a Python exception
    rendered at one.

    A non-2xx body is read and used: the gateway puts its real explanation
    there ("You have used today's free limit. It resets at midnight"), and
    discarding it in favour of "HTTP 429" throws away the only part of the
    response a user could act on.

    *answers* names the status codes that are replies rather than failures for
    this call, whose body is returned like a 200's. The device poll needs it:
    the gateway says "pending" with 428 and "expired" or "denied" with 410.
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"))
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", _USER_AGENT)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(  # noqa: S310 - https enforced by _verified_context
            request, timeout=_TIMEOUT_SECONDS, context=_verified_context()
        ) as response:
            raw = response.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as error:
        if error.code in answers:
            try:
                raw = error.read().decode("utf-8", errors="replace")
                return json.loads(raw) if raw.strip() else {}
            except (ValueError, OSError):
                return {}
        raise _error_for_status(error) from error
    except urllib.error.URLError as error:
        raise _unreachable(url, error) from error
    except (TimeoutError, OSError) as error:
        raise _unreachable(url, error) from error
    except json.JSONDecodeError as error:
        raise GatewayServiceError(
            "The AI service sent back something QUILL could not read. "
            "Try again in a moment. Nothing was used."
        ) from error


def _error_for_status(error: urllib.error.HTTPError) -> GatewayError:
    """Turn an HTTP failure into the right coded error, keeping the server's words."""
    try:
        payload = json.loads(error.read().decode("utf-8", errors="replace") or "{}")
    except (ValueError, OSError):
        payload = {}
    message = str(payload.get("message", "")).strip()

    if error.code == 401:
        return GatewayAuthError(message or "This computer has been signed out of QUILL's free AI.")
    if error.code == 429:
        # Sign-up throttling and quota exhaustion share a status code and are
        # completely different facts: one is about this network, the other about
        # this person's allowance.
        if payload.get("status") == "throttled":
            return GatewayPausedError(
                message or "Too many computers have connected from this network recently."
            )
        return GatewayQuotaError(
            message or "You have used your free AI allowance for now.",
            scope=str(payload.get("scope", "")),
            reset_at=str(payload.get("reset_at") or ""),
        )
    if error.code == 422:
        return GatewayTooLargeError(
            message or "That passage is too long for the free tier.",
            words=int(payload.get("tokens_counted", 0) or 0),
            limit_words=int(payload.get("max_input_tokens", 0) or 0),
        )
    if error.code == 503:
        return GatewayPausedError(message or "QUILL's free AI is paused right now.")
    return GatewayServiceError(
        message or "The AI service is having trouble right now. Nothing was used."
    )


# --------------------------------------------------------------------------- #
# The device-code adapter
# --------------------------------------------------------------------------- #


def device_flow_poster(base_url: str) -> Poster:
    """A ``poster`` for :mod:`quill.core.ai.device_login`, speaking to the gateway.

    The gateway implements RFC 8628 with its own spelling: a ``status`` field
    rather than an OAuth ``error`` string, JSON rather than form encoding, and
    HTTP codes carrying the pending/slow-down states. This translates in both
    directions so the existing state machine -- its interval handling, its
    back-off on slow-down, its expiry -- is reused rather than rewritten.

    Reusing it is not only about the lines saved. That module is what
    ``announce_device_code`` reads from, and its polling behaviour has already
    been made to behave for a screen-reader user once.
    """

    def poster(url: str, form: dict[str, str]) -> dict[str, Any]:
        if url.endswith("/device/code"):
            grant = _urlopen_json(f"{base_url}/v1/device/code", body={})
            return dict(grant)

        try:
            # 428 is "pending" and 410 is "expired" or "denied": the gateway's
            # normal answers while somebody types the code, not failures. Read
            # as failures, the very first poll ended the sign-in with
            # "server_error" (reported 2026-09-25).
            reply = _urlopen_json(
                f"{base_url}/v1/device/token",
                body={"device_code": form.get("device_code", "")},
                answers=(410, 428),
            )
        except GatewayQuotaError:
            # 429 on the poll endpoint is "you are polling too fast", not a
            # quota: the gateway uses it for slow_down.
            return {"error": "slow_down"}
        except GatewayPausedError:
            return {"error": "slow_down"}
        except GatewayServiceError as error:
            return {"error": "expired_token" if "expired" in str(error).lower() else "server_error"}

        status = str(reply.get("status", ""))
        if status == "authorized":
            return {
                "access_token": reply.get("token", ""),
                "device_id": reply.get("device_id", ""),
            }
        if status == "pending":
            return {"error": "authorization_pending"}
        if status == "slow_down":
            return {"error": "slow_down"}
        if status == "denied":
            return {"error": "access_denied"}
        return {"error": "expired_token"}

    return poster


# --------------------------------------------------------------------------- #
# The client
# --------------------------------------------------------------------------- #


class GatewayClient:
    """Talks to one gateway, as one signed-in computer.

    ``opener`` exists so every test in the suite runs without a socket: it is
    the only seam, and the default is the reviewed egress site above.
    """

    def __init__(
        self, base_url: str = "", token: str = "", *, opener: Opener | None = None
    ) -> None:
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.token = token
        self._open = opener or _urlopen_json

    # -- read-only ------------------------------------------------------- #

    def fetch_limits(self) -> GatewayLimits:
        """What the service allows. No authentication -- the client needs this
        before it can offer to sign in at all."""
        return GatewayLimits.from_json(self._open(f"{self.base_url}/v1/config"))

    def fetch_quota(self) -> GatewayQuota:
        """What is left for this computer's account."""
        return GatewayQuota.from_json(self._open(f"{self.base_url}/v1/quota", token=self.token))

    # -- the one that costs something ------------------------------------- #

    def ask(
        self, feature: str, prompt: str, chunks: list[str] | None = None
    ) -> tuple[str, GatewayQuota | None]:
        """Run one AI request. Returns ``(answer, quota_after)``.

        The quota comes back with the answer so the display updates without a
        second round trip -- which matters because the alternative is a second
        network call on the success path of every single request.
        """
        body: dict[str, Any] = {"feature": feature, "prompt": prompt}
        if chunks:
            body["chunks"] = chunks
        reply = self._open(f"{self.base_url}/v1/chat", token=self.token, body=body)

        text = str(reply.get("text", ""))
        if not text.strip():
            raise GatewayServiceError(
                "The AI service returned an empty answer. Try again. Nothing was used."
            )

        remaining = reply.get("remaining_quota") or {}
        quota = None
        if remaining:
            quota = GatewayQuota(
                monthly_cap=int(remaining.get("monthly", 0)),
                monthly_used=0,
                daily_cap=int(remaining.get("daily", 0)),
                daily_used=0,
            )
        return text, quota

    # -- signing out ------------------------------------------------------ #

    def revoke(self, device_id: str) -> None:
        """Tell the server this computer is signed out.

        Best effort by design: the local token is deleted whatever happens here.
        A user who has chosen to sign out must end up signed out even if they
        are on a train with no signal, and a token left on the server that
        nothing holds any more is revocable from the console.
        """
        try:
            self._open(f"{self.base_url}/v1/devices/{device_id}", token=self.token, method="DELETE")
        except GatewayError:
            pass
