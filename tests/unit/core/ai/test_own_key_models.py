"""The own-key model list: what is offered, in what order, and the estimates."""

from __future__ import annotations

from quill.core.ai import own_key_models as models


def test_luna_6_then_gpt_6_come_first_and_the_rest_by_name() -> None:
    """OpenAI's own names, as a real account listed them on 2026-09-25."""
    offered = models.ordered(["gpt-4o", "gpt-6-sol", "gpt-6-luna", "chat-latest", "gpt-6-astra"])
    assert offered == ["gpt-6-luna", "gpt-6-astra", "gpt-6-sol", "chat-latest", "gpt-4o"]

    offered = models.ordered([
        "gpt-4o",
        "o3",
        "gpt-6-mini",
        "luna-6",
        "gpt-60",
        "Luna-6-pro",
        "gpt-6",
    ])
    assert offered == ["luna-6", "Luna-6-pro", "gpt-6", "gpt-6-mini", "gpt-4o", "gpt-60", "o3"]


def test_models_that_cannot_answer_text_are_left_out_and_repeats_dropped() -> None:
    offered = models.usable([
        "text-embedding-3-large",
        "tts-1",
        "whisper-1",
        "dall-e-3",
        "omni-moderation-latest",
        "gpt-4o-transcribe",
        "gpt-3.5-turbo-instruct",
        "gpt-4o-realtime-preview",
        "gpt-image-1",
        "gpt-4o",
        "gpt-4o",
    ])
    assert offered == ["gpt-4o"]


def test_every_estimate_says_it_is_one_and_where_the_real_prices_are() -> None:
    assert "estimate" in models.choice_label("gpt-6")
    assert "not OpenAI's prices" in models.ESTIMATE_NOTE
    assert models.PRICING_URL in models.ESTIMATE_NOTE
    assert "per 100 requests" in models.describe_estimate("gpt-6")


def test_smaller_models_are_estimated_cheaper() -> None:
    cost = lambda name: models.estimate_for(name).per_request()  # noqa: E731
    assert cost("gpt-6-nano") < cost("gpt-6-mini") < cost("gpt-6") < cost("gpt-6-pro")
    assert models.estimate_for("gpt-5-pro").tier == "premium"
    assert models.estimate_for("o4-mini").tier == "small"


def test_a_listing_is_ordered_and_an_error_is_a_sentence(monkeypatch) -> None:
    import quill.core.assistant_ai as assistant_ai

    monkeypatch.setattr(
        assistant_ai,
        "list_assistant_models",
        lambda *_a, **_k: (["gpt-4o", "tts-1", "gpt-6"], None),
    )
    assert models.list_models("sk-test") == (["gpt-6", "gpt-4o"], "")
    monkeypatch.setattr(
        assistant_ai, "list_assistant_models", lambda *_a, **_k: ([], "Invalid key.")
    )
    assert models.list_models("sk-bad") == ([], "Invalid key.")
    monkeypatch.setattr(assistant_ai, "list_assistant_models", lambda *_a, **_k: (["tts-1"], None))
    assert models.list_models("sk-test")[0] == []
