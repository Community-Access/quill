"""Tests for the wx-free AI onboarding model."""

from __future__ import annotations

import quill.core.ai.onboarding as ob


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "onboarding_state_path", lambda: tmp_path / "ai" / "onboarding.json")


def test_paths_and_providers_are_well_formed() -> None:
    ids = {p.id for p in ob.ONBOARDING_PATHS}
    # on-device folded into the provider list; "agent" routes to the AI Hub Engines tab.
    assert ids == {"cloud", "agent", "skip"}
    assert all(p.title and p.summary and p.detail for p in ob.ONBOARDING_PATHS)
    assert ob.onboarding_path("agent").id == "agent"
    assert ob.onboarding_path("cloud").id == "cloud"
    assert ob.onboarding_path("nope") is None
    from quill.core.ai.providers import provider_requires_api_key

    # Cloud options are all keyed; the on-device option is local and needs no key.
    for opt in ob.CLOUD_PROVIDER_OPTIONS:
        assert opt.name and opt.blurb and opt.key_hint and opt.signup_url
        assert provider_requires_api_key(opt.id)
        assert not opt.local
    assert ob.ONDEVICE_PROVIDER_OPTION.local is True
    assert not provider_requires_api_key(ob.ONDEVICE_PROVIDER_OPTION.id)
    # Combined wizard list leads with on-device Ollama, then the requested cloud order.
    assert [p.id for p in ob.SETUP_PROVIDERS] == [
        "ollama",
        "ollama_cloud",
        "openai",
        "gemini",
        "claude",
        "openrouter",
    ]
    assert ob.cloud_provider_option("Claude").name.startswith("Claude")  # case-insensitive
    assert ob.cloud_provider_option("ollama").local is True  # local option is findable too
    assert ob.cloud_provider_option("nope") is None


def test_celebration_lines_are_tailored() -> None:
    on_device = ob.celebration_lines("on_device")
    assert any("connected" in line.lower() for line in on_device)
    assert any("Ask Quill" in line for line in on_device)
    cloud = ob.celebration_lines("cloud", provider_name="Claude")
    assert any("Claude" in line for line in cloud)
    skip = ob.celebration_lines("skip")
    assert any("off for now" in line.lower() for line in skip)
    assert not any("Ask Quill" in line for line in skip)
    agent = ob.celebration_lines("agent")
    assert any("Engines tab" in line for line in agent)
    assert any("Copilot" in line for line in agent)


def test_experience_mode_defaults_to_advanced_and_persists(tmp_path, monkeypatch) -> None:
    _isolate(tmp_path, monkeypatch)
    # Default is advanced so nothing is hidden from users who never opted into Basic.
    assert ob.load_experience_mode() == ob.EXPERIENCE_ADVANCED
    assert ob.is_basic_mode() is False
    ob.save_experience_mode(ob.EXPERIENCE_BASIC)
    assert ob.load_experience_mode() == ob.EXPERIENCE_BASIC
    assert ob.is_basic_mode() is True
    # Garbage falls back to advanced.
    ob.save_experience_mode("nonsense")
    assert ob.load_experience_mode() == ob.EXPERIENCE_ADVANCED


def test_completion_state_persists_and_resets(tmp_path, monkeypatch) -> None:
    _isolate(tmp_path, monkeypatch)
    assert ob.onboarding_complete() is False
    ob.mark_onboarding_complete()
    assert ob.onboarding_complete() is True
    ob.reset_onboarding()
    assert ob.onboarding_complete() is False


def test_ollama_status_classifies_reachability(monkeypatch) -> None:
    import quill.core.assistant_ai as aa

    # Reachable with models -> ok, returns a real installed model.
    monkeypatch.setattr(aa, "list_assistant_models", lambda *a, **k: (["gemma3:4b", "x"], None))
    ok, msg, model = ob.ollama_status()
    assert ok is True and msg == "" and model == "gemma3:4b"

    # Not running (error) -> not ok, friendly guidance, no model.
    monkeypatch.setattr(aa, "list_assistant_models", lambda *a, **k: ([], "connection refused"))
    ok, msg, model = ob.ollama_status()
    assert ok is False and "ollama.com" in msg.lower() and model == ""

    # Running but no models -> not ok, guidance to pull a model.
    monkeypatch.setattr(aa, "list_assistant_models", lambda *a, **k: ([], None))
    ok, msg, _model = ob.ollama_status()
    assert ok is False and "pull" in msg.lower()


def test_ai_connection_ready_probes_local_ollama(monkeypatch) -> None:
    import quill.core.assistant_ai as aa

    def _conn(provider, host="http://localhost:11434"):
        return aa.AssistantConnectionSettings(provider=provider, host=host, model="m")

    # Default local Ollama that is NOT running -> not ready, so callers offer setup
    # instead of letting the chat hang on "Thinking".
    monkeypatch.setattr(aa, "load_assistant_connection_settings", lambda: _conn("ollama"))
    monkeypatch.setattr(ob, "ollama_status", lambda host="": (False, "down", ""))
    assert ob.ai_connection_ready() is False

    # Local Ollama that answers -> ready.
    monkeypatch.setattr(ob, "ollama_status", lambda host="": (True, "", "llama3.2"))
    assert ob.ai_connection_ready() is True

    # Cloud provider with a stored key -> ready; without any key -> not ready.
    monkeypatch.setattr(aa, "load_assistant_connection_settings", lambda: _conn("claude"))
    monkeypatch.setattr(aa, "load_assistant_api_key", lambda: "")
    monkeypatch.setattr(ob, "stored_provider_key", lambda pid: "sk-123")
    assert ob.ai_connection_ready() is True
    monkeypatch.setattr(ob, "stored_provider_key", lambda pid: "")
    assert ob.ai_connection_ready() is False

    # Provider off -> not ready.
    monkeypatch.setattr(aa, "load_assistant_connection_settings", lambda: _conn("off"))
    assert ob.ai_connection_ready() is False


def test_provider_consent_grant_revoke_and_active(tmp_path, monkeypatch) -> None:
    _isolate(tmp_path, monkeypatch)
    import quill.core.assistant_ai as aa

    assert ob.provider_consent_granted("claude") is False
    ob.grant_provider_consent("Claude")  # stored case-insensitively
    assert ob.provider_consent_granted("claude") is True
    ob.grant_provider_consent("claude")  # idempotent
    assert ob.provider_consent_granted("claude") is True

    # active_connection_consented follows the active provider.
    def _conn(provider):
        return aa.AssistantConnectionSettings(provider=provider, host="h", model="m")

    monkeypatch.setattr(aa, "load_assistant_connection_settings", lambda: _conn("claude"))
    assert ob.active_connection_consented() is True
    monkeypatch.setattr(aa, "load_assistant_connection_settings", lambda: _conn("openai"))
    assert ob.active_connection_consented() is False

    ob.revoke_provider_consent("claude")
    assert ob.provider_consent_granted("claude") is False


def test_forget_provider_key_also_revokes_consent(tmp_path, monkeypatch) -> None:
    _isolate(tmp_path, monkeypatch)
    import quill.core.assistant_ai as aa

    monkeypatch.setattr(aa, "clear_provider_api_key", lambda pid: None)
    ob.grant_provider_consent("openai")
    assert ob.provider_consent_granted("openai") is True
    ob.forget_provider_key("openai")  # removing a provider withdraws consent too
    assert ob.provider_consent_granted("openai") is False


def test_apply_cloud_setup_configures_provider_key_and_enables(monkeypatch) -> None:
    import quill.core.ai.model_manager as mm
    import quill.core.assistant_ai as aa

    saved: dict[str, object] = {}
    # set_active_provider is the primitive that persists the connection AND mirrors the
    # key into the active-key store the generation path reads — saving only the
    # per-provider key left Ask Quill reporting "active provider: none" after setup.
    monkeypatch.setattr(aa, "set_active_provider", lambda s, k: saved.update(settings=s, key=k))
    monkeypatch.setattr(mm, "save_ai_enabled", lambda v: saved.update(enabled=v))

    ob.apply_cloud_setup("claude", "sk-test")
    assert saved["settings"].provider == "claude"
    assert saved["key"] == "sk-test"  # active key is set, not just the per-provider key
    assert saved["enabled"] is True
    assert saved["settings"].model  # a default model was filled in


def test_apply_on_device_setup_points_at_ollama_and_enables(monkeypatch) -> None:
    import quill.core.ai.model_manager as mm
    import quill.core.assistant_ai as aa

    saved: dict[str, object] = {}
    monkeypatch.setattr(aa, "set_active_provider", lambda s, k: saved.update(settings=s, key=k))
    monkeypatch.setattr(mm, "save_ai_enabled", lambda v: saved.update(enabled=v))

    ob.apply_on_device_setup()
    assert saved["settings"].provider == "ollama"
    assert "localhost" in saved["settings"].host
    assert saved["key"] == ""  # local Ollama clears the active key (needs none)
    assert saved["enabled"] is True


def test_list_provider_models_returns_models_or_error(monkeypatch) -> None:
    import quill.core.assistant_ai as aa

    monkeypatch.setattr(ob, "stored_provider_key", lambda p: "")
    monkeypatch.setattr(aa, "list_assistant_models", lambda *a, **k: (["m1", "m2", "m3"], None))
    models, error = ob.list_provider_models("ollama_cloud")
    assert models == ["m1", "m2", "m3"] and error == ""

    # An error from discovery is surfaced, never raised.
    monkeypatch.setattr(aa, "list_assistant_models", lambda *a, **k: ([], "connection refused"))
    models, error = ob.list_provider_models("ollama_cloud")
    assert models == [] and "refused" in error


def test_needs_setup_only_when_incomplete_and_ai_off(tmp_path, monkeypatch) -> None:
    _isolate(tmp_path, monkeypatch)
    import quill.core.ai.model_manager as mm

    # Fresh + AI off -> offer it.
    monkeypatch.setattr(mm, "load_ai_enabled", lambda: False)
    assert ob.ai_needs_setup() is True
    # AI already on -> never nag.
    monkeypatch.setattr(mm, "load_ai_enabled", lambda: True)
    assert ob.ai_needs_setup() is False
    # Completed -> never nag, even with AI off.
    monkeypatch.setattr(mm, "load_ai_enabled", lambda: False)
    ob.mark_onboarding_complete()
    assert ob.ai_needs_setup() is False
