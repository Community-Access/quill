"""Cross-SDK acceptance matrix: every catalog agent runs on every engine.

Proves the headline promise — each agent in the catalog runs on the Native harness
AND each SDK pack (OpenAI / Claude / Copilot), driving the SAME gateway and applying
the model's output through the reviewed editor path. The SDK packs use an injected
transport (no real SDK / network), so this is deterministic in CI; the live runs are
validated separately. 15 agents x 4 engines = 60 cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from quill.ai_packs import ClaudeAgentHarness, CopilotHarness, OpenAIAgentsHarness
from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.agent_catalog import load_catalog
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import AgentSpec, AIContext
from quill.core.ai.harness.native import NativeHarness
from quill.core.ai.permissions import PermissionBroker, RiskLevel, SafetyProfile
from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway

AGENTS = load_catalog().agents
ENGINES = ("native", "openai", "claude", "copilot")


@dataclass
class FakeHost:
    selection: str = "the original selection"
    document: str = "the original document body"
    replacements: list[str] = field(default_factory=list)
    inserts: list[str] = field(default_factory=list)
    doc_writes: list[str] = field(default_factory=list)

    def get_document(self) -> str:
        return self.document

    def get_selection(self) -> str:
        return self.selection

    def get_outline(self) -> list[str]:
        return ["Intro", "Body"]

    def get_file_type(self) -> str:
        return "md"

    def create_undo_checkpoint(self, label: str) -> None: ...

    def apply_replacement(self, text: str) -> None:
        self.replacements.append(text)

    def apply_insert(self, text: str) -> None:
        self.inserts.append(text)

    def apply_document_text(self, text: str) -> None:
        self.doc_writes.append(text)

    def run_command(self, command_id: str) -> None: ...

    def confirm(self, message: str) -> bool:
        return True

    def preview_diff(self, review: object) -> bool:
        return True

    def announce(self, message: str) -> None: ...


def _engine(name: str, transport):  # type: ignore[no-untyped-def]
    if name == "native":
        return NativeHarness(transport)
    if name == "openai":
        return OpenAIAgentsHarness(invoke=transport)
    if name == "claude":
        return ClaudeAgentHarness(invoke=transport)
    if name == "copilot":
        return CopilotHarness(invoke=transport)
    raise AssertionError(name)


@pytest.mark.parametrize("engine_name", ENGINES)
@pytest.mark.parametrize("agent", AGENTS, ids=lambda a: a.id)
def test_agent_runs_on_engine(agent: AgentSpec, engine_name: str, tmp_path: Path) -> None:
    host = FakeHost()
    events: list[AgentEvent] = []
    gateway = SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(SafetyProfile.POWER_USER),
        activity=ActivityLog(tmp_path / "a.json"),
        identity=AgentIdentity(agent_id=agent.id, risk=RiskLevel.LOW),
        emit=events.append,
    )
    output = f"[{engine_name}] result for {agent.id}"

    def transport(_agent: AgentSpec, _ctx: AIContext) -> str:
        return output

    engine = _engine(engine_name, transport)
    session = engine.start_session(
        agent,
        AIContext(prompt="improve it", context_text="some source text"),
        gateway,
        PermissionBroker(SafetyProfile.POWER_USER),
        events.append,
    )
    result = session.run()

    assert result.status == "completed"
    assert result.final_text == output
    # The output reached the editor through the gateway (replace for selection/
    # section scopes, insert otherwise).
    assert output in (host.replacements + host.inserts)
    assert AgentEventKind.AGENT_COMPLETED in [e.kind for e in events]


def test_matrix_covers_every_agent_and_engine() -> None:
    # Guard: the launch + rich set is present and the matrix is non-trivial.
    ids = {a.id for a in AGENTS}
    for expected in {
        "writing-companion",
        "accessibility-editor",
        "plain-language-rewriter",
        "citation-link-fixer",
        "meeting-notes-to-actions",
        "data-cleaner",
    }:
        assert expected in ids
    assert len(AGENTS) >= 15
    assert len(ENGINES) == 4
