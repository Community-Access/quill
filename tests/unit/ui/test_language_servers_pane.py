"""Language-server problems and Quick Fix through the Problems commands
(quill.ui.problems_commands), on QUILL's code-nav host with a stand-in server,
and the Language Servers window on a real wx dialog."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.lsp.convert import QuickFix
from quill.core.problems.model import Problem
from tests.unit.ui.test_main_frame_code_nav import _PaneHost

wx = pytest.importorskip("wx")


class _ServerHost(_PaneHost):
    """QUILL's host, with a language server for .ts that finds one problem."""

    def __init__(self, text: str, fixes: list[QuickFix] | None = None) -> None:
        super().__init__(text, "app.ts")
        self.fixes = fixes if fixes is not None else []
        self.replaced: list[tuple[int, int, str]] = []
        self.chosen = 0

    def _ls_serves(self, path: Any) -> bool:
        return True

    def _ls_problems_for(self, path: Any, text: str) -> list[Problem]:
        return [Problem(1, 7, "error", "Type 'string' is not assignable", "typescript")]

    def _ls_quick_fixes(self, path: Any, text: str, problem: Problem, done: Any) -> bool:
        done(self.fixes)
        return True

    def _problems_replace(self, start: int, end: int, text: str) -> None:
        self.replaced.append((start, end, text))
        self.editor.text = self.editor.text[:start] + text + self.editor.text[end:]


def test_server_problems_join_the_report_off_the_ui_thread() -> None:
    host = _ServerHost("let a: number = 'x';\n")
    host._problems_pane_widget.shown = True
    host.tools_check_this_file()
    assert host.background, "a check with a server runs in the background"
    report = host._problems_report
    assert [(p.source, p.line) for p in report.problems] == [("typescript", 1)]
    assert "typescript" in report.checked_with


def test_quick_fix_lists_fixes_applies_one_span_and_checks_again() -> None:
    fixes = [QuickFix("Use const", ((0, 3, "const"),), True), QuickFix("Ignore", (), False)]
    host = _ServerHost("let a = 1;\n", fixes)
    host._problems_pane_widget.shown = True
    host.tools_check_this_file()
    host._problems_quick_fix(0)
    summary, rows = host.lists[-1]
    assert summary == "2 quick fixes." and rows == ["Use const", "Ignore"]
    assert len(host.replaced) == 1, "one span: one undo step"
    assert host.editor.text == "const a = 1;\n"
    assert host.said[-1] == "Fixed: Use const" or host.said[-2] == "Fixed: Use const"


def test_no_quick_fix_says_so_and_changes_nothing() -> None:
    host = _ServerHost("let a = 1;\n", [])
    host._problems_pane_widget.shown = True
    host.tools_check_this_file()
    host._problems_quick_fix(0)
    assert host.said[-1] == "No quick fix for this problem"
    assert host.editor.text == "let a = 1;\n" and host.replaced == []


def test_cancelling_the_quick_fix_list_changes_nothing() -> None:
    host = _ServerHost("let a = 1;\n", [QuickFix("Use const", ((0, 3, "const"),), True)])
    host._problems_pane_widget.shown = True
    host.tools_check_this_file()
    host.chosen = None
    host._problems_quick_fix(0)
    assert host.replaced == [] and host.editor.text == "let a = 1;\n"


def test_the_window_writes_every_switch(wx_session_app: Any) -> None:
    from quill.core.lsp.servers import LANGUAGE_SERVERS
    from quill.ui.app_context_help import ensure_help_provider
    from quill.ui.language_servers_dialog import LanguageServersDialog, server_row

    ensure_help_provider(wx)
    settings = SimpleNamespace(language_servers_off=["Pyright"])
    window = LanguageServersDialog(None, settings)
    try:
        names = [spec.name for spec in LANGUAGE_SERVERS]
        assert not window.servers.IsChecked(names.index("Pyright"))
        assert window.servers.GetString(0) == server_row(LANGUAGE_SERVERS[0])
        assert not window.features["parameter_hints_as_you_type"].GetValue()
        window.servers.Check(names.index("Pyright"), True)
        window.servers.Check(names.index("CSS server"), False)
        window.features["language_server_problems"].SetValue(False)
        window.enabled.SetValue(False)
        window.apply()
        assert settings.language_servers_off == ["CSS server"]
        assert settings.language_server_problems is False
        assert settings.language_servers_enabled is False
        for control in (window.enabled, window.servers, *window.features.values()):
            assert control.GetHelpText()
    finally:
        window.destroy()
