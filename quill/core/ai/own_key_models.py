"""The models an own OpenAI key can use, in the order they are offered, and what
each might cost.

**The list comes from the account, never from here.** OpenAI's ``/v1/models``
is asked with the user's key once the key is known to be good, so a model the
account gains appears without a QUILL release and one it loses disappears. Two
things are decided here and nowhere else:

* **What is left out.** ``/v1/models`` also returns models that cannot answer a
  passage of text at all -- embeddings, speech, transcription, images,
  moderation, and the completion-only ``instruct`` models. Choosing one would
  make every AI help request fail, so they are not offered. Everything else is.
* **The order.** Luna 6 first, then the other GPT-6 models, then the rest by name
  -- and the first one is what a person who never chose gets.

**The prices are estimates, and say so everywhere they appear.** OpenAI does
not publish prices through its API, so :func:`estimate_for` sorts a model into
a rough tier by its name and works out what a typical AI help request (about a
page in, a paragraph out) would cost at that tier. That is enough to tell a
cheap model from a costly one before choosing, which is the point; it is not a
bill, and :data:`ESTIMATE_NOTE` says where the real prices are.

wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

__all__ = [
    "ESTIMATE_NOTE",
    "PRICING_URL",
    "TYPICAL_INPUT_TOKENS",
    "TYPICAL_OUTPUT_TOKENS",
    "Estimate",
    "choice_label",
    "describe_estimate",
    "estimate_for",
    "list_models",
    "ordered",
    "usable",
]

PRICING_URL = "https://openai.com/api/pricing"
PRICING_URLS = {"openai": PRICING_URL, "gemini": "https://ai.google.dev/pricing"}

ESTIMATE_NOTE = (
    "Costs shown are estimates to help you compare models, not OpenAI's prices. "
    f"OpenAI's real prices are at {PRICING_URL}."
)

#: A typical AI help request: about a page of text with the instructions, and a
#: paragraph back.
TYPICAL_INPUT_TOKENS = 1_100
TYPICAL_OUTPUT_TOKENS = 300

#: Models that cannot answer a passage of text. Matched anywhere in the name.
_NOT_FOR_TEXT = re.compile(
    r"embedding|tts|whisper|transcribe|dall-e|image|moderation|audio|realtime"
    r"|babbage|davinci|sora|instruct|aqa|imagen|veo|learnlm",
    re.IGNORECASE,
)

#: Offered first, in this order: Luna 6 (OpenAI names it ``gpt-6-luna``; a bare
#: ``luna-6`` is matched too), then every other GPT-6 model.
_FIRST = (
    re.compile(r"^(gpt[-_ ]?6[-_ ]luna|luna[-_ ]?6)(?![0-9])", re.IGNORECASE),
    re.compile(r"^gpt[-_ ]?6(?![0-9])", re.IGNORECASE),
)


@dataclass(frozen=True)
class Estimate:
    """An estimated price tier, in US dollars per million tokens."""

    tier: str
    input_per_million: float
    output_per_million: float

    def per_request(self) -> float:
        return (
            TYPICAL_INPUT_TOKENS * self.input_per_million
            + TYPICAL_OUTPUT_TOKENS * self.output_per_million
        ) / 1_000_000


#: Gemini's published tiers (US dollars per million tokens, text, mid 2026):
#: Flash-Lite, Flash, Pro. Names carry the tier, as OpenAI's do.
_GEMINI_LITE = Estimate("smallest", 0.10, 0.40)
_GEMINI_FLASH = Estimate("small", 0.30, 2.50)
_GEMINI_PRO = Estimate("premium", 1.25, 10.0)
#: Offered first for Gemini: the current Flash, then the current Pro, then the
#: rest of that generation, then older ones, each by name.
_GEMINI_FIRST = (
    re.compile(r"^gemini[-_ ]?2\.5[-_ ]flash(?![-_ ]lite)", re.IGNORECASE),
    re.compile(r"^gemini[-_ ]?2\.5[-_ ]pro", re.IGNORECASE),
    re.compile(r"^gemini[-_ ]?2\.5", re.IGNORECASE),
    re.compile(r"^gemini[-_ ]?2", re.IGNORECASE),
    re.compile(r"^gemini", re.IGNORECASE),
)
_PREMIUM = Estimate("premium", 15.0, 60.0)
_NANO = Estimate("smallest", 0.10, 0.40)
_MINI = Estimate("small", 0.40, 1.60)
_REASONING = Estimate("reasoning", 2.0, 8.0)
_STANDARD = Estimate("standard", 2.50, 10.0)


def usable(names: Iterable[str]) -> list[str]:
    """*names* without the models that cannot answer text, and without repeats."""
    seen: dict[str, None] = {}
    for name in names:
        name = str(name).strip()
        if name and not _NOT_FOR_TEXT.search(name):
            seen.setdefault(name, None)
    return list(seen)


def ordered(names: Iterable[str], provider: str = "openai") -> list[str]:
    """OpenAI: Luna 6, then GPT-6, then the rest. Gemini: the current Flash, then
    Pro, then the rest of its generation. Each group by name."""
    patterns = _GEMINI_FIRST if provider.strip().lower() == "gemini" else _FIRST

    def rank(name: str) -> tuple[int, str]:
        for position, pattern in enumerate(patterns):
            if pattern.search(name):
                return position, name.lower()
        return len(patterns), name.lower()

    return sorted(usable(names), key=rank)


def pricing_url(provider: str = "openai") -> str:
    return PRICING_URLS.get(provider.strip().lower(), PRICING_URL)


def estimate_note(provider: str = "openai") -> str:
    """The honesty line beside every estimate, naming the provider's own prices."""
    who = "Google" if provider.strip().lower() == "gemini" else "OpenAI"
    return (
        f"Costs shown are estimates to help you compare models, not {who}'s prices. "
        f"{who}'s real prices are at {pricing_url(provider)}."
    )


def estimate_for(model: str, provider: str = "openai") -> Estimate:
    """The rough price tier *model*'s name suggests, for *provider*'s price list."""
    name = model.lower()
    if provider.strip().lower() == "gemini" or name.startswith("gemini"):
        if "lite" in name:
            return _GEMINI_LITE
        if "pro" in re.split(r"[-_.]", name):
            return _GEMINI_PRO
        return _GEMINI_FLASH
    if "pro" in re.split(r"[-_.]", name):
        return _PREMIUM
    if "nano" in name:
        return _NANO
    if "mini" in name:
        return _MINI
    if re.match(r"^o\d", name):
        return _REASONING
    return _STANDARD


def _dollars(amount: float) -> str:
    if amount < 0.01:
        return "less than 1 cent"
    return f"${amount:,.2f}"


def describe_estimate(model: str, provider: str = "openai") -> str:
    """One sentence: what *model* might cost, per request and per hundred."""
    estimate = estimate_for(model, provider)
    return (
        f"Estimated cost for {model}: {_dollars(estimate.per_request())} per request, "
        f"about {_dollars(estimate.per_request() * 100)} per 100 requests "
        f"({estimate.tier} price tier)."
    )


def choice_label(model: str, provider: str = "openai") -> str:
    """How *model* reads in the model list: its name and its estimate, briefly."""
    per_hundred = _dollars(estimate_for(model, provider).per_request() * 100)
    return f"{model}, about {per_hundred} per 100 requests (estimate)"


def list_models(key: str, provider: str = "openai") -> tuple[list[str], str]:
    """``(models, error)`` for *key* at *provider*, ordered for offering.
    Blocking; never raises.

    A successful list is also the proof that the key is good: both providers'
    model lists refuse a key they do not recognise, and cost nothing to ask.
    """
    from quill.core.ai.own_key import default_model, normalize_provider, provider_name
    from quill.core.assistant_ai import (
        AssistantConnectionSettings,
        default_host_for_provider,
        list_assistant_models,
    )

    chosen = normalize_provider(provider)
    connection = AssistantConnectionSettings(
        provider=chosen,
        host=default_host_for_provider(chosen),
        model=default_model(chosen),
    )
    try:
        models, error = list_assistant_models(connection, key, max_models=1_000)
    except Exception as exc:  # noqa: BLE001 - a sentence for a person, never a crash
        return [], str(exc)
    if error:
        return [], error
    offered = ordered(models, chosen)
    if not offered:
        return [], f"{provider_name(chosen)} listed no models this key can use for text."
    return offered, ""
