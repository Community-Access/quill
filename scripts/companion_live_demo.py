"""Live end-to-end proof of the QUILL Companion agent stack.

Drives the *real* agent path — ProviderChatBackend -> PromptToolPlanner ->
ConversationSession -> SafeEditorToolGateway -> EditorHost — against whatever AI
provider is configured (Claude, OpenAI, Ollama, ...). It is provider-agnostic:
swap the provider/model and the same loop runs. Output is a JSON document of the
scenario results on stdout, so a caller can render a report (e.g. fun.md).

Usage:
    python scripts/companion_live_demo.py [--model MODEL]

The model override is only needed when the configured model is not usable on this
machine (e.g. an un-pulled Ollama model); with Claude/OpenAI keys configured, omit
it. A headless FakeHost stands in for the wx editor so no UI is required; the
permission broker, diff preview, undo, and audit all still run.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from dataclasses import dataclass, field


@dataclass
class FakeHost:
    """Headless EditorHost: records edits, auto-approves previews/confirms."""

    document: str = ""
    selection: str = ""
    cursor: tuple[int, int] = (1, 1)
    section: str = ""
    flags: dict[str, bool] = field(default_factory=lambda: {"ai_enabled": True, "safe_mode": False})
    replacements: list[str] = field(default_factory=list)
    inserts: list[str] = field(default_factory=list)
    doc_writes: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)

    def get_document(self) -> str:
        return self.document

    def get_selection(self) -> str:
        return self.selection

    def get_outline(self) -> list[str]:
        return []

    def get_file_type(self) -> str:
        return "md"

    def get_cursor_position(self) -> tuple[int, int]:
        return self.cursor

    def get_current_section(self) -> str:
        return self.section

    def get_status_flags(self) -> dict[str, bool]:
        return self.flags

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

    def run_command(self, command_id: str) -> None:
        self.commands.append(command_id)

    def confirm(self, message: str) -> bool:
        return True

    def preview_diff(self, review: object) -> bool:
        return True

    def announce(self, message: str) -> None: ...


def _build_session(host: FakeHost, model: str | None):
    from quill.core.ai.activity_log import ActivityLog
    from quill.core.ai.conversation import ConversationSession
    from quill.core.ai.permissions import PermissionBroker, SafetyProfile
    from quill.core.ai.provider_backend import ProviderChatBackend
    from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway
    from quill.core.ai.tool_planner import PromptToolPlanner, model_responder_from_backend
    from quill.ui.agent_editor_host import _companion_agent

    settings = None
    if model:
        from quill.core.assistant_ai import load_assistant_connection_settings

        settings = dataclasses.replace(load_assistant_connection_settings(), model=model)
    backend = ProviderChatBackend(settings=settings)
    available, reason = backend.is_available()
    if not available:
        raise SystemExit(f"Provider unavailable: {reason}")

    agent = _companion_agent()
    gateway = SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(SafetyProfile.BALANCED, overrides=agent.overrides_map()),
        activity=ActivityLog(),
        identity=AgentIdentity(agent_id=agent.id, risk=agent.risk),
    )
    planner = PromptToolPlanner(model_responder_from_backend(backend))
    return ConversationSession(agent, gateway, planner, max_steps=5), backend


def _run_scenario(name, host, model, ask, *, context_text):
    session, backend = _build_session(host, model)
    start = time.time()
    result = session.ask(ask, context_text=context_text)
    return {
        "scenario": name,
        "provider": backend.settings.provider,
        "model": backend.settings.model,
        "prompt": ask,
        "answer": result.answer,
        "edited": result.edited,
        "status": result.status,
        "error": result.error,
        "tools_used": list(result.tools_used),
        "elapsed_seconds": round(time.time() - start, 1),
        "doc_after": host.document,
        "selection_after": host.selection,
        "replacements": host.replacements,
        "inserts": host.inserts,
    }


# Real research text gathered externally (QUILL in-app web research is Phase 5).
RESEARCH_TEXT = (
    "Research notes (Space Shuttle Challenger):\n"
    "- Challenger broke apart 73 seconds after launch on January 28, 1986, killing all "
    "seven crew members.\n"
    "- Immediate cause: two rubber O-rings failed to seal a joint on the right solid "
    "rocket booster in severe cold, letting hot exhaust gas escape.\n"
    "- Contributing factors: faulty SRB joint design, insufficient low-temperature "
    "testing, and poor communication across NASA management; the O-ring flaw had been "
    "known since 1977.\n"
    "- Afterward the booster was redesigned with three O-rings."
)


class FakeWeb:
    """A stand-in web-research backend (the real one is engine-native / Phase 5)."""

    def available(self) -> bool:
        return True

    def search(self, query, *, max_results=5):
        from quill.core.ai.web_research import WebResult

        return [
            WebResult(
                "Challenger disaster | Britannica",
                "https://www.britannica.com/event/Challenger-disaster",
                "Broke apart 73 seconds after launch on January 28, 1986; O-ring seal failure.",
            ),
            WebResult(
                "What Caused the Challenger Disaster? | HISTORY",
                "https://www.history.com/articles/how-the-challenger-disaster-changed-nasa",
                "Cold-stiffened O-rings, flawed booster joint design, NASA communication gaps.",
            ),
        ]

    def fetch(self, url):
        return "Fetched page text (demo)."


def capability_samples() -> dict:
    """Deterministic samples of the Phase 3-5 tools straight through the gateway."""
    from quill.core.ai.activity_log import ActivityLog
    from quill.core.ai.agent_catalog import load_catalog
    from quill.core.ai.concierge import ConciergeContext, suggest
    from quill.core.ai.permissions import PermissionBroker, RiskLevel, SafetyProfile
    from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway

    host = FakeHost(
        document=(
            "# Trip notes\n\nSee [click here](https://x.example) for the itinerary.\n\n"
            "### Day three\n\nWe hiked.\n"
        ),
        cursor=(5, 3),
        section="### Day three\n\nWe hiked.",
        flags={"ai_enabled": True, "safe_mode": False, "document_modified": True},
    )
    gateway = SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(SafetyProfile.POWER_USER),
        activity=ActivityLog(),
        identity=AgentIdentity(agent_id="quill-companion", risk=RiskLevel.LOW),
        web=FakeWeb(),
    )
    concierge = suggest(
        ConciergeContext(file_type="md", outline_headings=2, ai_enabled=True),
        load_catalog().agents,
        limit=4,
    )
    return {
        "read_app_state": gateway.read_app_state(),
        "read_current_section": gateway.read_current_section(),
        "audit_accessibility": gateway.audit_accessibility(),
        "web_search": gateway.web_search("Challenger disaster cause"),
        "concierge_suggestions": [f"{s.label} — {s.reason}" for s in concierge],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="Override the configured model id.")
    args = parser.parse_args()

    results = []

    # 1) Q&A about document content — should answer, not edit.
    qa_host = FakeHost(document="QUILL is an accessible, screen-reader-first word processor.")
    results.append(
        _run_scenario(
            "Q&A about the document",
            qa_host,
            args.model,
            "In one short sentence, what is this document about?",
            context_text=qa_host.document,
        )
    )

    # 2) Edit/revision — should call an edit tool and change the selection.
    edit_host = FakeHost(selection="the cat sat on teh mat")
    results.append(
        _run_scenario(
            "Edit the selection",
            edit_host,
            args.model,
            "Fix the spelling mistakes in the selected text and replace the selection "
            "with the corrected version.",
            context_text=edit_host.selection,
        )
    )

    # 3) Research -> refine -> document — turn web research into a cited paragraph.
    research_host = FakeHost(document="")
    results.append(
        _run_scenario(
            "Refine web research into the document",
            research_host,
            args.model,
            "Using the research notes provided as context, write a clear three-sentence "
            "summary of the Challenger disaster for a student's science paper, then "
            "insert it into the document.",
            context_text=RESEARCH_TEXT,
        )
    )

    json.dump({"results": results, "capabilities": capability_samples()}, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
