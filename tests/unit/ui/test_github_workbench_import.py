"""GitHub Workbench: Import Issues from a Spreadsheet and New Issues from Lines (PRD 22.7).

A real frame over a fake GitHub Items provider and a recorded API, background
work inline; the file and preview dialogs are answered by patching, so each
command is called the way its menu row calls it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.core.github.rest_transport import RestResponse  # noqa: E402
from quill.core.github.workbench_window_menu import WORKBENCH_KEYS  # noqa: E402
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"
IMPORT = "github.workbench.import_issues"
LINES = "github.workbench.issues_from_lines"


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []
        self.next_number = 40

    def rest(self, method: str, path: str, *, body=None, query=None) -> RestResponse:
        self.calls.append((method, path, body))
        if path.endswith("/milestones"):
            return RestResponse(200, {}, [{"title": "1.0", "number": 7}])
        if method == "POST" and path.endswith("/issues"):
            if body and body.get("title") == "Refused":
                raise RuntimeError("Validation Failed")
            self.next_number += 1
            return RestResponse(201, {}, {"number": self.next_number, "id": 900 + self.next_number})
        return RestResponse(201, {}, {})

    def graphql(self, query: str, variables: Any) -> dict[str, Any]:
        return {}


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [GitHubItem(3, "One", "open", "https://github.com/o/r/issues/3", False)]

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return []

    def close(self) -> None:
        pass


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir, monkeypatch):
    monkeypatch.setattr("quill.core.github.consent.load_github_consent_complete", lambda: True)
    said: list[str] = []
    provider = GitHubWorkbenchProvider(
        _Items(),
        REPO,
        announce=said.append,
        gist_source=lambda: ("notes.md", "- [ ] Write the guide\n* Fix the parser\n"),
    )
    provider.api = FakeApi()
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    ref = NodeRef("repository", "issues", REPO)
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    yield frame
    provider.stop_watch_timer()
    frame.frame.Destroy()


def _open_file(monkeypatch, path: Path | None) -> None:
    class Dialog:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def __enter__(self) -> Dialog:
            return self

        def __exit__(self, *_exc: object) -> None:
            pass

        def GetPath(self) -> str:  # noqa: N802 - wx's name
            return str(path)

    monkeypatch.setattr(wx, "FileDialog", Dialog)
    monkeypatch.setattr(
        "quill.ui.github_workbench_import.show_modal_dialog",
        lambda _d, _t: wx.ID_OK if path is not None else wx.ID_CANCEL,
    )


def _reports(monkeypatch) -> list[str]:
    shown: list[str] = []
    monkeypatch.setattr(
        "quill.ui.wordpress_dialogs.show_report",
        lambda _p, _s, *, title, text, help_text: shown.append(text),
    )
    return shown


def _preview(monkeypatch, answer: bool) -> list[tuple[str, list[str]]]:
    shown: list[tuple[str, list[str]]] = []

    def ask(_parent, _show, *, title, summary, lines, yes, destructive=None):
        shown.append((summary, list(lines)))
        return answer

    monkeypatch.setattr("quill.ui.wordpress_workbench_dialogs.ask_preview", ask)
    return shown


def test_both_rows_have_keys_and_permissions(bench) -> None:
    assert WORKBENCH_KEYS[IMPORT] == "Ctrl+Alt+I"
    assert WORKBENCH_KEYS[LINES] == "Ctrl+Alt+L"
    assert COMMAND_REQUIREMENTS[IMPORT][0] == "sign_in"
    assert bench.provider.supports(IMPORT) and bench.provider.supports(LINES)


def test_import_previews_then_makes_each_row(bench, monkeypatch, tmp_path: Path) -> None:
    sheet = tmp_path / "issues.csv"
    sheet.write_text(
        "Title,Labels,Milestone,Due\nCrash,bug,1.0,soon\n,,,\nRefused,,,\nLater,,Someday,\n",
        encoding="utf-8",
    )
    _open_file(monkeypatch, sheet)
    shown = _preview(monkeypatch, True)
    reports = _reports(monkeypatch)
    bench.run(IMPORT)
    summary, lines = shown[0]
    assert summary == "2 issues will be made in owner/repo; 1 rows are skipped."
    assert "Left out, matching no field: due." in lines
    assert "Row 5: skipped, this repository has no milestone called Someday." in lines
    posts = [(p, b) for m, p, b in bench.provider.api.calls if m == "POST"]
    assert posts[0] == (
        "/repos/owner/repo/issues",
        {"title": "Crash", "labels": ["bug"], "milestone": 7},
    )
    details = reports[0]
    assert "Row 2: made #41, Crash." in details
    # Row 3 is blank and skipped, but still counted, so these are Excel's numbers.
    assert "Row 4: GitHub refused it: Validation Failed" in details
    assert any(s.startswith("Made 1 of 2 issues in owner/repo.") for s in bench.said)


def test_cancelling_the_preview_sends_nothing(bench, monkeypatch, tmp_path: Path) -> None:
    sheet = tmp_path / "issues.csv"
    sheet.write_text("Title\nOne\n", encoding="utf-8")
    _open_file(monkeypatch, sheet)
    _preview(monkeypatch, False)
    bench.run(IMPORT)
    assert not [c for c in bench.provider.api.calls if c[0] == "POST"]


def test_issues_from_lines_makes_sub_issues(bench, monkeypatch) -> None:
    answers = iter([None, "#12"])

    def ask_text(_self, _title, _prompt, *, multiline=False, value=""):
        given = next(answers)
        return value if given is None else given

    monkeypatch.setattr(
        "quill.ui.github_workbench_actions.GitHubWorkbenchActionsMixin._ask_text", ask_text
    )
    shown = _preview(monkeypatch, True)
    reports = _reports(monkeypatch)
    bench.run(LINES)
    assert shown[0][0] == "2 issues will be made in owner/repo, each a sub-issue of #12."
    assert shown[0][1] == ["Line 1: Write the guide", "Line 2: Fix the parser"]
    calls = [(p, b) for m, p, b in bench.provider.api.calls if m == "POST"]
    assert calls == [
        ("/repos/owner/repo/issues", {"title": "Write the guide"}),
        ("/repos/owner/repo/issues/12/sub_issues", {"sub_issue_id": 941}),
        ("/repos/owner/repo/issues", {"title": "Fix the parser"}),
        ("/repos/owner/repo/issues/12/sub_issues", {"sub_issue_id": 942}),
    ]
    assert "Line 1: made #41, a sub-issue of #12, Write the guide." in reports[0]
