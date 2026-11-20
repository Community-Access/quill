"""Nothing goes to an AI the person did not choose (2026-11 data-routing fixes).

The wx-free half of the fixes for the audit in
``docs/qa/ai-and-settings-legibility-2026-11.md``: AI set to Off, a saved key
sent to the company it belongs to and nowhere else, and signing out leaving
nothing behind that keeps sending. Fakes only: no key is real, no network is
reached.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import quill.core.assistant_ai as aai
from quill.core.ai import own_key
from quill.core.assistant_ai import AssistantConnectionSettings

#: Captured at import, before tests/conftest.py stands it in with ``False``:
#: the own-key tests here are about what that function really answers.
_REAL_HAS_OWN_KEY = own_key.has_own_key

_ENV_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
    "OLLAMA_API_KEY",
)


class _Store:
    """In-memory stand-in for the OS credential store."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def load(self, name: str) -> str:
        return self.data.get(name, "")

    def save(self, name: str, value: str) -> None:
        self.data[name] = value

    def delete(self, name: str) -> None:
        self.data.pop(name, None)


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _Store:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    for name in _ENV_KEYS:
        monkeypatch.delenv(name, raising=False)
    fake = _Store()
    monkeypatch.setattr(aai, "_cs_load", fake.load)
    monkeypatch.setattr(aai, "_cs_save", fake.save)
    monkeypatch.setattr(aai, "_cs_delete", fake.delete)
    monkeypatch.setattr(own_key, "has_own_key", _REAL_HAS_OWN_KEY)
    return fake


def _connection(provider: str) -> AssistantConnectionSettings:
    return AssistantConnectionSettings(
        provider=provider,
        host=aai.default_host_for_provider(provider),
        model=aai.default_model_for_provider(provider) or "a-model",
    )


# -- 1. AI set to Off ---------------------------------------------------------- #


class _Backend:
    def __init__(self, name: str) -> None:
        self.name = name

    def is_available(self) -> tuple[bool, str]:
        return True, ""


def test_off_never_reaches_a_cloud_provider(monkeypatch: pytest.MonkeyPatch, store: _Store) -> None:
    """Off, with Ask Quill's chat setup naming OpenAI: nothing goes to OpenAI."""
    import quill.core.ai.llama_cpp_backend as llama
    import quill.core.ai.provider_backend as providers
    import quill.core.settings as settings_module
    from quill.core.ai.assistant import make_default_backend

    aai.save_assistant_connection_settings(_connection("off"))
    monkeypatch.setattr(providers, "SimpleChatBackend", lambda provider, _model: _Backend(provider))
    monkeypatch.setattr(
        settings_module,
        "load_settings",
        lambda: SimpleNamespace(
            ai_chat_default_provider="openai",
            ai_chat_default_model="gpt-4o-mini",
            ai_prompt_default_model="",
        ),
    )
    monkeypatch.setattr(llama, "LlamaCppBackend", lambda: _Backend("local"))
    monkeypatch.setattr("sys.platform", "win32")

    assert make_default_backend().name == "local"


# -- 8. Signing out leaves no copy behind ---------------------------------------- #


def test_signing_out_of_an_own_key_clears_the_older_key_store(store: _Store) -> None:
    aai.set_active_provider(_connection("claude"), "fake-claude-key")
    assert aai.load_assistant_api_key() == "fake-claude-key"

    aai.clear_provider_api_key("claude")

    assert aai.stored_assistant_api_key() == ""
    assert aai.load_assistant_api_key() == ""


def test_signing_out_of_another_provider_keeps_the_one_in_use(store: _Store) -> None:
    aai.set_active_provider(_connection("openai"), "fake-openai-key")
    aai.save_provider_api_key("gemini", "fake-gemini-key")

    aai.clear_provider_api_key("gemini")

    assert aai.load_assistant_api_key() == "fake-openai-key"


# -- 9. A key goes only to the company it belongs to ----------------------------- #


def test_a_saved_key_is_never_sent_to_a_different_company(store: _Store) -> None:
    from quill.core.ai.provider_backend import ProviderChatBackend

    aai.set_active_provider(_connection("openai"), "fake-openai-key")
    # The connection moves to Claude without a Claude key (a model pick, an
    # older window, a hand edit): the OpenAI key must not travel with it.
    aai.save_assistant_connection_settings(_connection("claude"))

    backend = ProviderChatBackend()

    assert backend.is_available()[0] is False
    assert aai.load_assistant_api_key() == ""


def test_an_older_install_with_one_key_keeps_working(store: _Store) -> None:
    """No owner was ever recorded: the one key is the active provider's."""
    from quill.core.ai.provider_backend import ProviderChatBackend

    aai.save_assistant_connection_settings(_connection("openai"))
    store.save(aai._ASSISTANT_CREDENTIAL_TARGET, "fake-old-key")

    assert ProviderChatBackend().is_available()[0] is True
    assert aai.load_assistant_api_key() == "fake-old-key"


def test_an_older_key_that_is_another_providers_is_refused(store: _Store) -> None:
    from quill.core.ai.provider_backend import ProviderChatBackend

    aai.save_assistant_connection_settings(_connection("claude"))
    store.save(aai._ASSISTANT_CREDENTIAL_TARGET, "fake-openai-key")
    aai.save_provider_api_key("openai", "fake-openai-key")

    assert ProviderChatBackend().is_available()[0] is False


# -- 2. Signing out of Ollama on this computer ---------------------------------- #


class _App:
    def __init__(self, provider: str) -> None:
        self.settings = SimpleNamespace(ai_own_key_provider=provider, ai_own_key_model="")
        self.saved = 0

    def save_settings(self) -> None:
        self.saved += 1


def _route(app: _App, connection: str = "own_key") -> Any:
    from quill.ui.hosted_ai_own_key_route import OwnKeyRouteMixin

    route = OwnKeyRouteMixin()
    route._app = app
    route.route = connection
    return route


def test_signing_out_of_ollama_never_moves_requests_to_the_cloud(store: _Store) -> None:
    aai.save_provider_api_key("openai", "fake-openai-key")
    app = _App("ollama")
    route = _route(app)
    assert route.own_key_active

    route.own_key_sign_out()

    assert route.own_key_provider != "openai"
    assert not route.own_key_ready  # "No AI is in use" is now true
    assert not route.own_key_active


def test_choosing_ollama_again_sets_it_up_again(store: _Store) -> None:
    from quill.core.ai import own_key_providers as providers

    has_own_key = _REAL_HAS_OWN_KEY
    _route(_App("ollama")).own_key_sign_out()
    assert not has_own_key("ollama")

    providers.mark_set_up("ollama")

    assert has_own_key("ollama")


def test_signing_out_keeps_a_saved_ollama_address(store: _Store) -> None:
    from quill.core.ai import own_key_providers as providers

    providers.save_host("ollama", "http://example.test:11434")
    _route(_App("ollama")).own_key_sign_out()

    assert providers.host_for("ollama") == "http://example.test:11434"
    providers.save_host("ollama", "http://example.test:11435")
    assert providers.signed_out("ollama")
