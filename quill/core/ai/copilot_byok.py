"""Build a Copilot SDK BYOK connection from the explicitly chosen AI provider."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

__all__ = [
    "CopilotByokConnection",
    "SUPPORTED_BYOK_PROVIDERS",
    "load_selected_connection",
    "make_connection",
]

SUPPORTED_BYOK_PROVIDERS: dict[str, str] = {
    "openai": "openai",
    "gemini": "google",
    "claude": "anthropic",
    "openrouter": "openai",
    "ollama_cloud": "openai",
    "custom": "openai",
}

_PROVIDER_PATHS = {
    "openai": "/v1",
    "gemini": "/v1beta",
    "openrouter": "/v1",
    "ollama_cloud": "/v1",
    "claude": "",
}


@dataclass(frozen=True, slots=True)
class CopilotByokConnection:
    """Validated route details; the user's key is intentionally omitted from repr."""

    provider: str
    provider_type: str
    base_url: str
    model: str
    api_key: str = field(repr=False)
    local_only: bool = False

    def inference_options(self) -> dict[str, object]:
        """The SDK 2 session inference config for this one named provider."""
        provider: dict[str, str] = {
            "name": "quill_user",
            "type": self.provider_type,
            "base_url": self.base_url,
        }
        if self.api_key:
            provider["api_key"] = self.api_key
        return {
            "default_provider": "quill_user",
            "providers": [provider],
        }


def _is_loopback(hostname: str) -> bool:
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _validated_url(provider: str, host: str) -> tuple[str, bool]:
    raw = host.strip()
    parsed = urlsplit(raw)
    hostname = parsed.hostname or ""
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("The provider address must be an HTTP(S) URL without credentials.")
    local = _is_loopback(hostname)
    if parsed.scheme != "https" and not local:
        raise ValueError("A remote provider address must use HTTPS.")
    if provider == "custom" and parsed.path in {"", "/"}:
        parsed = parsed._replace(path="/v1")
    elif provider in _PROVIDER_PATHS:
        required_path = _PROVIDER_PATHS[provider]
        path = parsed.path.rstrip("/")
        if required_path and not path.endswith(required_path):
            path = f"{path}{required_path}"
        parsed = parsed._replace(path=path)
    return urlunsplit(parsed).rstrip("/"), local


def make_connection(
    provider: str,
    model: str,
    host: str,
    api_key: str,
) -> CopilotByokConnection:
    """Validate a chosen provider route without making a network request."""
    normalized = provider.strip().lower()
    provider_type = SUPPORTED_BYOK_PROVIDERS.get(normalized)
    if provider_type is None:
        raise ValueError("This provider is not supported for Copilot SDK agent tasks.")
    chosen_model = model.strip()
    if not chosen_model:
        raise ValueError("Choose a model before using this provider for agent tasks.")
    base_url, local = _validated_url(normalized, host)
    key = api_key.strip()
    if not key and not local:
        raise ValueError("Save this provider's API key securely before using agent tasks.")
    return CopilotByokConnection(
        provider=normalized,
        provider_type=provider_type,
        base_url=base_url,
        model=chosen_model,
        api_key=key,
        local_only=local,
    )


def load_selected_connection(
    provider: str,
    model: str,
) -> CopilotByokConnection:
    """Load only the key explicitly saved for *provider*; never borrow env keys."""
    from quill.core.ai.own_key_providers import host_for
    from quill.core.assistant_ai import stored_provider_api_key

    normalized = provider.strip().lower()
    host = host_for(normalized)
    key = stored_provider_api_key(normalized)
    return make_connection(normalized, model, host, key)
