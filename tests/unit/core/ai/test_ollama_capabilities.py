from __future__ import annotations

import pytest

import quill.core.ai.ollama_capabilities as caps_mod
from quill.core.ai.ollama_capabilities import (
    capability_badge,
    capability_summary,
    enrich_capabilities,
    fetch_model_capabilities,
    format_model_line,
)

# --- pure helpers ---


def test_badge_vision() -> None:
    assert capability_badge(["completion", "vision"]) == "Vision"


def test_badge_tools() -> None:
    assert capability_badge(["completion", "tools"]) == "Tools"


def test_badge_vision_and_tools() -> None:
    assert capability_badge(["completion", "vision", "tools"]) == "Vision + Tools"


def test_badge_completion_only_is_empty() -> None:
    assert capability_badge(["completion"]) == ""


def test_badge_none_or_empty_is_empty() -> None:
    assert capability_badge(None) == ""
    assert capability_badge([]) == ""


def test_badge_is_case_insensitive() -> None:
    assert capability_badge(["Completion", "VISION"]) == "Vision"


def test_format_model_line_adds_badge() -> None:
    assert format_model_line("llava:7b", ["completion", "vision"]) == "llava:7b (Vision)"


def test_format_model_line_bare_for_completion_only() -> None:
    assert format_model_line("llama3.2:1b", ["completion"]) == "llama3.2:1b"


def test_format_model_line_bare_for_unknown() -> None:
    assert format_model_line("mystery-model", None) == "mystery-model"


def test_capability_summary_lists_each_model() -> None:
    summary = capability_summary(
        ["llava:7b", "llama3.2:1b", "qwen2.5:7b"],
        {"llava:7b": ["completion", "vision"], "qwen2.5:7b": ["completion", "tools"]},
    )
    assert summary == "llava:7b (Vision), llama3.2:1b, qwen2.5:7b (Tools)"


def test_capability_summary_empty_for_no_models() -> None:
    assert capability_summary([], {}) == ""


# --- fetch_model_capabilities (mocked _post_json) ---


@pytest.fixture
def _clear_cache():
    caps_mod._CAPABILITY_CACHE.clear()
    yield
    caps_mod._CAPABILITY_CACHE.clear()


def test_fetch_returns_capabilities(monkeypatch, _clear_cache) -> None:
    monkeypatch.setattr(
        "quill.core.ai_chat._post_json",
        lambda url, payload, headers, timeout: {"capabilities": ["completion", "vision"]},
    )
    assert fetch_model_capabilities("http://localhost:11434", "llava:7b") == [
        "completion",
        "vision",
    ]


def test_fetch_returns_empty_list_when_only_completion(monkeypatch, _clear_cache) -> None:
    monkeypatch.setattr(
        "quill.core.ai_chat._post_json",
        lambda url, payload, headers, timeout: {"capabilities": ["completion"]},
    )
    assert fetch_model_capabilities("http://localhost:11434", "llama3.2:1b") == ["completion"]


def test_fetch_returns_none_when_field_missing(monkeypatch, _clear_cache) -> None:
    # Older Ollama without the capabilities field -> unknown, not "text only".
    monkeypatch.setattr(
        "quill.core.ai_chat._post_json",
        lambda url, payload, headers, timeout: {"details": {"family": "llama"}},
    )
    assert fetch_model_capabilities("http://localhost:11434", "llama3.2:1b") is None


def test_fetch_returns_none_on_error(monkeypatch, _clear_cache) -> None:
    def _raise(*a, **k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("quill.core.ai_chat._post_json", _raise)
    assert fetch_model_capabilities("http://localhost:11434", "llava:7b") is None


def test_fetch_returns_none_for_empty_host_or_model(_clear_cache) -> None:
    assert fetch_model_capabilities("", "llava:7b") is None
    assert fetch_model_capabilities("http://localhost:11434", "") is None


def test_fetch_caches_successful_lookup(monkeypatch, _clear_cache) -> None:
    calls: list[str] = []

    def _post(url, payload, headers, timeout):
        calls.append(payload["model"])
        return {"capabilities": ["completion", "vision"]}

    monkeypatch.setattr("quill.core.ai_chat._post_json", _post)
    host = "http://localhost:11434"
    assert fetch_model_capabilities(host, "llava:7b") == ["completion", "vision"]
    assert fetch_model_capabilities(host, "llava:7b") == ["completion", "vision"]
    assert fetch_model_capabilities(host, "LLAVA:7b") == [
        "completion",
        "vision",
    ]  # case-insensitive
    assert len(calls) == 1  # served from cache after the first call


def test_fetch_does_not_cache_failures(monkeypatch, _clear_cache) -> None:
    calls: list[str] = []

    def _post(url, payload, headers, timeout):
        calls.append(payload["model"])
        raise RuntimeError("down")

    monkeypatch.setattr("quill.core.ai_chat._post_json", _post)
    assert fetch_model_capabilities("http://localhost:11434", "llava:7b") is None
    assert fetch_model_capabilities("http://localhost:11434", "llava:7b") is None
    assert len(calls) == 2  # retried both times so a later restart is picked up


# --- enrich_capabilities ---


def test_enrich_skips_unknowns(monkeypatch, _clear_cache) -> None:
    def _post(url, payload, headers, timeout):
        if payload["model"] == "llava:7b":
            return {"capabilities": ["completion", "vision"]}
        if payload["model"] == "qwen2.5:7b":
            return {"capabilities": ["completion", "tools"]}
        raise RuntimeError("unknown model")

    monkeypatch.setattr("quill.core.ai_chat._post_json", _post)
    result = enrich_capabilities(
        "http://localhost:11434", ["llava:7b", "llama3.2:1b", "qwen2.5:7b"]
    )
    assert result == {"llava:7b": ["completion", "vision"], "qwen2.5:7b": ["completion", "tools"]}
    # llama3.2:1b is absent (unknown), NOT falsely recorded as text-only.
    assert "llama3.2:1b" not in result


def test_enrich_empty_host_returns_empty(_clear_cache) -> None:
    assert enrich_capabilities("", ["llava:7b"]) == {}


def test_enrich_respects_max_models_cap(monkeypatch, _clear_cache) -> None:
    calls: list[str] = []

    def _post(url, payload, headers, timeout):
        calls.append(payload["model"])
        return {"capabilities": ["completion"]}

    monkeypatch.setattr("quill.core.ai_chat._post_json", _post)
    models = [f"m{i}" for i in range(50)]
    enrich_capabilities("http://localhost:11434", models, max_models=3)
    assert len(calls) == 3  # capped; the rest are left unknown, not silently dropped from UI
