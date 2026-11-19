"""Help > GitHub Service Status... (complete.md 1.3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.github import service_status as ss
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_service_status import GitHubWorkbenchServiceStatusMixin


class _Window(GitHubWorkbenchServiceStatusMixin):
    def __init__(self, *, yes: bool = True) -> None:
        self.yes = yes
        self.asked: list[str] = []
        self.shown: list[tuple[str, str]] = []

    def _say(self, text: str) -> None:
        pass

    def _confirm(self, title: str, question: str) -> bool:
        self.asked.append(question)
        return self.yes

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())

    def _show_text(self, title: str, text: str) -> None:
        self.shown.append((title, text))


@pytest.fixture
def status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[int]:
    monkeypatch.setattr(ss, "app_data_dir", lambda: tmp_path)
    reads: list[int] = []

    def read() -> ss.ServiceStatus:
        reads.append(1)
        return ss.ServiceStatus("GitHub says: All Systems Operational.")

    monkeypatch.setattr(ss, "read_status", read)
    return reads


def test_registered() -> None:
    assert "service_status" in DEVELOPMENT_VERBS


def test_asks_once_then_reads(status: list[int]) -> None:
    window = _Window()
    window._do_service_status(None, None)
    window._do_service_status(None, None)
    assert len(window.asked) == 1 and "nothing about you" in window.asked[0]
    assert len(status) == 2
    assert window.shown[0] == (
        "GitHub Service Status",
        "GitHub says: All Systems Operational.\nGitHub lists no incident.",
    )


def test_no_reads_nothing(status: list[int]) -> None:
    window = _Window(yes=False)
    window._do_service_status(None, None)
    assert status == [] and window.shown == [] and not ss.consented()


def test_safe_mode_greys_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    assert not _Window()._fits_service_status(None)
    monkeypatch.delenv("QUILL_SAFE_MODE")
    assert _Window()._fits_service_status(None)
