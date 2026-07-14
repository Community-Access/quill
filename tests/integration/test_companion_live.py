"""Live, provider-agnostic proof that the Companion agent stack actually works.

Drives the real path — ProviderChatBackend -> PromptToolPlanner ->
ConversationSession -> SafeEditorToolGateway -> headless host — against whatever AI
provider is configured (Claude, OpenAI, Ollama, ...). Skipped unless a provider is
configured AND answers a trivial ping, so CI without keys stays green; with a
Claude or OpenAI key configured it exercises that provider end to end.

Override the model when the configured one is not usable on this machine:
    QUILL_LIVE_MODEL=gemma4:31b-cloud pytest tests/integration/test_companion_live.py
"""

from __future__ import annotations

import dataclasses
import os

import pytest

_MODEL = os.environ.get("QUILL_LIVE_MODEL", "")


def _backend():
    from quill.core.ai.provider_backend import ProviderChatBackend

    settings = None
    if _MODEL:
        from quill.core.assistant_ai import load_assistant_connection_settings

        settings = dataclasses.replace(load_assistant_connection_settings(), model=_MODEL)
    return ProviderChatBackend(settings=settings)


def _provider_ready() -> bool:
    try:
        backend = _backend()
        ok, _ = backend.is_available()
        if not ok:
            return False
        reply = backend.respond("Reply with exactly one word: pong")
        return bool(reply and reply.strip())
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _provider_ready(),
    reason="No reachable AI provider configured (set one up, or QUILL_LIVE_MODEL).",
)


from dataclasses import dataclass, field  # noqa: E402


@dataclass
class _Host:
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


def _session(host: _Host):
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
    planner = PromptToolPlanner(model_responder_from_backend(_backend()))
    return ConversationSession(agent, gateway, planner, max_steps=5)


def test_question_is_answered_without_editing() -> None:
    host = _Host(document="QUILL is an accessible, screen-reader-first word processor.")
    result = _session(host).ask(
        "In one short sentence, what is this document about?", context_text=host.document
    )
    assert result.status == "completed"
    assert result.answer.strip()
    assert host.replacements == [] and host.inserts == [] and host.doc_writes == []


def test_edit_request_changes_the_selection() -> None:
    host = _Host(selection="the cat sat on teh mat")
    result = _session(host).ask(
        "Fix the spelling mistakes in the selected text and replace the selection.",
        context_text=host.selection,
    )
    assert result.status == "completed"
    # The model went through an editing tool and the buffer changed.
    assert host.replacements or host.inserts or host.doc_writes
    assert result.edited is True
