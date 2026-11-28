"""The dictation provider ladder falls back to the frame's own provider.

``MainFrame._speech_provider`` takes no arguments. The resolver used to call it
with ``registry=``, which raised TypeError exactly when the preference ladder
named an engine the registry doesn't hold -- the one case that needs the
fallback.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui import dictation_transcription


class _Registry:
    def __init__(self, engines: dict[str, object]) -> None:
        self._engines = engines

    def get(self, provider_id: str) -> object | None:
        return self._engines.get(provider_id)


class _Frame:
    """Just what resolve_dictation_provider touches, with the real signatures."""

    def __init__(self, registry: _Registry, chosen: str = "") -> None:
        self.settings = SimpleNamespace(speech_provider=chosen)
        self._registry = registry
        self.fallback = object()

    def _speech_registry(self) -> _Registry:
        return self._registry

    def _speech_provider(self) -> object:  # no arguments, like MainFrame's
        return self.fallback


def test_an_unregistered_engine_falls_back_instead_of_raising(monkeypatch) -> None:
    monkeypatch.setattr(
        "quill.core.speech.service.preferred_dictation_provider_id",
        lambda _registry, _chosen: "no-such-engine",
    )
    frame = _Frame(_Registry({}), chosen="no-such-engine")
    assert dictation_transcription.resolve_dictation_provider(frame) is frame.fallback
    # The answer is cached against the user's choice, like any other.
    assert frame._dictation_provider_cache is frame.fallback


def test_a_registered_engine_wins_over_the_fallback(monkeypatch) -> None:
    engine = object()
    monkeypatch.setattr(
        "quill.core.speech.service.preferred_dictation_provider_id",
        lambda _registry, _chosen: "whisper",
    )
    frame = _Frame(_Registry({"whisper": engine}))
    assert dictation_transcription.resolve_dictation_provider(frame) is engine
