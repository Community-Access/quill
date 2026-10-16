"""Asking before speech goes to a cloud provider, and saying where it goes (D-31).

**The question is generated from the provider's facts** (point 5): what is
sent (speech only, after the voice detector hears it), to which company and
region, who pays, and that QUILL keeps no copy. No is the default. The answer
is saved per provider and per
:attr:`~quill.core.windows_dictation.cloud.types.CloudProvider.consent_version`
in ``windows_dictation_speech_provider_consent``, like
``windows_dictation_openai_consent``: when what is sent changes, the version
goes up and the question is asked again.

**Safe Mode refuses every provider**, before the microphone opens.

**Biasing is said honestly**: "Up to 100 of your words go with it" appears
only for a provider whose capability table has biasing; QUILL never claims a
provider learns words it cannot be told.

wx-free.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.windows_dictation.cloud.types import CloudProvider, Values

__all__ = [
    "biasing_terms",
    "consent_text",
    "consented",
    "speech_line",
    "start_problem",
]


def consent_text(provider: CloudProvider, values: Values | None = None) -> str:
    """The question asked before *provider* first hears anybody."""
    where = provider.where(values or {})
    region = f", in {where}," if where else ""
    capabilities = provider.capabilities()
    words = ""
    if capabilities.biasing:
        words = (
            f" Up to {capabilities.biasing_limit} of your words from My Words and "
            "Phrases go with it, so it spells them your way."
        )
    console = f" See its usage page: {provider.console_url}." if provider.console_url else ""
    terms = (
        f" Read {provider.company}'s terms at {provider.privacy_url} before you agree."
        if provider.privacy_url
        else ""
    )
    return (
        f"{provider.name} sends what you say to {provider.company}.\n\n"
        f"While dictation is on with {provider.name}, each phrase the voice detector "
        f"hears is sent over an encrypted connection to {provider.company}{region} "
        "with the account details you saved in Speech Providers, and the words come "
        f"back.{words} Nothing is sent while nobody is speaking.\n\n"
        f"Your provider bills you; QUILL shows no prices and counts nothing.{console} "
        "Nothing goes through QUILL's servers, and QUILL keeps no copy of the audio.\n\n"
        f"{provider.company}'s own policies apply to what it receives.{terms}\n\n"
        "The built-in engines never send anything anywhere. You can switch back to "
        "one at any time in Dictation Settings.\n\n"
        f"Send your speech to {provider.company} when you dictate with {provider.name}?"
    )


def consented(provider: CloudProvider, consents: Mapping[str, Any] | None) -> bool:
    """Whether the person agreed to *provider*'s current consent version."""
    try:
        version = int(str((consents or {}).get(provider.id, 0)))
    except (TypeError, ValueError):
        version = 0
    return version >= provider.consent_version


def start_problem(
    provider: CloudProvider,
    values: Values,
    consents: Mapping[str, Any] | None,
) -> str:
    """Why dictation with *provider* cannot start, as a sentence; ``""`` when it can.

    Checked before the microphone opens, and before anything is sent.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        return "Safe Mode is on, and Safe Mode never sends anything to the internet."
    missing = provider.available()
    if missing:
        return missing
    problem = provider.problem(values)
    if problem is not None:
        return (
            f"{provider.name} needs its account details first. Open Dictation "
            f"Settings, Speech Providers: {problem.args[0]}"
        )
    if not consented(provider, consents):
        return (
            f"{provider.name} is not switched on. Choose it in Dictation Settings, "
            "where it says what is sent, and agree."
        )
    return ""


def speech_line(provider: CloudProvider, values: Values | None = None) -> str:
    """ "Speech goes to Azure, westeurope." -- the D-24 line, with the region
    when the provider has one."""
    where = provider.where(values or {})
    name = provider.short_name or provider.name
    return f"Speech goes to {name}, {where}." if where else f"Speech goes to {name}."


def biasing_terms(words: Sequence[str], limit: int) -> tuple[list[str], int]:
    """``(terms, left_out)``: the person's vocabulary words for a provider that
    takes at most *limit*, most recent first (the end of My Words is the newest),
    with how many did not fit. Replacements are never sent, only words."""
    cleaned: list[str] = []
    for word in reversed(list(words)):
        text = " ".join(str(word).replace("<", " ").replace(">", " ").split())
        if text and text not in cleaned:
            cleaned.append(text)
    if limit <= 0:
        return [], len(cleaned)
    return cleaned[:limit], max(0, len(cleaned) - limit)
