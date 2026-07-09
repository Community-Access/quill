"""Optional SDK harness packs: availability, capabilities, registration, bridge."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from quill.ai_packs import all_packs, register_all
from quill.ai_packs._base import SdkHarness
from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.context_builder import ContextScope
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import AgentSpec, AIContext, HarnessCapabilities, HarnessRegistry
from quill.core.ai.permissions import PermissionBroker, RiskLevel, SafetyProfile
from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway

PACK_IDS = {
    "copilot",
    "claude_agent_sdk",
    "openai_agents",
}


@dataclass
class FakeHost:
    selection: str = "old"
    replacements: list[str] = field(default_factory=list)
    inserts: list[str] = field(default_factory=list)
    checkpoints: list[str] = field(default_factory=list)
    announcements: list[str] = field(default_factory=list)

    def get_document(self) -> str:
        return "doc"

    def get_selection(self) -> str:
        return self.selection

    def get_outline(self) -> list[str]:
        return []

    def get_file_type(self) -> str:
        return "markdown"

    def create_undo_checkpoint(self, label: str) -> None:
        self.checkpoints.append(label)

    def apply_replacement(self, text: str) -> None:
        self.replacements.append(text)

    def apply_insert(self, text: str) -> None:
        self.inserts.append(text)

    def apply_document_text(self, text: str) -> None: ...

    def run_command(self, command_id: str) -> None: ...

    def confirm(self, message: str) -> bool:
        return True

    def preview_diff(self, review: object) -> bool:
        return True

    def announce(self, message: str) -> None:
        self.announcements.append(message)


def test_all_packs_present() -> None:
    assert {p.id for p in all_packs()} == PACK_IDS


def test_packs_report_status_consistently() -> None:
    # Installation-agnostic: a pack is either available (its SDK is installed) or
    # reports a reason naming its extra. CI usually has none installed; a dev
    # machine may have some (e.g. openai-agents), and both must hold.
    for pack in all_packs():
        available, reason = pack.is_available()
        if available:
            assert reason is None
        else:
            assert reason is not None and pack.extra in reason


def test_crash_interrupted_install_reports_unavailable_not_stuck(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression (support report): "OpenAI shows up as being active; however, I
    can't actually switch to it or add my existing API key" after Quill crashed
    "downloading the OpenAI package".

    An on-demand pack install (``sdk_install.install_pack``) writes wheel-only
    files into a user-writable ``--target`` directory; if the host process
    crashes partway through, some files land and others don't. Before this fix,
    ``SdkHarness.is_available()`` used only ``importlib.util.find_spec``, which
    is satisfied the moment *any* file resolving the module exists — so a
    package whose ``__init__.py`` landed but whose real body did not would be
    reported "available" forever. The AI Hub's Engines tab and the AI Setup
    Wizard both trust ``is_available()`` to decide "Active"/"Available" vs
    "Not installed"; a false-positive there is exactly the stuck state in the
    report: the engine looks configured, Set Up short-circuits with "already
    installed" instead of retrying, and there is no other path back to a
    working configuration.
    """
    pkg_dir = tmp_path / "quill_crashed_pack"
    pkg_dir.mkdir()
    # Simulate the crash: __init__.py was written, but it imports a submodule
    # that never made it to disk before the process died.
    (pkg_dir / "__init__.py").write_text(
        "from . import never_written_submodule\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("quill_crashed_pack", None)
    importlib.invalidate_caches()

    class CrashedInstallPack(SdkHarness):
        pack_id = "crashed_test_pack"
        pack_name = "Crashed Test Pack"
        extra = "ai-crashed-test"
        sdk_modules = ("quill_crashed_pack",)

        def capabilities(self) -> HarnessCapabilities:
            return HarnessCapabilities()

    pack = CrashedInstallPack()

    # find_spec alone would say this is present (its file is right there);
    # the fix must actually attempt the import to see it is broken.
    assert importlib.util.find_spec("quill_crashed_pack") is not None

    available, reason = pack.is_available()

    assert available is False
    assert reason is not None and pack.extra in reason


def test_copilot_pack_matches_real_sdk() -> None:
    # Cross-check against the GA GitHub Copilot SDK: PyPI `github-copilot-sdk`,
    # import name `copilot`, OAuth-by-default.
    copilot = next(p for p in all_packs() if p.id == "copilot")
    assert copilot.sdk_modules == ("copilot",)
    assert copilot.extra == "ai-copilot"
    caps = copilot.capabilities()
    assert caps.requires_oauth is True
    assert caps.tool_calling and caps.skills


def test_every_pack_declares_capabilities() -> None:
    for pack in all_packs():
        caps = pack.capabilities()
        assert caps.chat is True
        assert caps.tool_calling is True
        assert caps.patch_generation is True


def test_register_all_into_registry() -> None:
    reg = HarnessRegistry()
    register_all(reg)
    assert {h.id for h in reg.all()} == PACK_IDS
    # Uninstalled packs are registered but not "available"; available() is always a
    # subset of all packs (empty in CI, may include locally-installed SDKs).
    assert {h.id for h in reg.available()} <= PACK_IDS


def test_unavailable_session_returns_error_not_crash(tmp_path: Path) -> None:
    events: list[AgentEvent] = []
    # Pick a pack whose SDK is NOT installed, so this never triggers a real model
    # call (some SDKs may be installed locally, e.g. openai-agents/claude-agent-sdk).
    pack = next((p for p in all_packs() if not p.is_available()[0]), None)
    if pack is None:
        pytest.skip("all SDK packs are installed in this environment")
    gw = _gateway(tmp_path, FakeHost(), events)
    session = pack.start_session(
        _agent(), AIContext(prompt="hi"), gw, PermissionBroker(), events.append
    )
    result = session.run()
    assert result.status == "error"
    assert pack.extra in result.error
    assert AgentEventKind.ERROR in [e.kind for e in events]


def test_injected_transport_drives_gateway(tmp_path: Path) -> None:
    # Simulate an installed SDK by injecting a transport; the pack must apply the
    # result through the gateway exactly like Native.
    events: list[AgentEvent] = []
    host = FakeHost()
    gw = _gateway(tmp_path, host, events)

    class FakePack(SdkHarness):
        pack_id = "fake"
        pack_name = "Fake SDK"
        extra = "ai-fake"
        sdk_modules = ("definitely_not_installed_xyz",)

        def capabilities(self):  # type: ignore[no-untyped-def]
            from quill.core.ai.harness import HarnessCapabilities

            return HarnessCapabilities()

    pack = FakePack(invoke=lambda agent, ctx: "bridged text")
    assert pack.is_available()[0] is True  # override forces availability
    session = pack.start_session(
        _agent(),
        AIContext(prompt="go"),
        gw,
        PermissionBroker(SafetyProfile.POWER_USER),
        events.append,
    )
    result = session.run()
    assert result.ok
    assert result.final_text == "bridged text"
    assert host.replacements == ["bridged text"]
    assert AgentEventKind.AGENT_COMPLETED in [e.kind for e in events]


def test_injected_transport_error_is_contained(tmp_path: Path) -> None:
    events: list[AgentEvent] = []
    gw = _gateway(tmp_path, FakeHost(), events)

    class FakePack(SdkHarness):
        pack_id = "fake"
        pack_name = "Fake SDK"
        extra = "ai-fake"
        sdk_modules = ()

        def capabilities(self):  # type: ignore[no-untyped-def]
            from quill.core.ai.harness import HarnessCapabilities

            return HarnessCapabilities()

    def boom(agent: AgentSpec, ctx: AIContext) -> str:
        raise RuntimeError("sdk exploded")

    pack = FakePack(invoke=boom)
    session = pack.start_session(
        _agent(), AIContext(prompt="x"), gw, PermissionBroker(), events.append
    )
    result = session.run()
    assert result.status == "error"
    assert "sdk exploded" in result.error


# -- helpers ---------------------------------------------------------------


def _gateway(tmp_path: Path, host: FakeHost, events: list[AgentEvent]) -> SafeEditorToolGateway:
    return SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(SafetyProfile.POWER_USER),
        activity=ActivityLog(tmp_path / "a.json"),
        identity=AgentIdentity(agent_id="a", risk=RiskLevel.LOW),
        emit=events.append,
    )


def _agent() -> AgentSpec:
    return AgentSpec(
        id="writing-companion",
        display_name="Writing Companion",
        system_prompt="Improve.",
        default_scope=ContextScope.SELECTION,
    )
