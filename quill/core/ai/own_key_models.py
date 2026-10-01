"""The models an own API key (OpenAI or Google Gemini) can use, in the order
they are offered, and what each might cost.

**The list comes from the account, never from here.** The provider's model catalog
is asked with the user's key once the key is known to be good, so a model the
account gains appears without a QUILL release and one it loses disappears. Two
things are decided here and nowhere else:

* **What is left out.** Models that cannot answer a passage of text (embeddings,
  speech, transcription, images, moderation, etc.) would make text AI help fail,
  so they are filtered out. Everything else is offered.
* **The order.** Primary flagship models first (Luna 6/GPT-6 for OpenAI,
  Gemini 2.5 Flash/Pro for Gemini), then the rest by name.

**The prices are estimates, and say so everywhere they appear.**
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

__all__ = [
    "ESTIMATE_NOTE",
    "PRICING_URL",
    "PRICING_URL_GEMINI",
    "PRICING_URL_OPENAI",
    "TYPICAL_INPUT_TOKENS",
    "TYPICAL_OUTPUT_TOKENS",
    "Estimate",
    "choice_label",
    "describe_estimate",
    "estimate_for",
    "estimate_note_for",
    "list_models",
    "ordered",
    "pricing_url_for",
    "usable",
]

PRICING_URL_OPENAI = "https://openai.com/api/pricing"
PRICING_URL_GEMINI = "https://ai.google.dev/pricing"
PRICING_URL = PRICING_URL_OPENAI

ESTIMATE_NOTE = (
    "Costs shown are estimates to help you compare models, not OpenAI's prices. "
    f"OpenAI's real prices are at {PRICING_URL_OPENAI}."
)


def pricing_url_for(provider: str) -> str:
    return PRICING_URL_GEMINI if provider.strip().lower() == "gemini" else PRICING_URL_OPENAI


def estimate_note_for(provider: str) -> str:
    url = pricing_url_for(provider)
    prov_name = "Google" if provider.strip().lower() == "gemini" else "OpenAI"
    return (
        f"Costs shown are estimates to help you compare models, not {prov_name}'s prices. "
        f"{prov_name}'s real prices are at {url}."
    )


#: A typical AI help request: about a page of text with the instructions, and a
#: paragraph back.
TYPICAL_INPUT_TOKENS = 1_100
TYPICAL_OUTPUT_TOKENS = 300

#: Models that cannot answer a passage of text. Matched anywhere in the name.
_NOT_FOR_TEXT = re.compile(
    r"embedding|tts|whisper|transcribe|dall-e|image|moderation|audio|realtime"
    r"|babbage|davinci|sora|instruct|aqa|imagen",
    re.IGNORECASE,
)

#: Offered first for OpenAI.
_OPENAI_FIRST = (
    re.compile(r"^(gpt[-_ ]?6[-_ ]luna|luna[-_ ]?6)(?![0-9])", re.IGNORECASE),
    re.compile(r"^gpt[-_ ]?6(?![0-9])", re.IGNORECASE),
)

#: Offered first for Gemini.
_GEMINI_FIRST = (
    re.compile(r"^gemini[-_ ]?2\.5[-_ ]flash($|[-_ ](preview|exp))", re.IGNORECASE),
    re.compile(r"^gemini[-_ ]?2\.5[-_ ]pro($|[-_ ](preview|exp))", re.IGNORECASE),
    re.compile(r"^gemini[-_ ]?2\.5", re.IGNORECASE),
    re.compile(r"^gemini[-_ ]?2\.0[-_ ]flash", re.IGNORECASE),
    re.compile(r"^gemini[-_ ]?1\.5[-_ ]flash", re.IGNORECASE),
    re.compile(r"^gemini[-_ ]?1\.5[-_ ]pro", re.IGNORECASE),
    re.compile(r"^gemini", re.IGNORECASE),
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


_PREMIUM = Estimate("premium", 15.0, 60.0)
_NANO = Estimate("smallest", 0.10, 0.40)
_MINI = Estimate("small", 0.40, 1.60)
_REASONING = Estimate("reasoning", 2.0, 8.0)
_STANDARD = Estimate("standard", 2.50, 10.0)

_GEMINI_FLASH = Estimate("small", 0.075, 0.30)
_GEMINI_PRO = Estimate("standard", 1.25, 5.00)


def usable(names: Iterable[str]) -> list[str]:
    """*names* without the models that cannot answer text, and without repeats."""
    seen: dict[str, None] = {}
    for name in names:
        name = str(name).strip().removeprefix("models/")
        if name and not _NOT_FOR_TEXT.search(name):
            seen.setdefault(name, None)
    return list(seen)


def ordered(names: Iterable[str], provider: str = "openai") -> list[str]:
    """Flagship models first, then everything else, each by name."""
    patterns = _GEMINI_FIRST if provider.strip().lower() == "gemini" else _OPENAI_FIRST

    def rank(name: str) -> tuple[int, str]:
        for position, pattern in enumerate(patterns):
            if pattern.search(name):
                return position, name.lower()
        return len(patterns), name.lower()

    return sorted(usable(names), key=rank)


def estimate_for(model: str, provider: str = "openai") -> Estimate:
    """The rough price tier *model*'s name suggests."""
    name = model.lower()
    if provider.strip().lower() == "gemini" or "gemini" in name:
        if "pro" in name:
            return _GEMINI_PRO
        if "flash" in name or "nano" in name:
            return _GEMINI_FLASH
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
    estimate = estimate_for(model, provider=provider)
    return (
        f"Estimated cost for {model}: {_dollars(estimate.per_request())} per request, "
        f"about {_dollars(estimate.per_request() * 100)} per 100 requests "
        f"({estimate.tier} price tier)."
    )


def choice_label(model: str, provider: str = "openai") -> str:
    """How *model* reads in the model list: its name and its estimate, briefly."""
    per_hundred = _dollars(estimate_for(model, provider=provider).per_request() * 100)
    return f"{model}, about {per_hundred} per 100 requests (estimate)"


def list_models(key: str, provider: str = "openai") -> tuple[list[str], str]:
    """``(models, error)`` for *key*, ordered for offering. Blocking; never raises.

    A successful list is also the proof that the key is good.
    """
    from quill.core.assistant_ai import (
        AssistantConnectionSettings,
        default_host_for_provider,
        default_model_for_provider,
        list_assistant_models,
    )

    prov = provider.strip().lower() or "openai"
    connection = AssistantConnectionSettings(
        provider=prov,
        host=default_host_for_provider(prov),
        model=default_model_for_provider(prov),
    )
    try:
        models, error = list_assistant_models(connection, key, max_models=1_000)
    except Exception as exc:  # noqa: BLE001 - a sentence for a person, never a crash
        return [], str(exc)
    if error:
        return [], error
    offered = ordered(models, provider=prov)
    if not offered:
        prov_name = "Google Gemini" if prov == "gemini" else "OpenAI"
        return [], f"{prov_name} listed no models this key can use for text."
    return offered, ""
