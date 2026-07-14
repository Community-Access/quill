from __future__ import annotations

import json
from pathlib import Path

import pytest

import quill.core.ai.providers as providers
import quill.core.assistant_ai as assistant_ai


def test_assistant_connection_settings_round_trip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assistant_ai.save_assistant_connection_settings(
        assistant_ai.AssistantConnectionSettings(
            provider="openai",
            host="https://api.openai.com",
            model="gpt-4o-mini",
        )
    )
    loaded = assistant_ai.load_assistant_connection_settings()
    assert loaded.provider == "openai"
    assert loaded.host == "https://api.openai.com"
    assert loaded.model == "gpt-4o-mini"


def test_assistant_api_key_is_protected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(assistant_ai, "_save_api_key_with_credential_manager", lambda *_args: False)
    monkeypatch.setattr(assistant_ai, "_load_api_key_from_credential_manager", lambda: "")
    monkeypatch.setattr(assistant_ai, "protect_secret", lambda secret: f"enc:{secret}")
    monkeypatch.setattr(
        assistant_ai,
        "unprotect_secret",
        lambda secret: secret.removeprefix("enc:"),
    )
    assistant_ai.save_assistant_api_key("secret-value")
    assert assistant_ai.load_assistant_api_key() == "secret-value"


def test_assistant_api_key_prefers_credential_manager(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    saved: dict[str, str] = {}

    def _save(secret: str) -> bool:
        saved["secret"] = secret
        return True

    monkeypatch.setattr(assistant_ai, "_save_api_key_with_credential_manager", _save)
    monkeypatch.setattr(
        assistant_ai,
        "_load_api_key_from_credential_manager",
        lambda: saved.get("secret", ""),
    )
    assistant_ai.save_assistant_api_key("vault-secret")
    assert assistant_ai.load_assistant_api_key() == "vault-secret"
    assert not assistant_ai.assistant_secret_path().exists()


def test_clear_assistant_api_key_clears_both_stores(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # SEC-7: forgetting the key removes it from the credential manager *and* the
    # DPAPI fallback file, and reports whether anything was actually cleared.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    vault: dict[str, str] = {}

    monkeypatch.setattr(
        assistant_ai,
        "_save_api_key_with_credential_manager",
        lambda secret: vault.update(secret=secret) or True,
    )
    monkeypatch.setattr(
        assistant_ai,
        "_load_api_key_from_credential_manager",
        lambda: vault.get("secret", ""),
    )
    monkeypatch.setattr(
        assistant_ai,
        "_delete_api_key_from_credential_manager",
        lambda: vault.clear(),
    )

    assistant_ai.save_assistant_api_key("to-be-forgotten")
    assert assistant_ai.load_assistant_api_key() == "to-be-forgotten"

    assert assistant_ai.clear_assistant_api_key() is True
    assert assistant_ai.load_assistant_api_key() == ""
    assert not assistant_ai.assistant_secret_path().exists()
    assert vault == {}

    # Forgetting again, with nothing stored, reports that no key was present.
    assert assistant_ai.clear_assistant_api_key() is False


def test_clear_assistant_api_key_removes_dpapi_fallback_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # SEC-7: when only the on-disk DPAPI fallback exists (no credential
    # manager), forgetting still deletes the file and reports a clear.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(assistant_ai, "_save_api_key_with_credential_manager", lambda *_a: False)
    monkeypatch.setattr(assistant_ai, "_load_api_key_from_credential_manager", lambda: "")
    monkeypatch.setattr(assistant_ai, "_delete_api_key_from_credential_manager", lambda: None)
    monkeypatch.setattr(assistant_ai, "protect_secret", lambda secret: f"enc:{secret}")

    assistant_ai.save_assistant_api_key("disk-only-secret")
    assert assistant_ai.assistant_secret_path().exists()

    assert assistant_ai.clear_assistant_api_key() is True
    assert not assistant_ai.assistant_secret_path().exists()


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.parametrize(
    ("provider", "expected_host"),
    [
        ("openai", "https://api.openai.com"),
        ("claude", "https://api.anthropic.com"),
        ("openrouter", "https://openrouter.ai/api"),
        ("gemini", "https://generativelanguage.googleapis.com"),
    ],
)
def test_default_host_for_provider(provider: str, expected_host: str) -> None:
    assert assistant_ai.default_host_for_provider(provider) == expected_host


def test_settings_accepts_new_provider() -> None:
    settings = assistant_ai.AssistantConnectionSettings.from_dict({
        "provider": "gemini",
        "host": "https://generativelanguage.googleapis.com",
        "model": "gemini-2.0-flash",
    })
    assert settings.provider == "gemini"


def test_list_assistant_models_reads_openai_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        assistant_ai,
        "urlopen",
        lambda *_args, **_kwargs: _FakeResponse({
            "data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4.1"}]
        }),
    )
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com"
    )
    models, error = assistant_ai.list_assistant_models(settings, api_key="x")
    assert error is None
    assert models == ["gpt-4o-mini", "gpt-4.1"]


def test_verify_assistant_connection_reports_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Unauthorized(assistant_ai.HTTPError):
        def __init__(self) -> None:
            super().__init__(
                url="https://api.openai.com/v1/models",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=None,
            )

    def _raise(*_args, **_kwargs):
        raise _Unauthorized()

    monkeypatch.setattr(assistant_ai, "urlopen", _raise)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai",
        host="https://api.openai.com",
        model="gpt-4o-mini",
    )
    ok, message = assistant_ai.verify_assistant_connection(settings, api_key="bad-key")
    assert ok is False
    assert "Authentication failed" in message


def test_verify_assistant_connection_rejects_non_https_cloud_endpoint() -> None:
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai",
        host="http://api.openai.com",
        model="gpt-4o-mini",
    )
    ok, message = assistant_ai.verify_assistant_connection(settings, api_key="bad-key")
    assert ok is False
    assert "Only HTTPS endpoints are allowed" in message


def test_verify_assistant_connection_surfaces_unlock_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # L-5: when the on-disk key cannot be unlocked on this device, verify
    # should short-circuit with the screen-reader-friendly message instead
    # of the generic "unauthorized" from the provider.
    monkeypatch.setattr(assistant_ai, "assistant_secret_unlock_failed", lambda: True)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai",
        host="https://api.openai.com",
        model="gpt-4o-mini",
    )
    ok, message = assistant_ai.verify_assistant_connection(settings, api_key="")
    assert ok is False
    assert "encrypted for a different Windows user" in message
    assert "Open AI Connection" in message


def test_list_assistant_models_surfaces_unlock_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # L-5: same short-circuit for the list-models surface; no network call
    # is made when the saved key cannot be unlocked.
    monkeypatch.setattr(assistant_ai, "assistant_secret_unlock_failed", lambda: True)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai",
        host="https://api.openai.com",
        model="gpt-4o-mini",
    )
    models, error = assistant_ai.list_assistant_models(settings, api_key="")
    assert models == []
    assert error is not None
    assert "encrypted for a different Windows user" in error


def test_verify_assistant_connection_allows_local_custom_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        assistant_ai,
        "urlopen",
        lambda *_args, **_kwargs: _FakeResponse({"data": [{"id": "llama3.1:8b"}]}),
    )
    settings = assistant_ai.AssistantConnectionSettings(
        provider="custom",
        host="http://localhost:11434",
        model="llama3.1:8b",
    )
    ok, message = assistant_ai.verify_assistant_connection(settings, api_key="")
    assert ok is True
    assert "Connection verified" in message


def test_build_auth_headers_for_provider_types() -> None:
    assert "Authorization" in assistant_ai._build_auth_headers(
        "openai", "https://api.openai.com", "sk-1"
    )
    claude_headers = assistant_ai._build_auth_headers(
        "claude", "https://api.anthropic.com", "claude-key"
    )
    assert claude_headers["x-api-key"] == "claude-key"
    assert claude_headers["anthropic-version"] == "2023-06-01"
    gemini_headers = assistant_ai._build_auth_headers(
        "gemini", "https://generativelanguage.googleapis.com", "gem-key"
    )
    assert gemini_headers["x-goog-api-key"] == "gem-key"


def test_filter_model_names_prioritizes_prefix_matches() -> None:
    models = ["gpt-4o-mini", "claude-3-5-sonnet-latest", "gpt-4.1", "gemini-2.0-flash"]
    filtered = assistant_ai.filter_model_names(models, "gpt")
    assert filtered[0] == "gpt-4.1"
    assert "gpt-4o-mini" in filtered
    assert "claude-3-5-sonnet-latest" not in filtered


def test_recommended_models_for_provider_cloud_and_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(providers, "total_ram_gb", lambda: 6.0)
    local = assistant_ai.recommended_models_for_provider("ollama")
    assert local[0] == "llama3.2:1b-instruct-q4_K_M"
    cloud = assistant_ai.recommended_models_for_provider("openai")
    assert "gpt-4o-mini" in cloud


def test_ollama_cloud_default_and_recommended_models_are_real_ids() -> None:
    # Bare "qwen3"/"gemma3" 404 on ollama.com; every default/recommended cloud
    # model id must carry a size tag (or be a tagless flagship that exists).
    default = providers.default_model_for_provider("ollama_cloud")
    recommended = providers.recommended_models_for_provider("ollama_cloud")
    assert default == "gemma3:12b"
    assert "qwen3" not in recommended and "gemma3" not in recommended
    # The non-reasoning default leads so it works on chat and the agent path.
    assert recommended[0] == "gemma3:12b"


def test_parse_chat_response_falls_back_to_reasoning_when_content_empty() -> None:
    # Reasoning models (gpt-oss, some OpenRouter routes) leave `content` empty and
    # put the answer on a reasoning channel; we must surface it, not fail.
    payload = {"choices": [{"message": {"content": "", "reasoning_content": "the answer"}}]}
    assert assistant_ai.parse_chat_response("ollama_cloud", payload) == "the answer"
    payload2 = {"choices": [{"message": {"content": "", "reasoning": "alt channel"}}]}
    assert assistant_ai.parse_chat_response("openrouter", payload2) == "alt channel"
    # Normal content still wins over any reasoning field.
    payload3 = {"choices": [{"message": {"content": "real", "reasoning": "ignored"}}]}
    assert assistant_ai.parse_chat_response("openai", payload3) == "real"


def test_recommended_model_guidance_returns_framing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(providers, "total_ram_gb", lambda: 16.0)
    guidance = assistant_ai.recommended_model_guidance("ollama")
    assert guidance
    assert guidance[0].framing != ""


def _http_error(code: int, url: str = "https://api.openai.com/v1/models") -> Exception:
    return assistant_ai.HTTPError(url=url, code=code, msg="x", hdrs=None, fp=None)


def test_list_models_distinguishes_forbidden_from_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*_args, **_kwargs):
        raise _http_error(403)

    monkeypatch.setattr(assistant_ai, "urlopen", _raise)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com"
    )
    models, error = assistant_ai.list_assistant_models(settings, api_key="valid-key")
    assert models == []
    assert error is not None
    assert "Access denied" in error
    assert "Authentication failed" not in error


def test_list_models_unauthorized_still_reports_auth_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*_args, **_kwargs):
        raise _http_error(401)

    monkeypatch.setattr(assistant_ai, "urlopen", _raise)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com"
    )
    _models, error = assistant_ai.list_assistant_models(settings, api_key="bad-key")
    assert error is not None
    assert "Authentication failed" in error


def test_list_models_does_not_false_positive_on_port_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A healthy local endpoint whose URL merely contains "403" must not be
    # misread as an authentication failure.
    monkeypatch.setattr(
        assistant_ai,
        "urlopen",
        lambda *_a, **_k: _FakeResponse({"models": [{"name": "llama3.2:1b"}]}),
    )
    settings = assistant_ai.AssistantConnectionSettings(
        provider="ollama", host="http://localhost:11403"
    )
    models, error = assistant_ai.list_assistant_models(settings, api_key="")
    assert error is None
    assert models == ["llama3.2:1b"]


def test_list_models_reports_local_server_not_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(assistant_ai.time, "sleep", lambda *_a, **_k: None)

    def _raise(*_args, **_kwargs):
        raise assistant_ai.URLError(ConnectionRefusedError("refused"))

    monkeypatch.setattr(assistant_ai, "urlopen", _raise)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="ollama", host="http://localhost:11434"
    )
    _models, error = assistant_ai.list_assistant_models(settings, api_key="")
    assert error is not None
    assert "not running" in error.lower()


def test_list_models_retries_while_warming_up_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(assistant_ai.time, "sleep", lambda *_a, **_k: None)
    calls = {"n": 0}

    def _maybe_warm(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_error(503)
        return _FakeResponse({"data": [{"id": "gpt-4o-mini"}]})

    monkeypatch.setattr(assistant_ai, "urlopen", _maybe_warm)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com"
    )
    models, error = assistant_ai.list_assistant_models(settings, api_key="k")
    assert error is None
    assert models == ["gpt-4o-mini"]
    assert calls["n"] >= 2


def test_list_models_does_not_retry_auth_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(assistant_ai.time, "sleep", lambda *_a, **_k: None)
    calls = {"n": 0}

    def _raise(*_args, **_kwargs):
        calls["n"] += 1
        raise _http_error(401)

    monkeypatch.setattr(assistant_ai, "urlopen", _raise)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com"
    )
    _models, error = assistant_ai.list_assistant_models(settings, api_key="bad")
    assert error is not None and "Authentication failed" in error
    # Only the single candidate endpoint is tried; no warm-up retries.
    assert calls["n"] == 1


def test_assistant_secret_unlock_failed_detects_undecryptable_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(assistant_ai, "_load_api_key_from_credential_manager", lambda: "")
    monkeypatch.setattr(assistant_ai, "protect_secret", lambda secret: f"enc:{secret}")
    monkeypatch.setattr(assistant_ai, "_save_api_key_with_credential_manager", lambda *_a: False)
    assistant_ai.save_assistant_api_key("secret-value")

    # A secret that decrypts cleanly is not flagged.
    monkeypatch.setattr(assistant_ai, "unprotect_secret", lambda s: s.removeprefix("enc:"))
    assert assistant_ai.assistant_secret_unlock_failed() is False

    # A secret that cannot be unlocked here (moved portable install) is flagged.
    monkeypatch.setattr(assistant_ai, "unprotect_secret", lambda _s: "")
    assert assistant_ai.assistant_secret_unlock_failed() is True


def test_assistant_secret_unlock_failed_false_when_no_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(assistant_ai, "_load_api_key_from_credential_manager", lambda: "")
    assert assistant_ai.assistant_secret_unlock_failed() is False


# --- #120: Ollama Cloud model discovery --------------------------------------


def test_ollama_cloud_model_candidates_prefer_openai_endpoint() -> None:
    # Ollama Cloud is OpenAI-compatible; the full hosted catalog lives at
    # /v1/models, not the local-style /api/tags, so /v1/models must be queried.
    candidates = assistant_ai._model_endpoint_candidates("ollama_cloud", "https://ollama.com")
    assert candidates == ["https://ollama.com/v1/models"]
    assert "https://ollama.com/api/tags" not in candidates


def test_list_models_ollama_cloud_hits_openai_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    def _record(request, *_args, **_kwargs):
        seen.append(request.full_url)
        return _FakeResponse({"data": [{"id": "gpt-oss:120b"}, {"id": "qwen3:480b"}]})

    monkeypatch.setattr(assistant_ai, "urlopen", _record)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="ollama_cloud", host="https://ollama.com"
    )
    models, error = assistant_ai.list_assistant_models(settings, api_key="cloud-key")
    assert error is None
    assert models == ["gpt-oss:120b", "qwen3:480b"]
    assert seen == ["https://ollama.com/v1/models"]


def test_list_models_falls_through_empty_first_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A successful but empty first endpoint must not stop discovery while a
    # later candidate could still return the full catalog (#120 secondary bug).
    seen: list[str] = []

    def _by_endpoint(request, *_args, **_kwargs):
        seen.append(request.full_url)
        if request.full_url.endswith("/api/tags"):
            return _FakeResponse({"models": []})
        return _FakeResponse({"data": [{"id": "llama3.2:1b"}]})

    monkeypatch.setattr(assistant_ai, "urlopen", _by_endpoint)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="ollama", host="http://localhost:11434"
    )
    models, error = assistant_ai.list_assistant_models(settings, api_key="")
    assert error is None
    assert models == ["llama3.2:1b"]
    assert seen == [
        "http://localhost:11434/api/tags",
        "http://localhost:11434/v1/models",
    ]


# --- #123: verify with a blank required key fails ----------------------------


def test_verify_blank_key_fails_for_key_required_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ollama.com/api/tags answers 200 unauthenticated, so without the guard a
    # blank key would falsely verify. The network must not even be reached.
    def _boom(*_args, **_kwargs):
        raise AssertionError("network must not be called for a blank required key")

    monkeypatch.setattr(assistant_ai, "urlopen", _boom)
    settings = assistant_ai.AssistantConnectionSettings(
        provider="ollama_cloud", host="https://ollama.com"
    )
    ok, message = assistant_ai.verify_assistant_connection(settings, api_key="   ")
    assert ok is False
    assert "API key is required" in message
    assert "Ollama Cloud" in message


def test_verify_local_ollama_allows_blank_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Local Ollama needs no key, so a blank key must still verify.
    monkeypatch.setattr(
        assistant_ai,
        "urlopen",
        lambda *_a, **_k: _FakeResponse({"models": [{"name": "llama3.2:1b"}]}),
    )
    settings = assistant_ai.AssistantConnectionSettings(
        provider="ollama", host="http://localhost:11434"
    )
    ok, message = assistant_ai.verify_assistant_connection(settings, api_key="")
    assert ok is True
    assert "verified" in message.lower()


def test_verify_local_custom_http_allows_blank_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A custom OpenAI-compatible endpoint on loopback legitimately needs no key,
    # so the #123 guard must exempt local hosts even though "custom" requires a
    # key for remote endpoints.
    monkeypatch.setattr(
        assistant_ai,
        "urlopen",
        lambda *_a, **_k: _FakeResponse({"data": [{"id": "llama3.1:8b"}]}),
    )
    settings = assistant_ai.AssistantConnectionSettings(
        provider="custom", host="http://localhost:11434", model="llama3.1:8b"
    )
    ok, _message = assistant_ai.verify_assistant_connection(settings, api_key="")
    assert ok is True


def test_missing_required_api_key_rule() -> None:
    # Remote, key-required, blank key -> missing.
    assert assistant_ai.missing_required_api_key("ollama_cloud", "https://ollama.com", "") is True
    # Key supplied -> not missing.
    assert assistant_ai.missing_required_api_key("ollama_cloud", "https://ollama.com", "k") is False
    # Local custom endpoint -> exempt.
    assert assistant_ai.missing_required_api_key("custom", "http://localhost:1234", "") is False
    # Provider that needs no key -> never missing.
    assert assistant_ai.missing_required_api_key("ollama", "http://localhost:11434", "") is False


# --- #122: plain-language API key labels -------------------------------------


def test_api_key_labels_have_no_storage_jargon() -> None:
    jargon = ("Credential Manager", "DPAPI", "encrypted fallback")
    for provider in (
        "openai",
        "claude",
        "openrouter",
        "gemini",
        "ollama_cloud",
        "custom",
        "off",
    ):
        label = assistant_ai.provider_api_key_label(provider)
        for term in jargon:
            assert term not in label, f"{provider!r} label leaks jargon: {label!r}"


def test_api_key_storage_hint_is_plain_and_jargon_free() -> None:
    hint = assistant_ai.provider_api_key_storage_hint()
    assert "securely" in hint.lower()
    for term in ("Credential Manager", "DPAPI", "Windows", "encrypted fallback"):
        assert term not in hint


def test_provider_display_name_is_friendly() -> None:
    assert assistant_ai.provider_display_name("ollama_cloud") == "Ollama Cloud"
    assert assistant_ai.provider_display_name("openai") == "OpenAI"
    assert assistant_ai.provider_display_name("claude") == "Claude"


# --- Test Chat helper (AI Hub) -----------------------------------------------


def test_test_chat_off_provider_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = assistant_ai.AssistantConnectionSettings(provider="off")
    ok, message = assistant_ai.test_chat(settings, "")
    assert ok is False
    assert "Off" in message


def test_test_chat_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assistant_ai, "generate_assistant_response", lambda *a, **k: ("pong", None))
    settings = assistant_ai.AssistantConnectionSettings(provider="openai")
    ok, message = assistant_ai.test_chat(settings, "key")
    assert ok is True
    assert "pong" in message


def test_test_chat_error_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        assistant_ai, "generate_assistant_response", lambda *a, **k: (None, "Rate limited.")
    )
    settings = assistant_ai.AssistantConnectionSettings(provider="claude")
    ok, message = assistant_ai.test_chat(settings, "key")
    assert ok is False
    assert message == "Rate limited."


def test_test_chat_empty_reply_is_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assistant_ai, "generate_assistant_response", lambda *a, **k: ("   ", None))
    settings = assistant_ai.AssistantConnectionSettings(provider="gemini")
    ok, message = assistant_ai.test_chat(settings, "key")
    assert ok is False
    assert "empty" in message.lower()


# --- Per-provider credentials (AI Hub) ---------------------------------------


def _fake_credential_store(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    store: dict[str, str] = {}

    def _save(target, secret):
        store[target] = secret

    monkeypatch.setattr(assistant_ai, "_cs_save", _save)
    monkeypatch.setattr(assistant_ai, "_cs_load", lambda target: store.get(target, ""))
    monkeypatch.setattr(assistant_ai, "_cs_delete", lambda target: store.pop(target, None))
    return store


def test_per_provider_keys_are_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_credential_store(monkeypatch)
    assert assistant_ai.save_provider_api_key("openai", "openai-key") is True
    assert assistant_ai.save_provider_api_key("claude", "claude-key") is True
    assert assistant_ai.load_provider_api_key("openai") == "openai-key"
    assert assistant_ai.load_provider_api_key("claude") == "claude-key"
    # Distinct targets, so configuring one never clobbers another.
    openai_target = assistant_ai.provider_credential_target("openai")
    claude_target = assistant_ai.provider_credential_target("claude")
    assert openai_target != claude_target


def test_keyed_provider_key_prefers_per_provider_store(monkeypatch: pytest.MonkeyPatch) -> None:
    # Even when the active provider is something else, the per-provider OpenAI key
    # is used for a direct OpenAI call (Whisper / OpenAI TTS).
    _fake_credential_store(monkeypatch)
    assistant_ai.save_provider_api_key("openai", "openai-key")
    monkeypatch.setattr(
        assistant_ai,
        "load_assistant_connection_settings",
        lambda: assistant_ai.AssistantConnectionSettings(provider="claude"),
    )
    monkeypatch.setattr(assistant_ai, "load_assistant_api_key", lambda: "claude-active-key")
    assert assistant_ai.load_keyed_provider_api_key("openai") == "openai-key"


def test_keyed_provider_key_falls_back_to_active_only_when_provider_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_credential_store(monkeypatch)  # no per-provider openai key stored
    monkeypatch.setattr(
        assistant_ai,
        "load_assistant_connection_settings",
        lambda: assistant_ai.AssistantConnectionSettings(provider="openai"),
    )
    monkeypatch.setattr(assistant_ai, "load_assistant_api_key", lambda: "openai-active-key")
    assert assistant_ai.load_keyed_provider_api_key("openai") == "openai-active-key"


def test_keyed_provider_key_never_returns_another_providers_active_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The 401 bug: with no OpenAI key but an active Anthropic key, asking for the
    # OpenAI key must return "" rather than the Anthropic key (which OpenAI rejects).
    _fake_credential_store(monkeypatch)
    monkeypatch.setattr(
        assistant_ai,
        "load_assistant_connection_settings",
        lambda: assistant_ai.AssistantConnectionSettings(provider="claude"),
    )
    monkeypatch.setattr(assistant_ai, "load_assistant_api_key", lambda: "claude-active-key")
    assert assistant_ai.load_keyed_provider_api_key("openai") == ""


def test_clear_provider_api_key_only_affects_that_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_credential_store(monkeypatch)
    assistant_ai.save_provider_api_key("openai", "openai-key")
    assistant_ai.save_provider_api_key("gemini", "gemini-key")
    assistant_ai.clear_provider_api_key("openai")
    assert assistant_ai.load_provider_api_key("openai") == ""
    assert assistant_ai.load_provider_api_key("gemini") == "gemini-key"


def test_save_provider_api_key_empty_clears(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_credential_store(monkeypatch)
    assistant_ai.save_provider_api_key("openrouter", "k")
    assert assistant_ai.save_provider_api_key("openrouter", "  ") is False
    assert assistant_ai.load_provider_api_key("openrouter") == ""


def test_set_active_provider_persists_key_and_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    store = _fake_credential_store(monkeypatch)
    legacy_target = assistant_ai._ASSISTANT_CREDENTIAL_TARGET

    def _save_legacy(secret):
        store[legacy_target] = secret
        return True

    # Route the legacy active-key store through the same in-memory credential store.
    monkeypatch.setattr(assistant_ai, "_save_api_key_with_credential_manager", _save_legacy)
    monkeypatch.setattr(
        assistant_ai,
        "_load_api_key_from_credential_manager",
        lambda: store.get(legacy_target, ""),
    )
    settings = assistant_ai.AssistantConnectionSettings(provider="openai", model="gpt-4o-mini")
    assistant_ai.set_active_provider(settings, "active-key")
    assert assistant_ai.load_provider_api_key("openai") == "active-key"
    assert assistant_ai.load_assistant_api_key() == "active-key"
    assert assistant_ai.load_assistant_connection_settings().provider == "openai"


# --- Per-provider default model (AI Hub / Ask Quill) -------------------------


def test_per_provider_model_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assistant_ai.save_provider_model("openai", "gpt-4o-mini")
    assistant_ai.save_provider_model("claude", "claude-haiku-4-5-20251001")
    assert assistant_ai.load_provider_model("openai") == "gpt-4o-mini"
    assert assistant_ai.load_provider_model("claude") == "claude-haiku-4-5-20251001"
    assert assistant_ai.load_provider_model("gemini") == ""


def test_save_provider_model_empty_clears(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assistant_ai.save_provider_model("openrouter", "openrouter/auto")
    assistant_ai.save_provider_model("openrouter", "  ")
    assert assistant_ai.load_provider_model("openrouter") == ""


# ---------------------------------------------------------------------------
# Prompt caching: build_chat_body and build_chat_headers
# ---------------------------------------------------------------------------


def test_build_chat_body_claude_without_system_prompt() -> None:
    body = assistant_ai.build_chat_body("claude", "claude-3-5-sonnet-20241022", "Hello")
    assert "system" not in body
    assert body["messages"] == [{"role": "user", "content": "Hello"}]


def test_build_chat_body_claude_with_system_prompt_adds_cache_control() -> None:
    body = assistant_ai.build_chat_body(
        "claude", "claude-3-5-sonnet-20241022", "Hello", system_prompt="Be concise."
    )
    system = body.get("system")
    assert isinstance(system, list) and len(system) == 1
    block = system[0]
    assert block["type"] == "text"
    assert block["text"] == "Be concise."
    assert block["cache_control"] == {"type": "ephemeral"}
    assert body["messages"] == [{"role": "user", "content": "Hello"}]


def test_build_chat_body_openai_with_system_prompt_prepends_system_role() -> None:
    body = assistant_ai.build_chat_body("openai", "gpt-4o", "Hello", system_prompt="Be helpful.")
    messages = body["messages"]
    assert messages[0] == {"role": "system", "content": "Be helpful."}
    assert messages[1] == {"role": "user", "content": "Hello"}


def test_build_chat_body_openai_without_system_prompt_no_system_role() -> None:
    body = assistant_ai.build_chat_body("openai", "gpt-4o", "Hello")
    roles = [m["role"] for m in body["messages"]]
    assert "system" not in roles


def test_build_chat_body_gemini_with_system_prompt() -> None:
    body = assistant_ai.build_chat_body(
        "gemini", "gemini-2.0-flash", "Hello", system_prompt="Be precise."
    )
    assert "systemInstruction" in body
    assert body["systemInstruction"]["parts"][0]["text"] == "Be precise."


def test_build_chat_body_ollama_with_system_prompt() -> None:
    body = assistant_ai.build_chat_body("ollama", "llama3", "Hello", system_prompt="Be brief.")
    messages = body["messages"]
    assert messages[0] == {"role": "system", "content": "Be brief."}
    assert messages[1] == {"role": "user", "content": "Hello"}


def test_build_chat_headers_claude_no_cache_by_default() -> None:
    headers = assistant_ai.build_chat_headers("claude", "https://api.anthropic.com", "key123")
    assert "anthropic-beta" not in headers


def test_build_chat_headers_claude_with_cache_adds_beta_header() -> None:
    headers = assistant_ai.build_chat_headers(
        "claude", "https://api.anthropic.com", "key123", cache_system_prompt=True
    )
    assert headers.get("anthropic-beta") == "prompt-caching-2024-07-31"


def test_build_chat_headers_openai_does_not_get_anthropic_beta() -> None:
    headers = assistant_ai.build_chat_headers(
        "openai", "https://api.openai.com", "key123", cache_system_prompt=True
    )
    assert "anthropic-beta" not in headers
