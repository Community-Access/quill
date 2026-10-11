"""The models an own key can use, in the order they are offered, and what each
might cost -- for OpenAI and for Google Gemini, each by its own rules.

**The list comes from the account, never from here.** The provider's own model
list (OpenAI's ``/v1/models``, Gemini's ``/v1beta/models``) is asked with the
user's key once the key is known to be good, so a model the account gains
appears without a QUILL release and one it loses disappears. Two things are
decided here and nowhere else, per provider:

* **What is left out.** ``/v1/models`` also returns models that cannot answer a
  passage of text at all -- embeddings, speech, transcription, images,
  moderation, and the completion-only ``instruct`` models. Choosing one would
  make every AI help request fail, so they are not offered. Everything else is.
* **The order.** Luna 6 first, then the other GPT-6 models, then the rest by name
  -- and the first one is what a person who never chose gets. For Gemini:
  stable models before previews and experiments, newer versions first, Flash
  before Flash-Lite before Pro within a version, then by name. Deterministic:
  the same list in any order comes out the same, so a listener arrowing through
  it meets the same rows in the same places every time.
* **Gemini's leftovers** are embeddings, Imagen, Veo, speech, live audio, image
  generation and the attributed-question model -- none can answer a passage.

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
    "GEMINI_ESTIMATE_NOTE",
    "GEMINI_PRICING_URL",
    "PRICING_URL",
    "TYPICAL_INPUT_TOKENS",
    "TYPICAL_OUTPUT_TOKENS",
    "Estimate",
    "choice_label",
    "describe_estimate",
    "estimate_for",
    "estimate_note",
    "list_models",
    "ordered",
    "usable",
]

PRICING_URL = "https://openai.com/api/pricing"
GEMINI_PRICING_URL = "https://ai.google.dev/gemini-api/docs/pricing"

ESTIMATE_NOTE = (
    "Costs shown are estimates to help you compare models, not OpenAI's prices. "
    f"OpenAI's real prices are at {PRICING_URL}."
)

GEMINI_ESTIMATE_NOTE = (
    "Costs shown are estimates to help you compare models, not Google's prices. "
    "A key on Google's free tier may not be charged at all, but Google may use "
    "what is sent on the free tier to improve its products. "
    f"Google's real prices are at {GEMINI_PRICING_URL}."
)

_GEMINI = "gemini"

#: A typical AI help request: about a page of text with the instructions, and a
#: paragraph back.
TYPICAL_INPUT_TOKENS = 1_100
TYPICAL_OUTPUT_TOKENS = 300

#: Models that cannot answer a passage of text. Matched anywhere in the name.
_NOT_FOR_TEXT = re.compile(
    r"embedding|tts|whisper|transcribe|dall-e|image|moderation|audio|realtime"
    r"|babbage|davinci|sora|instruct",
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


_PREMIUM = Estimate("premium", 15.0, 60.0)
_NANO = Estimate("smallest", 0.10, 0.40)
_MINI = Estimate("small", 0.40, 1.60)
_REASONING = Estimate("reasoning", 2.0, 8.0)
_STANDARD = Estimate("standard", 2.50, 10.0)

#: Gemini's tiers, by the same rough method: a name says which.
_GEMINI_LITE = Estimate("smallest", 0.10, 0.40)
_GEMINI_FLASH = Estimate("small", 0.30, 2.50)
_GEMINI_PRO = Estimate("premium", 1.25, 10.0)

#: Gemini models that cannot answer a passage of text. Matched anywhere in the name.
_GEMINI_NOT_FOR_TEXT = re.compile(
    r"embedding|aqa|imagen|veo|tts|image|native-audio|live|computer-use|robotics",
    re.IGNORECASE,
)
_GEMINI_PREVIEW = re.compile(r"preview|exp(erimental)?\b|-exp-", re.IGNORECASE)
_GEMINI_VERSION = re.compile(r"gemini-(\d+(?:\.\d+)?)", re.IGNORECASE)


def estimate_note(provider: str = "openai") -> str:
    """Where *provider*'s real prices are, and that the figures are estimates."""
    return GEMINI_ESTIMATE_NOTE if provider == _GEMINI else ESTIMATE_NOTE


def _gemini_rank(name: str) -> tuple[int, float, int, str]:
    lowered = name.lower()
    preview = 1 if _GEMINI_PREVIEW.search(lowered) else 0
    found = _GEMINI_VERSION.search(lowered)
    version = float(found.group(1)) if found else 0.0
    if "flash-lite" in lowered:
        family = 2
    elif "flash" in lowered:
        family = 0
    elif "pro" in lowered:
        family = 1
    else:
        family = 3
    return preview, -version, family, lowered


def usable(names: Iterable[str], provider: str = "openai") -> list[str]:
    """*names* without the models that cannot answer text, and without repeats.

    A Gemini name loses the ``models/`` prefix Gemini's own list gives it, so
    ``models/gemini-2.5-flash`` and ``gemini-2.5-flash`` are one row.
    """
    from quill.core.ai.endpoints import gemini_model_id

    gemini = provider == _GEMINI
    leave_out = _GEMINI_NOT_FOR_TEXT if gemini else _NOT_FOR_TEXT
    seen: dict[str, None] = {}
    for name in names:
        name = gemini_model_id(str(name)) if gemini else str(name).strip()
        if name and not leave_out.search(name):
            seen.setdefault(name, None)
    return list(seen)


def ordered(names: Iterable[str], provider: str = "openai") -> list[str]:
    """OpenAI: Luna 6, then GPT-6, then everything else, each by name.

    Gemini: stable before preview, newest version first, Flash, Flash-Lite,
    Pro, then by name (see the module docstring).
    """
    if provider == _GEMINI:
        return sorted(usable(names, provider), key=_gemini_rank)

    def rank(name: str) -> tuple[int, str]:
        for position, pattern in enumerate(_FIRST):
            if pattern.search(name):
                return position, name.lower()
        return len(_FIRST), name.lower()

    return sorted(usable(names), key=rank)


def estimate_for(model: str, provider: str = "openai") -> Estimate:
    """The rough price tier *model*'s name suggests, on *provider*."""
    name = model.lower()
    if provider == _GEMINI:
        if "flash-lite" in name:
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


def list_models(key: str, provider: str = "openai", *, host: str = "") -> tuple[list[str], str]:
    """``(models, error)`` for *key* on *provider*, ordered for offering.

    Blocking; never raises; the error never contains the key. A successful
    list is also the proof that the key is good: both providers refuse a key
    they do not recognise, and listing costs nothing. *host* is for tests.
    """
    from quill.core.ai.own_key import default_model, provider_name, scrub
    from quill.core.assistant_ai import (
        AssistantConnectionSettings,
        default_host_for_provider,
        list_assistant_models,
    )

    connection = AssistantConnectionSettings(
        provider=provider,
        host=host or default_host_for_provider(provider),
        model=default_model(provider),
    )
    try:
        models, error = list_assistant_models(connection, key, max_models=1_000)
    except Exception as exc:  # noqa: BLE001 - a sentence for a person, never a crash
        return [], scrub(str(exc), key)
    if error:
        return [], scrub(error, key)
    offered = ordered(models, provider)
    if not offered:
        return [], f"{provider_name(provider)} listed no models this key can use for text."
    return offered, ""
