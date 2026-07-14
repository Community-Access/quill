"""Lightweight AI chat client for the Ask AI dialog (Phase 2).

Supports OpenRouter (native and OpenAI-compatible mode), OpenAI, and Ollama
(local or cloud). All network calls are synchronous; the caller is responsible
for threading (use QuillTaskManager).
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING

from quill.core.assistant_ai import provider_credential_target
from quill.core.error_codes import CodedError

if TYPE_CHECKING:
    pass

TIMEOUT_CHAT_S = 60
TIMEOUT_MODELS_S = 10

_VERIFIED_CTX = ssl.create_default_context()


class AIChatError(CodedError):
    code = "QUILL-AI-CHAT-FAILED"


class AIChatCredentialError(AIChatError):
    pass


class AIChatTimeoutError(AIChatError):
    pass


class AIChatProviderError(AIChatError):
    pass


@dataclass
class AIModel:
    id: str
    display_name: str
    provider: str


def _post_json(url: str, payload: dict, headers: dict, timeout: int) -> dict:  # type: ignore[type-arg]
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_VERIFIED_CTX) as r:
            return json.loads(r.read())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode(errors="replace")[:300]
        except Exception:
            pass
        raise AIChatProviderError(f"HTTP {exc.code}: {body}") from exc
    except TimeoutError as exc:
        raise AIChatTimeoutError("Request timed out") from exc
    except Exception as exc:
        raise AIChatError(str(exc)) from exc


def _get_json(url: str, headers: dict, timeout: int) -> dict:  # type: ignore[type-arg]
    req = urllib.request.Request(url, headers=headers)
    try:
        ctx = _VERIFIED_CTX if url.startswith("https://") else None
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode(errors="replace")[:300]
        except Exception:
            pass
        raise AIChatProviderError(f"HTTP {exc.code}: {body}") from exc
    except TimeoutError as exc:
        raise AIChatTimeoutError("Model list fetch timed out") from exc
    except Exception as exc:
        raise AIChatError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Provider definitions
# ---------------------------------------------------------------------------

# One provider truth (§7): the ``credential_name`` for each keyed provider is the
# *canonical* per-provider credential target used by ``assistant_ai`` and the AI
# Hub, so this lightweight client and the main AI stack read/write the SAME key.
# A reversible startup migration (assistant_ai.consolidate_provider_keys) copies
# any key from the old ``quill-<provider>-api-key`` slot into the canonical one.
PROVIDERS: dict[str, dict] = {
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "needs_key": True,
        "credential_name": provider_credential_target("openrouter"),
        "mode": "openai_compat",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "needs_key": True,
        "credential_name": provider_credential_target("openai"),
        "mode": "openai_compat",
    },
    "ollama_local": {
        "label": "Ollama (local)",
        "base_url": "http://localhost:11434",
        "needs_key": False,
        "credential_name": None,
        "mode": "ollama",
    },
    "ollama_cloud": {
        "label": "Ollama Cloud",
        "base_url": "https://api.ollama.com",
        "needs_key": True,
        "credential_name": provider_credential_target("ollama_cloud"),
        "mode": "openai_compat",
    },
}


def list_models(provider_id: str, api_key: str = "", base_url: str = "") -> list[AIModel]:
    """Fetch model list for the given provider."""
    pdef = PROVIDERS.get(provider_id)
    if pdef is None:
        raise AIChatProviderError(f"Unknown provider: {provider_id}")
    url = base_url or pdef["base_url"]
    mode = pdef["mode"]

    if mode == "ollama":
        data = _get_json(f"{url}/api/tags", {}, TIMEOUT_MODELS_S)
        return [
            AIModel(id=m["name"], display_name=m["name"], provider=provider_id)
            for m in data.get("models", [])
        ]
    else:
        # OpenAI-compatible
        if not api_key and pdef["needs_key"]:
            raise AIChatCredentialError(f"No API key configured for {pdef['label']}")
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        data = _get_json(f"{url}/models", headers, TIMEOUT_MODELS_S)
        models = []
        for m in data.get("data", []):
            mid = m.get("id", "")
            if not mid or mid.startswith("~"):
                continue
            models.append(AIModel(id=mid, display_name=mid, provider=provider_id))
        models.sort(key=lambda m: m.id)
        return models


def list_models_raw(provider_id: str, api_key: str = "", base_url: str = "") -> list[dict]:  # type: ignore[type-arg]
    """Fetch the raw model dicts for a provider, preserving pricing metadata.

    Unlike :func:`list_models` (which projects to :class:`AIModel`), this keeps
    the full provider payload so callers can read fields like OpenRouter's
    ``pricing``. Reuses the audited ``_get_json`` egress site — no new network
    call site is introduced. OpenAI-compatible providers only; Ollama's
    ``/api/tags`` has no pricing and returns bare name entries.
    """
    pdef = PROVIDERS.get(provider_id)
    if pdef is None:
        raise AIChatProviderError(f"Unknown provider: {provider_id}")
    url = base_url or pdef["base_url"]
    if pdef["mode"] == "ollama":
        data = _get_json(f"{url}/api/tags", {}, TIMEOUT_MODELS_S)
        return [dict(m) for m in data.get("models", []) if isinstance(m, dict)]
    if not api_key and pdef["needs_key"]:
        raise AIChatCredentialError(f"No API key configured for {pdef['label']}")
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = _get_json(f"{url}/models", headers, TIMEOUT_MODELS_S)
    return [
        dict(m)
        for m in data.get("data", [])
        if isinstance(m, dict) and m.get("id") and not str(m.get("id", "")).startswith("~")
    ]


def send_prompt(
    provider_id: str,
    model_id: str,
    prompt: str,
    api_key: str = "",
    base_url: str = "",
    system_prompt: str = "",
) -> str:
    """Send a chat prompt and return the response text."""
    pdef = PROVIDERS.get(provider_id)
    if pdef is None:
        raise AIChatProviderError(f"Unknown provider: {provider_id}")
    url = base_url or pdef["base_url"]
    mode = pdef["mode"]

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    if mode == "ollama":
        payload = {"model": model_id, "messages": messages, "stream": False}
        data = _post_json(f"{url}/api/chat", payload, {}, TIMEOUT_CHAT_S)
        return data.get("message", {}).get("content", "")  # type: ignore[no-any-return]
    else:
        # OpenAI-compatible
        if not api_key and pdef["needs_key"]:
            raise AIChatCredentialError(f"No API key configured for {pdef['label']}")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 4096,
        }
        data = _post_json(f"{url}/chat/completions", payload, headers, TIMEOUT_CHAT_S)
        choices = data.get("choices", [])
        if not choices:
            raise AIChatProviderError("No choices in response")
        message = choices[0].get("message", {})
        content = str(message.get("content", "") or "")
        if content.strip():
            return content
        # Reasoning models (e.g. gpt-oss on Ollama Cloud) leave `content` empty
        # and put the answer on a reasoning channel; surface it rather than
        # returning an empty string the caller cannot use.
        for key in ("reasoning_content", "reasoning"):
            reasoning = message.get(key)
            if isinstance(reasoning, str) and reasoning.strip():
                return reasoning
        return content
