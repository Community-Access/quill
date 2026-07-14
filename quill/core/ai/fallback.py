"""Cloud <-> local AI fallback decisions (Phase 4 — AI routing).

When an AI request fails because of connectivity (offline, timeout, rate-limit, a
5xx) and the *other kind* of provider is available, QUILL can offer to retry there:
a cloud request that can't reach the network falls back to a local model, and a
local model that isn't working falls back to a configured cloud provider.

Two firm rules, both encoded here (see QUILL-PRD.md §5.25f and the routing notes):

- **Never silent.** Every fallback is an **offer**, surfaced accessibly and announced.
  This module only ever produces a plan to *offer*; it never switches anything.
- **Never quietly change the privacy posture.** Falling back **cloud -> local** keeps
  data on the device (privacy improves), so it can be offered directly. Falling back
  **local -> cloud** would send text off the device, so the plan is marked
  ``requires_consent`` with a spoken privacy note — the UI must get an explicit yes.

Kept wx-free and headless-testable: it classifies the failure and returns a
:class:`FallbackPlan`; the UI decides how to present the offer and performs the retry.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Failure kinds that a fallback can help with (connectivity / availability, not a
#: bad request or a content-policy refusal, which retrying elsewhere won't fix).
CONNECTIVITY_FAILURES = frozenset({"offline", "timeout", "rate_limit", "server_error"})

#: Provider ids that run on the user's own machine (no data leaves the device).
_LOCAL_PROVIDERS = frozenset({"ollama", "local", "llama_cpp", "foundation"})


def is_local_provider(provider_id: str) -> bool:
    """True when ``provider_id`` runs on-device (so its data never leaves the machine)."""
    pid = (provider_id or "").strip().lower()
    return pid in _LOCAL_PROVIDERS


def classify_exception(exc: BaseException) -> str:
    """Map a raised exception to a fallback failure kind (best-effort, wx-free).

    Unknown/typed-as-other errors return ``"other"``, which never triggers a
    fallback offer — we only reroute on clear connectivity/availability problems.
    """
    import socket
    from urllib.error import HTTPError, URLError

    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, HTTPError):
        if exc.code == 429:
            return "rate_limit"
        if 500 <= exc.code < 600:
            return "server_error"
        return "other"
    if isinstance(exc, URLError):
        # DNS failure / connection refused / no route — treat as offline.
        return "offline"
    if isinstance(exc, (ConnectionError, socket.gaierror)):
        return "offline"
    return "other"


@dataclass(frozen=True, slots=True)
class FallbackPlan:
    """An accessible offer to retry a failed AI request on the other kind of provider."""

    #: True when a fallback should be offered at all.
    offer: bool
    #: The provider to fall back to ("local" or a cloud provider id), or "" when none.
    to_provider: str = ""
    #: True when the fallback would send data off the device and needs explicit consent.
    requires_consent: bool = False
    #: Complete, screen-reader-friendly announcement/offer text.
    announcement: str = ""

    @classmethod
    def none(cls) -> FallbackPlan:
        return cls(offer=False)


def plan_fallback(
    *,
    primary_provider: str,
    failure_kind: str,
    local_available: bool,
    cloud_available: bool,
    cloud_provider: str = "",
) -> FallbackPlan:
    """Decide whether/where to offer a fallback for a failed request.

    ``primary_provider`` is what just failed; ``failure_kind`` is from
    :func:`classify_exception`. ``local_available`` means a local model is installed
    and usable; ``cloud_available`` means a cloud provider is configured (has a key).
    ``cloud_provider`` names that cloud provider for the announcement.
    """
    if failure_kind not in CONNECTIVITY_FAILURES:
        return FallbackPlan.none()

    if is_local_provider(primary_provider):
        # Local failed -> offer cloud, but only with explicit consent (data leaves device).
        if not cloud_available:
            return FallbackPlan.none()
        name = cloud_provider or "a cloud provider"
        return FallbackPlan(
            offer=True,
            to_provider=cloud_provider or "cloud",
            requires_consent=True,
            announcement=(
                f"The on-device model is unavailable. Retry this request with {name}? "
                "This sends your text to that service over the internet."
            ),
        )

    # Cloud failed -> offer local, which keeps data on the device (no new consent).
    if not local_available:
        return FallbackPlan.none()
    return FallbackPlan(
        offer=True,
        to_provider="local",
        requires_consent=False,
        announcement=(
            "The cloud service could not be reached. Retry this request with your "
            "on-device model? Your text stays on this computer."
        ),
    )
