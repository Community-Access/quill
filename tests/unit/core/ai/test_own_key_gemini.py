"""Tests for Google Gemini provider in own-key AI help."""

from __future__ import annotations

import pytest

from quill.core.ai import own_key, own_key_models as models


def test_gemini_models_ordering() -> None:
    """Gemini 2.5 Flash and Pro come first, followed by other Gemini models and standard sorting."""
    discovered = [
        "gemini-1.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "models/gemini-embedding-exp",
        "gemini-2.5-flash-lite",
    ]
    offered = models.ordered(discovered, provider="gemini")
    assert offered[0] == "gemini-2.5-flash"
    assert offered[1] == "gemini-2.5-pro"
    assert "gemini-embedding-exp" not in offered


def test_gemini_pricing_and_estimates() -> None:
    assert models.PRICING_URL_GEMINI == "https://ai.google.dev/pricing"
    assert models.pricing_url_for("gemini") == models.PRICING_URL_GEMINI
    flash_est = models.estimate_for("gemini-2.5-flash", provider="gemini")
    pro_est = models.estimate_for("gemini-2.5-pro", provider="gemini")
    assert flash_est.per_request() < pro_est.per_request()
    assert "ai.google.dev" in models.estimate_note_for("gemini")


def test_gemini_request_execution(monkeypatch) -> None:
    import quill.core.assistant_ai as assistant_ai

    sent: dict[str, object] = {}

    def fake(connection, key, prompt, **kwargs):  # noqa: ANN001, ANN003
        sent.update(provider=connection.provider, model=connection.model, key=key, prompt=prompt)
        sent.update(kwargs)
        return "Gemini summary result.", None

    def fake_key(provider: str) -> str:
        if provider == "gemini":
            return "AIzaSyTestKey"
        return ""

    monkeypatch.setattr(assistant_ai, "load_provider_api_key", fake_key)
    monkeypatch.setattr(assistant_ai, "generate_assistant_response", fake)

    answer = own_key.ask_with_own_key("summarize", "Text to summarize", provider="gemini", model="gemini-2.5-flash")
    assert answer == "Gemini summary result."
    assert sent["provider"] == "gemini"
    assert sent["model"] == "gemini-2.5-flash"
    assert sent["key"] == "AIzaSyTestKey"
    assert str(sent["system_prompt"]).startswith("Summarize the following text")


def test_gemini_size_warning() -> None:
    warning = own_key.size_warning("Sample document text.", "gemini-2.5-flash", free_limit_tokens=3000, provider="gemini")
    assert "Google Gemini" in warning
    assert "gemini-2.5-flash" in warning
    assert "no limits" in warning
