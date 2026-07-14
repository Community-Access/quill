"""Speech provider registry (#617 section 12).

Holds the live provider instances. Providers register themselves (the native
whisper.cpp provider always; optional packs only when their dependency imports
succeed), so an uninstalled engine simply never appears. Pure and wx-free.
"""

from __future__ import annotations

from quill.core.speech.provider import SpeechToTextProvider


class SpeechProviderRegistry:
    """A small ordered registry of speech providers, keyed by ``provider.id``."""

    def __init__(self) -> None:
        self._providers: dict[str, SpeechToTextProvider] = {}

    def register(self, provider: SpeechToTextProvider) -> None:
        """Register (or replace) a provider by its id."""
        self._providers[provider.id] = provider

    def get(self, provider_id: str) -> SpeechToTextProvider | None:
        return self._providers.get(provider_id)

    def all(self) -> list[SpeechToTextProvider]:
        return list(self._providers.values())

    def available(self) -> list[SpeechToTextProvider]:
        """Only providers whose runtime is usable right now.

        A provider that raises while reporting availability is treated as
        unavailable rather than breaking the whole list.
        """
        out: list[SpeechToTextProvider] = []
        for provider in self._providers.values():
            try:
                if provider.is_available():
                    out.append(provider)
            except Exception:  # noqa: BLE001 - a broken provider must not hide the rest
                continue
        return out

    def ids(self) -> list[str]:
        return list(self._providers)
