"""Accessible OAuth device-flow sign-in for AI subscriptions (AI-19).

The most requested accessibility win from the Pi research is "sign in with the
subscription you already have" instead of "paste a 51-character secret you
cannot see." The OAuth 2.0 Device Authorization Grant (RFC 8628) is ideal for a
screen-reader user: QUILL asks the provider for a short, speakable user code,
the user opens a URL in their browser and types that code, and QUILL polls in
the background until the user finishes — no unreadable key paste.

This module is the pure, wx-free, strict-typed state machine for that flow. It
deliberately takes an injected ``poster`` for every network exchange rather than
calling out itself, so:

* it is fully testable without any live endpoint, and
* it adds **no** new ``urlopen``/``urlretrieve`` site to the GATE-9 egress
  inventory — the real HTTP poster is supplied at the UI/provider layer where
  the consent surface and verified TLS context live (AI-13 boundary).

Token storage (DPAPI) and the consent surface are the caller's responsibility;
this engine only models the flow and produces screen-reader announcements.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# A poster performs one HTTPS form POST and returns the parsed JSON object.
Poster = Callable[[str, "dict[str, str]"], "dict[str, Any]"]
# A clock returns a monotonically increasing number of seconds.
Clock = Callable[[], float]
# A sleeper waits the given number of seconds (injectable for tests).
Sleeper = Callable[[float], None]


def spoken_code(user_code: str) -> str:
    """A device-flow user code as separate characters, so a reader says each one.

    ``WDJB-MJHT`` -> ``W D J B dash M J H T``: the letters spaced, the hyphen a
    word. Read as one word, the code is a word nobody can type back; spacing the
    whole string after swapping in " dash " would spell "dash" out letter by
    letter too. Every device-flow sign-in in the family (GitHub, Copilot, the
    hosted AI) speaks its code through this one helper.
    """
    return " dash ".join(" ".join(part) for part in user_code.strip().split("-"))


STATUS_AUTHORIZED = "authorized"
STATUS_PENDING = "pending"
STATUS_SLOW_DOWN = "slow_down"
STATUS_DENIED = "denied"
STATUS_EXPIRED = "expired"
STATUS_ERROR = "error"

_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
_SLOW_DOWN_INCREMENT = 5.0


@dataclass(frozen=True, slots=True)
class DeviceFlowConfig:
    client_id: str
    device_authorization_url: str
    token_url: str
    scope: str = ""


@dataclass(frozen=True, slots=True)
class DeviceCodeGrant:
    device_code: str
    user_code: str
    verification_uri: str
    interval: float = 5.0
    expires_in: float = 900.0
    verification_uri_complete: str | None = None

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> DeviceCodeGrant:
        try:
            device_code = str(data["device_code"])
            user_code = str(data["user_code"])
            verification_uri = str(data["verification_uri"])
        except KeyError as error:  # pragma: no cover - defensive
            raise ValueError(f"Device authorization response missing {error}.") from error
        complete = data.get("verification_uri_complete")
        return cls(
            device_code=device_code,
            user_code=user_code,
            verification_uri=verification_uri,
            interval=float(data.get("interval", 5)),
            expires_in=float(data.get("expires_in", 900)),
            verification_uri_complete=str(complete) if complete else None,
        )


@dataclass(frozen=True, slots=True)
class PollResult:
    status: str
    tokens: dict[str, Any] | None = None
    error: str | None = None


def request_device_code(config: DeviceFlowConfig, *, poster: Poster) -> DeviceCodeGrant:
    """Start the flow: ask the provider for a device and user code."""

    form = {"client_id": config.client_id}
    if config.scope:
        form["scope"] = config.scope
    response = poster(config.device_authorization_url, form)
    return DeviceCodeGrant.from_response(response)


def poll_once(config: DeviceFlowConfig, grant: DeviceCodeGrant, *, poster: Poster) -> PollResult:
    """Poll the token endpoint once and classify the provider's reply."""

    form = {
        "client_id": config.client_id,
        "grant_type": _GRANT_TYPE,
        "device_code": grant.device_code,
    }
    response = poster(config.token_url, form)
    if response.get("access_token"):
        return PollResult(STATUS_AUTHORIZED, tokens=response)
    error = str(response.get("error", "")).strip()
    if error == "authorization_pending":
        return PollResult(STATUS_PENDING)
    if error == "slow_down":
        return PollResult(STATUS_SLOW_DOWN)
    if error == "access_denied":
        return PollResult(STATUS_DENIED, error="You declined the sign-in request.")
    if error == "expired_token":
        return PollResult(STATUS_EXPIRED, error="The sign-in code expired before you finished.")
    description = str(response.get("error_description", "")).strip()
    detail = description or error or "Unknown sign-in error."
    return PollResult(STATUS_ERROR, error=detail)


def run_device_login(
    config: DeviceFlowConfig,
    grant: DeviceCodeGrant,
    *,
    poster: Poster,
    clock: Clock,
    sleeper: Sleeper,
) -> PollResult:
    """Poll until the user finishes, declines, or the code expires.

    Respects the provider's polling ``interval`` and honors ``slow_down`` by
    backing off, and stops at ``expires_in``. Returns the terminal result.
    """

    interval = max(grant.interval, 1.0)
    deadline = clock() + grant.expires_in
    while True:
        result = poll_once(config, grant, poster=poster)
        if result.status in (STATUS_AUTHORIZED, STATUS_DENIED, STATUS_EXPIRED, STATUS_ERROR):
            return result
        if result.status == STATUS_SLOW_DOWN:
            interval += _SLOW_DOWN_INCREMENT
        if clock() + interval >= deadline:
            return PollResult(STATUS_EXPIRED, error="The sign-in code expired before you finished.")
        sleeper(interval)


def announce_device_code(grant: DeviceCodeGrant) -> str:
    """A screen-reader-friendly instruction (A11Y-1 announcement grammar)."""

    minutes = max(1, round(grant.expires_in / 60))
    plural = "minute" if minutes == 1 else "minutes"
    return (
        f"To sign in, open {grant.verification_uri} in your browser and enter the "
        f"code {grant.user_code}. This code expires in about {minutes} {plural}."
    )


def describe_login_result(result: PollResult) -> str:
    """A spoken summary of a terminal poll result."""

    if result.status == STATUS_AUTHORIZED:
        return "Signed in. Your subscription is connected."
    if result.error:
        return f"Sign-in did not complete. {result.error}"
    if result.status == STATUS_DENIED:
        return "Sign-in did not complete. You declined the request."
    if result.status == STATUS_EXPIRED:
        return "Sign-in did not complete. The code expired."
    return "Sign-in did not complete."
