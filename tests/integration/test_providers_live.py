"""Live, multi-provider regression proof for the AI stack (manual / nightly).

Exercises every configured cloud provider across the full spectrum the user
relies on -- a plain response (chat), an answered question over document context
(conversation), and a real tool-gateway edit (agent) -- to confirm the world is
good end to end. It drives the same path as ``test_companion_live.py`` but fans
out across providers and injects each key explicitly, so it never reads or writes
the user's credential store.

Cost is deliberately conservative: cheap models only, tiny prompts, a low
``max_steps`` tool budget, and at most a handful of small-model calls per
provider. CI without keys stays green because the whole module skips unless a
keys file is provided.

Run it by pointing QUILL_LIVE_KEYS_FILE at a JSON file of ``{provider: api_key}``::

    QUILL_LIVE_KEYS_FILE=/path/to/live_keys.json pytest tests/integration/test_providers_live.py -v

Recognized provider ids: claude, openai, gemini, openrouter, ollama_cloud.
Override the model for one provider with QUILL_LIVE_MODEL_<PROVIDER> (upper-case),
e.g. QUILL_LIVE_MODEL_OLLAMA_CLOUD=qwen3:32b.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import pytest

# Cheapest reliable model per provider. Kept small on purpose; override via
# QUILL_LIVE_MODEL_<PROVIDER> when a default is not enabled on the account.
_CHEAP_MODEL = {
    "claude": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "openrouter": "openai/gpt-4o-mini",
    "ollama_cloud": "gemma3:12b",
}


def _load_keys() -> dict[str, str]:
    path = os.environ.get("QUILL_LIVE_KEYS_FILE", "").strip()
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return {
        str(k).strip().lower(): str(v).strip()
        for k, v in data.items()
        if str(k).strip().lower() in _CHEAP_MODEL and str(v).strip()
    }


_KEYS = _load_keys()
_PROVIDERS = sorted(_KEYS)

pytestmark = pytest.mark.skipif(
    not _PROVIDERS,
    reason="No live keys file (set QUILL_LIVE_KEYS_FILE to a {provider: key} JSON).",
)


def _model_for(provider: str) -> str:
    override = os.environ.get(f"QUILL_LIVE_MODEL_{provider.upper()}", "").strip()
    return override or _CHEAP_MODEL[provider]


def _backend(provider: str):
    from quill.core.ai.provider_backend import ProviderChatBackend
    from quill.core.ai.providers import default_host_for_provider
    from quill.core.assistant_ai import AssistantConnectionSettings

    settings = AssistantConnectionSettings(
        provider=provider,
        host=default_host_for_provider(provider),
        model=_model_for(provider),
    )
    return ProviderChatBackend(settings=settings, api_key=_KEYS[provider])


@dataclass
class _Host:
    """Headless editor surface matching the gateway host protocol."""

    document: str = ""
    selection: str = ""
    replacements: list[str] = field(default_factory=list)
    inserts: list[str] = field(default_factory=list)
    doc_writes: list[str] = field(default_factory=list)

    def get_document(self) -> str:
        return self.document

    def get_selection(self) -> str:
        return self.selection

    def get_outline(self) -> list[str]:
        return []

    def get_file_type(self) -> str:
        return "md"

    def create_undo_checkpoint(self, label: str) -> None: ...

    def apply_replacement(self, text: str) -> None:
        self.replacements.append(text)
        self.selection = text

    def apply_insert(self, text: str) -> None:
        self.inserts.append(text)
        self.document += text

    def apply_document_text(self, text: str) -> None:
        self.doc_writes.append(text)
        self.document = text

    def run_command(self, command_id: str) -> None: ...

    def confirm(self, message: str) -> bool:
        return True

    def preview_diff(self, review: object) -> bool:
        return True

    def announce(self, message: str) -> None: ...

    def edited(self) -> bool:
        return bool(self.replacements or self.inserts or self.doc_writes)


def _session(provider: str, host: _Host):
    from quill.core.ai.activity_log import ActivityLog
    from quill.core.ai.conversation import ConversationSession
    from quill.core.ai.permissions import PermissionBroker, SafetyProfile
    from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway
    from quill.core.ai.tool_planner import PromptToolPlanner, model_responder_from_backend
    from quill.ui.agent_editor_host import _companion_agent

    agent = _companion_agent()
    gateway = SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(SafetyProfile.BALANCED, overrides=agent.overrides_map()),
        activity=ActivityLog(),
        identity=AgentIdentity(agent_id=agent.id, risk=agent.risk),
    )
    planner = PromptToolPlanner(model_responder_from_backend(_backend(provider)))
    return ConversationSession(agent, gateway, planner, max_steps=4)


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_provider_responds(provider: str) -> None:
    """Chat: the provider returns a non-empty response (smallest possible call)."""
    backend = _backend(provider)
    ok, reason = backend.is_available()
    assert ok, f"{provider} not available: {reason}"
    reply = backend.respond("Reply with exactly one word: pong")
    assert reply and reply.strip(), f"{provider} returned an empty response"


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_provider_answers_question_without_editing(provider: str) -> None:
    """Conversation: answers from document context and leaves the buffer alone."""
    host = _Host(document="QUILL is an accessible, screen-reader-first word processor.")
    result = _session(provider, host).ask(
        "In one short sentence, what is this document about?", context_text=host.document
    )
    assert result.status == "completed", f"{provider}: status was {result.status}"
    assert result.answer.strip(), f"{provider}: empty answer"
    assert not host.edited(), f"{provider}: a read-only question edited the buffer"


@pytest.mark.parametrize("provider", _PROVIDERS)
def test_provider_edits_selection_through_gateway(provider: str) -> None:
    """Agent: an edit request goes through a tool and changes the buffer."""
    host = _Host(selection="the cat sat on teh mat")
    result = _session(provider, host).ask(
        "Fix the spelling mistakes in the selected text and replace the selection.",
        context_text=host.selection,
    )
    assert result.status == "completed", f"{provider}: status was {result.status}"
    assert host.edited(), f"{provider}: the buffer was never edited"
    assert result.edited is True, f"{provider}: result.edited was False"


@pytest.mark.skipif(
    "openrouter" not in _KEYS,
    reason="No OpenRouter key in the live keys file.",
)
def test_openrouter_free_model_writes() -> None:
    """The free path end to end: a zero-priced OpenRouter model rewrites text.

    Proves that (1) the free catalog can discover a genuinely free model from live
    pricing, and (2) that model produces usable writing output — the whole promise
    of the free-AI-for-everyone path. Costs nothing (free model, tiny prompt).
    """
    from quill.core.ai import free_models
    from quill.core.ai.provider_backend import ProviderChatBackend
    from quill.core.ai.providers import default_host_for_provider
    from quill.core.assistant_ai import AssistantConnectionSettings

    key = _KEYS["openrouter"]
    classified = free_models.fetch_classified_models("openrouter", api_key=key)
    free = free_models.free_models(classified)
    assert free, "OpenRouter returned no free models to classify"
    model = free[0].id
    assert free_models.is_free_model(model), f"picked model {model} is not free"

    settings = AssistantConnectionSettings(
        provider="openrouter",
        host=default_host_for_provider("openrouter"),
        model=model,
    )
    backend = ProviderChatBackend(settings=settings, api_key=key)
    ok, reason = backend.is_available()
    assert ok, f"free model {model} not available: {reason}"
    reply = backend.respond("Rewrite more clearly, return only the text: 'me want go store'")
    assert reply and reply.strip(), f"free model {model} returned an empty response"
