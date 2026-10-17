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

**Substitutions** (2026-10-16). A failed request is one way to end up on another
provider; the other is *resolution* -- the provider or route the person chose
cannot be used right now, and something else would quietly answer in its place.
:func:`plan_substitution` is the same plan for that moment, and every place QUILL
picks where an AI request goes now consults it:

- **Ask Quill and QUILL's AI tools** (:func:`quill.core.ai.assistant.make_default_backend`):
  the configured connection is unavailable. Substituting the on-device model is
  announced once, when Ask Quill opens. Substituting the *other* cloud provider
  saved in the Ask Quill setup is no longer silent: QUILL keeps the on-device
  model and asks first (``quill/ui/assistant_reply_delivery.py``).
- **The free AI, own keys and ChatGPT plans, in both editors**
  (``quill/ui/hosted_ai_route_guard.py``): the route requests were taking this
  session -- your ChatGPT plan, your own OpenAI or Gemini key, or QUILL's free
  AI -- has changed without you changing it (a key that has gone from the
  credential store, a ChatGPT sign-in that no longer works). Every such change
  sends text to a different company, so it always asks first, and saying No
  sends nothing.

The question is the announcement: a Yes/No box whose text the screen reader reads
as it opens, so nothing is spoken on top of it (GATE-13), and a substitution is
asked about once -- after Yes, the new route is simply the route.
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


def plan_substitution(
    *,
    chosen: str,
    substitute: str,
    substitute_is_local: bool,
    destination: str = "",
) -> FallbackPlan:
    """The plan for answering with *substitute* because *chosen* cannot be used.

    *chosen* and *substitute* are names as a person hears them ("OpenAI",
    "your own Gemini key", "QUILL's free AI"). The same name twice is no
    substitution at all. A local substitute keeps the text on this computer, so
    it is announced and no more; anything else sends the text to somebody the
    person did not pick, so the plan requires consent, and its announcement is
    worded as the question to ask. *destination* is who actually receives the
    text when that is not obvious from *substitute* ("OpenAI" for "your own
    OpenAI key"); it defaults to *substitute*.
    """
    chosen_name = (chosen or "").strip() or "The AI you chose"
    substitute_name = (substitute or "").strip()
    if not substitute_name or substitute_name.lower() == chosen_name.lower():
        return FallbackPlan.none()
    if substitute_is_local:
        return FallbackPlan(
            offer=True,
            to_provider="local",
            requires_consent=False,
            announcement=(
                f"{chosen_name} was not available, so Quill is using the on-device "
                "model instead. Check your provider and key in the AI settings to "
                "restore it."
            ),
        )
    receiver = (destination or "").strip() or substitute_name
    return FallbackPlan(
        offer=True,
        to_provider=substitute_name,
        requires_consent=True,
        announcement=(
            f"{chosen_name} is not available right now. Use {substitute_name} "
            f"instead? That sends your text to {receiver} over the internet. "
            "Choose No and nothing is sent."
        ),
    )
