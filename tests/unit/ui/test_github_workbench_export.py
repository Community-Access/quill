"""GitHub Workbench > File > Export List (PRD 22.7), in a real frame.

A real frame over a fake GitHub Items provider, background work inline; the
Save dialog is replaced, so Export List is called the way the menu row calls it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.core.github.workbench_window_menu import WORKBENCH_KEYS  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"
EXPORT = "github.workbench.export_list"


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [
            GitHubItem(3, "Speed up start", "open", "https://github.com/o/r/issues/3", False),
            GitHubItem(4, "Fix | in names", "open", "https://github.com/o/r/issues/4", False),
        ]

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
    opened: list[Path] = []
    provider = GitHubWorkbenchProvider(
        _Items(), REPO, announce=said.append, open_document=opened.append
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.opened = opened  # type: ignore[attr-defined]
    yield frame
    provider.stop_watch_timer()
    frame.frame.Destroy()


def _save_to(monkeypatch, path: Path | None) -> None:
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
        "quill.ui.github_workbench_actions.show_modal_dialog",
        lambda _d, _t: wx.ID_OK if path is not None else wx.ID_CANCEL,
    )


def _issues(frame: WorkbenchFrame) -> None:
    ref = NodeRef("repository", "issues", REPO)
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    assert frame.rows


def test_export_list_has_a_key_and_a_row(bench) -> None:
    assert WORKBENCH_KEYS[EXPORT] == "Ctrl+Shift+X"
    assert bench.provider.supports(EXPORT)


def test_export_list_writes_the_list_as_shown(bench, monkeypatch, tmp_path: Path) -> None:
    _issues(bench)
    target = tmp_path / "issues.md"
    _save_to(monkeypatch, target)
    monkeypatch.setattr(
        "quill.ui.github_workbench_actions.GitHubWorkbenchActionsMixin._confirm",
        lambda _s, _t, _q: True,
    )
    bench.run(EXPORT)
    text = target.read_text(encoding="utf-8")
    assert "Speed up start" in text and "Fix \\| in names" in text
    assert text.splitlines()[1].startswith("| --- ")
    assert any(line.startswith("Exported 2 rows to issues.md.") for line in bench.said)
    assert bench.opened == [target]


def test_export_list_says_when_there_is_nothing(bench, monkeypatch) -> None:
    _issues(bench)
    bench.rows = []
    _save_to(monkeypatch, None)
    bench.run(EXPORT)
    assert bench.said[-1] == "There is nothing in the list to export."


def test_cancelling_the_save_writes_nothing(bench, monkeypatch, tmp_path: Path) -> None:
    _issues(bench)
    _save_to(monkeypatch, None)
    bench.run(EXPORT)
    assert not list(tmp_path.iterdir())
