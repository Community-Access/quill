"""The code scanning commands on alert rows and in Code Scanning Analyses."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.item_shortcuts import NEW_HERE
from quill.ui.github_workbench_code_scanning import GitHubWorkbenchCodeScanningMixin
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from tests.unit.core.github_workbench.test_code_scanning_tools import FIX, Api


def _row(key: str) -> ExploreRow:
    return ExploreRow("Code scanning: high: app.py", "", "", "o/r", "security", key)


class _Window(GitHubWorkbenchCodeScanningMixin):
    signed_in = True

    def __init__(self, api: Api, answers: list[Any]) -> None:
        self.api, self.answers = api, list(answers)
        self.said: list[str] = []
        self.shown: list[tuple[str, str]] = []
        self.frame = SimpleNamespace(current=SimpleNamespace(key=""), reload=lambda: None)

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())

    def _choose(self, *_a: Any) -> int:
        return int(self.answers.pop(0))

    def _confirm(self, *_a: Any) -> bool:
        return bool(self.answers.pop(0))

    def _ask_text(self, *_a: Any, **_k: Any) -> str:
        return str(self.answers.pop(0))

    def _show_text(self, title: str, text: str) -> None:
        self.shown.append((title, text))


def test_wired_and_only_for_code_scanning_alerts() -> None:
    assert {"autofix_alert", "alert_instances", "upload_sarif"} <= set(DEVELOPMENT_VERBS)
    assert NEW_HERE["code_scanning_analyses"] == "github.workbench.upload_sarif"
    window = _Window(Api({}), [])
    assert window._fits_autofix_alert(_row("code-scanning:7"))
    assert not window._fits_autofix_alert(_row("dependabot:7"))


def test_autofix_asks_when_there_is_none_then_commits_a_ready_one() -> None:
    window = _Window(Api({f"POST {FIX}": {"status": "pending"}}, fail={f"GET {FIX}": 404}), [True])
    window._do_autofix_alert(None, _row("code-scanning:7"))
    assert window.said == ["Copilot Autofix is still making the fix. Ask again in a minute."]
    ready = Api({f"GET {FIX}": {"status": "success"}, f"POST {FIX}/commits": {"sha": "1234567"}})
    window = _Window(ready, [0, "fix-7", ""])
    window._do_autofix_alert(None, _row("code-scanning:7"))
    assert window.said == ["Committed the fix to fix-7 as 1234567."]


def test_every_place_opens_in_a_window_with_a_count() -> None:
    api = Api({"GET /repos/o/r/code-scanning/alerts/7/instances": [{"location": {"path": "a.py"}}]})
    window = _Window(api, [])
    window._do_alert_instances(None, _row("code-scanning:7"))
    assert window.shown == [
        ("Every Place: alert #7", "Alert #7 was found in 1 place.\n\na.py, open.")
    ]
