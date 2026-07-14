"""Phases 3-5 gateway tools: app state, current section, accessibility, web research."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.permissions import PermissionBroker, RiskLevel, SafetyProfile
from quill.core.ai.tool_gateway import AgentIdentity, SafeEditorToolGateway
from quill.core.ai.web_research import WebResult


@dataclass
class FakeHost:
    document: str = "# Title\n\nclick here for more.\n"
    selection: str = ""
    cursor: tuple[int, int] = (3, 1)
    section: str = "## Body\n\nSome words."
    flags: dict[str, bool] = field(default_factory=lambda: {"ai_enabled": True, "safe_mode": False})

    def get_document(self) -> str:
        return self.document

    def get_selection(self) -> str:
        return self.selection

    def get_outline(self) -> list[str]:
        return ["Title"]

    def get_file_type(self) -> str:
        return "md"

    def get_cursor_position(self) -> tuple[int, int]:
        return self.cursor

    def get_current_section(self) -> str:
        return self.section

    def get_status_flags(self) -> dict[str, bool]:
        return self.flags

    def create_undo_checkpoint(self, label: str) -> None: ...
    def apply_replacement(self, text: str) -> None: ...
    def apply_insert(self, text: str) -> None: ...
    def apply_document_text(self, text: str) -> None: ...
    def run_command(self, command_id: str) -> None: ...

    def confirm(self, message: str) -> bool:
        return True

    def preview_diff(self, review: object) -> bool:
        return True

    def announce(self, message: str) -> None: ...


class FakeWeb:
    def __init__(self, ready: bool = True) -> None:
        self._ready = ready
        self.searches: list[str] = []
        self.fetches: list[str] = []

    def available(self) -> bool:
        return self._ready

    def search(self, query: str, *, max_results: int = 5) -> list[WebResult]:
        self.searches.append(query)
        return [WebResult(title="Challenger disaster", url="https://example.org/c", snippet="1986")]

    def fetch(self, url: str) -> str:
        self.fetches.append(url)
        return "Fetched page text."


def _gateway(tmp_path: Path, host: FakeHost, *, web=None, profile=SafetyProfile.POWER_USER):
    return SafeEditorToolGateway(
        host=host,
        broker=PermissionBroker(profile),
        activity=ActivityLog(tmp_path / "a.json"),
        identity=AgentIdentity(agent_id="x", risk=RiskLevel.LOW),
        web=web,
    )


# -- Phase 3: app/editor-state awareness ----------------------------------


def test_read_app_state_reports_cursor_and_flags(tmp_path: Path) -> None:
    gw = _gateway(tmp_path, FakeHost())
    state = gw.read_app_state()
    assert "line 3, column 1" in state
    assert "File type: md" in state
    assert "ai_enabled=on" in state
    assert "safe_mode=off" in state


def test_read_current_section_returns_section_text(tmp_path: Path) -> None:
    gw = _gateway(tmp_path, FakeHost(section="## Body\n\nSome words."))
    assert "Some words." in gw.read_current_section()


def test_read_app_state_degrades_when_host_lacks_methods(tmp_path: Path) -> None:
    @dataclass
    class Minimal:
        def get_document(self) -> str:
            return "x"

        def get_selection(self) -> str:
            return ""

        def get_outline(self) -> list[str]:
            return []

        def get_file_type(self) -> str:
            return ""

    gw = _gateway(tmp_path, Minimal())  # type: ignore[arg-type]
    # No cursor/flags methods -> a graceful message, not a crash.
    assert gw.read_app_state() == "No app state available."


# -- Phase 4: accessibility audit -----------------------------------------


def test_audit_accessibility_flags_generic_link_text(tmp_path: Path) -> None:
    host = FakeHost(document="See [click here](https://x.example) for details.\n")
    gw = _gateway(tmp_path, host)
    report = gw.audit_accessibility()
    assert "Accessibility" in report
    assert "link" in report.lower()


# -- Phase 5: web research -------------------------------------------------


def test_web_search_not_configured_by_default(tmp_path: Path) -> None:
    gw = _gateway(tmp_path, FakeHost())  # NullWebResearchProvider by default
    assert gw.web_search("challenger") == "Web research is not configured."


def test_web_search_uses_provider_when_available(tmp_path: Path) -> None:
    web = FakeWeb(ready=True)
    gw = _gateway(tmp_path, FakeHost(), web=web)
    out = gw.web_search("challenger disaster")
    assert "Challenger disaster" in out
    assert "https://example.org/c" in out
    assert web.searches == ["challenger disaster"]


def test_web_fetch_uses_provider(tmp_path: Path) -> None:
    web = FakeWeb(ready=True)
    gw = _gateway(tmp_path, FakeHost(), web=web)
    assert gw.web_fetch("https://example.org/c") == "Fetched page text."
    assert web.fetches == ["https://example.org/c"]


def test_web_search_blocked_when_locked_down(tmp_path: Path) -> None:
    from quill.core.ai.tool_gateway import PermissionDeniedError

    web = FakeWeb(ready=True)
    gw = _gateway(tmp_path, FakeHost(), web=web, profile=SafetyProfile.LOCKED_DOWN)
    with pytest.raises(PermissionDeniedError):
        gw.web_search("anything")
    assert web.searches == []  # never reached the provider
