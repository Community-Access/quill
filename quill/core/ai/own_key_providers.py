"""Every provider "My own key" can use, in one table (codex.md decision 20, 10E.1).

My own key began with two providers, OpenAI and Google Gemini. The AI Hub
offered five more through its own Provider list -- Anthropic Claude,
OpenRouter, Ollama Cloud, a custom OpenAI-compatible service, and Ollama on
this computer -- and two ways to pick an AI was one too many. They are all
here now, in the order Use My Own AI Key lists them, and the AI Hub's list is
gone: the Hub's Provider page opens Use My Own AI Key instead.

What each row says:

* **The name** a person hears, and **whose account** a request is billed to.
* **Whether it needs a key.** Ollama on this computer does not: the model runs
  here, and its About line says exactly that -- "Runs on this computer.
  Nothing is sent." Every other provider needs the person's key, kept where
  QUILL has always kept each provider's key (Windows Credential Manager, or an
  encrypted file in a portable copy; :mod:`quill.core.assistant_ai`).
* **Whether the person gives the address.** A custom service and Ollama on
  this computer live where the person says; the address is kept per provider
  in ``assistant-own-key-hosts.json`` beside ``assistant-connection.json``, so
  a custom address saved in QUILL works in QUILL Lite too, as a key does. An
  address the AI Hub saved for the same provider is used until one is saved
  here, so nobody's custom service is lost in the move.
* **Where a key is made and where usage is**, as text to read, never opened
  behind the person's back.

**One choice, everywhere.** Saving a provider in Use My Own AI Key also makes
it the connection QUILL's advanced features use (Ask Quill, Run Agent, the AI
Library, Proofread, Transform and the rest), through the same
:func:`~quill.core.assistant_ai.set_active_provider` the AI Hub's list called.
That is what lets the Hub's list go without stranding a feature.

Models are never listed here: they come from the provider's own model list
(and, for Ollama, ``/api/tags`` with ``/api/show`` for what each model can do;
:mod:`quill.core.ai.own_key_models`).

wx-free and strict-typed.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ACCOUNT_NAMES",
    "CLAUDE",
    "COMPANIES",
    "CUSTOM",
    "GEMINI",
    "HOST_PROVIDERS",
    "KEYLESS_PROVIDERS",
    "KEY_URLS",
    "LOCAL_ABOUT",
    "OLLAMA",
    "OLLAMA_CLOUD",
    "OPENAI",
    "OPENROUTER",
    "PROVIDERS",
    "PROVIDER_NAMES",
    "USAGE_URLS",
    "host_for",
    "hosts_path",
    "is_local",
    "needs_key",
    "save_host",
    "use_for_advanced_features",
]

OPENAI = "openai"
GEMINI = "gemini"
CLAUDE = "claude"
OPENROUTER = "openrouter"
OLLAMA_CLOUD = "ollama_cloud"
CUSTOM = "custom"
OLLAMA = "ollama"

#: Every provider, in the order Use My Own AI Key lists them. The first two
#: keep their places so a listener's habit survives the longer list.
PROVIDERS: tuple[str, ...] = (OPENAI, GEMINI, CLAUDE, OPENROUTER, OLLAMA_CLOUD, CUSTOM, OLLAMA)

PROVIDER_NAMES: dict[str, str] = {
    OPENAI: "OpenAI",
    GEMINI: "Google Gemini",
    CLAUDE: "Anthropic Claude",
    OPENROUTER: "OpenRouter",
    OLLAMA_CLOUD: "Ollama Cloud",
    CUSTOM: "Custom OpenAI-compatible service",
    OLLAMA: "Ollama on this computer",
}

#: Whose account a request is billed to, for the cost sentences.
ACCOUNT_NAMES: dict[str, str] = {
    OPENAI: "OpenAI",
    GEMINI: "Google Gemini",
    CLAUDE: "Anthropic",
    OPENROUTER: "OpenRouter",
    OLLAMA_CLOUD: "Ollama",
    CUSTOM: "the service's",
    OLLAMA: "",
}

#: Who receives the text, for the About line and the picture consent.
COMPANIES: dict[str, str] = {
    OPENAI: "OpenAI",
    GEMINI: "Google",
    CLAUDE: "Anthropic",
    OPENROUTER: "OpenRouter",
    OLLAMA_CLOUD: "Ollama",
    CUSTOM: "the service at the address you gave",
    OLLAMA: "Ollama on this computer",
}

KEY_URLS: dict[str, str] = {
    OPENAI: "platform.openai.com, under API keys",
    GEMINI: "aistudio.google.com/apikey (Google AI Studio)",
    CLAUDE: "console.anthropic.com, under API keys",
    OPENROUTER: "openrouter.ai/keys",
    OLLAMA_CLOUD: "ollama.com/settings/keys",
    CUSTOM: "the service's own settings",
    OLLAMA: "",
}

USAGE_URLS: dict[str, str] = {
    OPENAI: "https://platform.openai.com/usage",
    GEMINI: "https://aistudio.google.com/usage",
    CLAUDE: "https://console.anthropic.com/settings/usage",
    OPENROUTER: "https://openrouter.ai/activity",
    OLLAMA_CLOUD: "https://ollama.com/settings",
    CUSTOM: "",
    OLLAMA: "",
}

#: Providers that need no key: the model runs on this computer.
KEYLESS_PROVIDERS = frozenset({OLLAMA})

#: Providers whose address the person gives.
HOST_PROVIDERS = frozenset({CUSTOM, OLLAMA})

#: The About line for a provider that runs here (decision 20, word for word).
LOCAL_ABOUT = "Runs on this computer. Nothing is sent."

_HOSTS_FILE = "assistant-own-key-hosts.json"


def needs_key(provider: str) -> bool:
    """Whether *provider* needs the person's key (every provider but local Ollama)."""
    return provider not in KEYLESS_PROVIDERS


def is_local(provider: str) -> bool:
    """Whether requests to *provider* stay on this computer."""
    return provider == OLLAMA


def hosts_path() -> Any:
    """``assistant-own-key-hosts.json``, beside the AI Hub's connection file."""
    from quill.core.assistant_ai import assistant_connection_path

    return assistant_connection_path().parent / _HOSTS_FILE


def _saved_hosts() -> dict[str, str]:
    from quill.core.storage import read_json

    raw = read_json(hosts_path(), default={})
    hosts = raw.get("hosts", {}) if isinstance(raw, dict) else {}
    return {str(k): str(v) for k, v in hosts.items()} if isinstance(hosts, dict) else {}


def host_for(provider: str) -> str:
    """The address requests to *provider* go to.

    For a provider with a fixed address, its own. For a custom service or
    Ollama on this computer: the address saved here, else the one the AI Hub
    saved for the same provider, else the provider's default.
    """
    from quill.core.assistant_ai import default_host_for_provider

    if provider not in HOST_PROVIDERS:
        return default_host_for_provider(provider)
    saved = _saved_hosts().get(provider, "").strip()
    if saved:
        return saved.rstrip("/")
    try:
        from quill.core.assistant_ai import load_assistant_connection_settings

        hub = load_assistant_connection_settings()
        if hub.provider == provider and hub.host.strip():
            return hub.host.strip().rstrip("/")
    except Exception:  # noqa: BLE001 - an unreadable Hub file means the default
        pass
    return default_host_for_provider(provider)


def save_host(provider: str, host: str) -> None:
    """Keep *host* for *provider* (only a provider whose address the person gives).

    Saving the provider's own default forgets the saved one, so nothing is
    written for a person who never changed it.
    """
    if provider not in HOST_PROVIDERS:
        return
    from quill.core.assistant_ai import default_host_for_provider
    from quill.core.storage import write_json_atomic

    value = host.strip().rstrip("/")
    hosts = _saved_hosts()
    if not value or value == default_host_for_provider(provider):
        if provider not in hosts:
            return
        hosts.pop(provider, None)
    else:
        hosts[provider] = value
    write_json_atomic(hosts_path(), {"schema_version": 1, "hosts": hosts})


def use_for_advanced_features(provider: str, model: str) -> None:
    """Make *provider* the connection the advanced AI features use (the Hub's old job).

    The key stays where it is; it is read only to mirror it into the store the
    advanced generation path reads, exactly as the AI Hub's list did.
    """
    from quill.core.assistant_ai import (
        AssistantConnectionSettings,
        load_provider_api_key,
        set_active_provider,
    )

    key = load_provider_api_key(provider) if needs_key(provider) else ""
    set_active_provider(
        AssistantConnectionSettings(provider=provider, host=host_for(provider), model=model),
        key,
    )
