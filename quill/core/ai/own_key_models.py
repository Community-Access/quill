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


def usable(names: Iterable[str]) -> list[str]:
    """*names* without the models that cannot answer text, and without repeats."""
    seen: dict[str, None] = {}
    for name in names:
        name = str(name).strip()
        if name and not _NOT_FOR_TEXT.search(name):
            seen.setdefault(name, None)
    return list(seen)


def ordered(names: Iterable[str]) -> list[str]:
    """Luna 6 models, then GPT-6 models, then everything else, each by name."""

    def rank(name: str) -> tuple[int, str]:
        for position, pattern in enumerate(_FIRST):
            if pattern.search(name):
                return position, name.lower()
        return len(_FIRST), name.lower()

    return sorted(usable(names), key=rank)


def estimate_for(model: str) -> Estimate:
    """The rough price tier *model*'s name suggests."""
    name = model.lower()
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


def describe_estimate(model: str) -> str:
    """One sentence: what *model* might cost, per request and per hundred."""
    estimate = estimate_for(model)
    return (
        f"Estimated cost for {model}: {_dollars(estimate.per_request())} per request, "
        f"about {_dollars(estimate.per_request() * 100)} per 100 requests "
        f"({estimate.tier} price tier)."
    )


def choice_label(model: str) -> str:
    """How *model* reads in the model list: its name and its estimate, briefly."""
    per_hundred = _dollars(estimate_for(model).per_request() * 100)
    return f"{model}, about {per_hundred} per 100 requests (estimate)"


def list_models(key: str) -> tuple[list[str], str]:
    """``(models, error)`` for *key*, ordered for offering. Blocking; never raises.

    A successful list is also the proof that the key is good: ``/v1/models``
    refuses a key OpenAI does not recognise, and costs nothing to ask.
    """
    from quill.core.ai.own_key import OWN_KEY_PROVIDER, default_model
    from quill.core.assistant_ai import (
        AssistantConnectionSettings,
        default_host_for_provider,
        list_assistant_models,
    )

    connection = AssistantConnectionSettings(
        provider=OWN_KEY_PROVIDER,
        host=default_host_for_provider(OWN_KEY_PROVIDER),
        model=default_model(),
    )
    try:
        models, error = list_assistant_models(connection, key, max_models=1_000)
    except Exception as exc:  # noqa: BLE001 - a sentence for a person, never a crash
        return [], str(exc)
    if error:
        return [], error
    offered = ordered(models)
    if not offered:
        return [], "OpenAI listed no models this key can use for text."
    return offered, ""
