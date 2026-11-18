"""New Here in Advisories, Publish or Close Advisory..., Request CVE... (GitHub PRD GX11)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.security_advisories import advisory_row
from quill.ui.github_workbench_advisories import GitHubWorkbenchAdvisoriesMixin
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from tests.unit.core.github_workbench.test_security_advisories import ADVISORY, FakeApi

ROW = advisory_row("o/r", ADVISORY)
REF = SimpleNamespace(instance="o/r")


class _Window(GitHubWorkbenchAdvisoriesMixin):
    signed_in = True

    def __init__(self, picks: list[int], texts: list[str] | None = None) -> None:
        self.api, self.picks, self.texts = FakeApi(), list(picks), list(texts or [])
        self.said: list[str] = []
        self.frame = SimpleNamespace(
            frame=None,
            current=SimpleNamespace(key="advisories"),
            reload=lambda: self.said.append("(reloaded)"),
        )

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, *_a: Any) -> int:
        return self.picks.pop(0)

    def _confirm(self, *_a: Any) -> bool:
        return True

    def _ask_text(self, *_a: Any, **_k: Any) -> str:
        return self.texts.pop(0)

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def test_registered_and_where_each_fits() -> None:
    assert {"new_advisory", "advisory_state", "request_cve"} <= set(DEVELOPMENT_VERBS)
    window = _Window([])
    assert window._fits_new_advisory(None)
    assert window._fits_advisory_state(ROW) and window._fits_request_cve(ROW)


def test_new_here_reports_a_vulnerability_privately() -> None:
    window = _Window([0, 1], ["Crash on open", "Steps to reproduce"])
    window._do_new_advisory(REF, None)
    assert window.api.sent[-1][1] == "/repos/o/r/security-advisories/reports"
    assert window.api.sent[-1][2]["severity"] == "high"
    assert window.said[0].startswith("Reported privately to o/r's maintainers")


def test_new_here_drafts_an_advisory_with_its_package() -> None:
    window = _Window([1, 4], ["Crash", "Steps", "quill-io", "pip"])
    window._do_new_advisory(REF, None)
    body = window.api.sent[-1][2]
    assert "severity" not in body and body["vulnerabilities"][0]["package"]["name"] == "quill-io"


def test_publishing_wants_the_ghsa_typed(monkeypatch: Any) -> None:
    seen: list[str] = []

    class Typed:
        def __init__(self, _parent: Any, **kw: Any) -> None:
            seen.append(kw["expected"])

        def show(self) -> bool:
            return False

    monkeypatch.setattr("quill.ui.github_repo_admin_dialogs.TypedConfirmDialog", Typed)
    window = _Window([0])
    window._do_advisory_state(None, ROW)
    assert seen == ["GHSA-abcd-2345-wxyz"]
    assert window.said == ["Cancelled; the advisory was not published."]
    assert not any(method == "PATCH" for method, *_rest in window.api.sent)
    window = _Window([1])
    window._do_advisory_state(None, ROW)
    assert window.api.sent[-1][2] == {"state": "closed"}
