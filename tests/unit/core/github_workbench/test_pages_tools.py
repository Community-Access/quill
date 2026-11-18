"""GitHub Pages: turn on or off, rebuild, and check the site."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import pages_tools as pages
from quill.core.github.explore_models import ExploreRow
from quill.core.github.item_shortcuts import NEW_HERE
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.ui.github_workbench_pages import GitHubWorkbenchPagesMixin
from tests.unit.core.github_workbench.test_run_more import Api

P = "/repos/o/r/pages"


def test_turning_pages_on_from_a_branch_or_by_a_workflow() -> None:
    api = Api({f"POST {P}": {"html_url": "https://o.github.io/r/"}})
    said = pages.turn_on(api, "o/r", workflow=False, branch="main", folder="/docs")
    assert said == "Pages is on, published from main/docs, at https://o.github.io/r/."
    assert api.sent[-1][2] == {
        "build_type": "legacy",
        "source": {"branch": "main", "path": "/docs"},
    }
    pages.turn_on(api, "o/r", workflow=True)
    assert api.sent[-1][2] == {"build_type": "workflow"}
    with pytest.raises(pages.PagesError, match="already"):
        pages.turn_on(Api(fail={f"POST {P}": 409}), "o/r", workflow=True)


def test_check_says_the_latest_build_then_the_domain() -> None:
    api = Api({
        f"GET {P}/builds/latest": {"status": "built", "created_at": "2026-11-17T08:00:00Z"},
        f"GET {P}/health": {
            "domain": {
                "host": "docs.example.org",
                "is_valid_domain": True,
                "dns_resolves": False,
                "is_pointed_to_github_pages_ip": True,
            }
        },
    })
    assert pages.check(api, "o/r") == (
        "The latest build was built, 2026-11-17 at 08:00. "
        "docs.example.org: the domain's DNS does not resolve."
    )
    no_domain = Api(
        {f"GET {P}/builds/latest": {"status": "errored"}}, fail={f"GET {P}/health": 404}
    )
    assert pages.check(no_domain, "o/r") == (
        "The latest build is errored. The site has no custom domain to check."
    )


def test_a_health_check_still_running_says_to_ask_again() -> None:
    class Busy(Api):
        def rest(self, method: str, path: str, **k: Any) -> Any:
            if path.endswith("/health"):
                return RestResponse(202, {}, {})
            return super().rest(method, path, **k)

    assert pages.check(Busy({f"GET {P}/builds/latest": {"status": "built"}}), "o/r").endswith(
        "Ask again in a minute."
    )


class _Window(GitHubWorkbenchPagesMixin):
    signed_in = True

    def __init__(self, api: Api, answers: list[Any], node: str = "pages") -> None:
        self.api, self.answers, self.said = api, list(answers), []
        self.frame = SimpleNamespace(current=SimpleNamespace(key=node), reload=lambda: None)

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _background(self, _n: str, work: Any, done: Any) -> None:
        done(work())

    def _choose(self, *_a: Any) -> int:
        return int(self.answers.pop(0))

    def _confirm(self, *_a: Any) -> bool:
        return bool(self.answers.pop(0))

    def _ask_text(self, *_a: Any, **_k: Any) -> str:
        return str(self.answers.pop(0))


def test_ctrl_n_turns_pages_on_and_turn_off_asks_first() -> None:
    assert NEW_HERE["pages"] == "github.workbench.pages_turn_on"
    window = _Window(Api(), [0, "main", 0])
    assert window._fits_pages_turn_on(None)
    window._do_pages_turn_on(SimpleNamespace(instance="o/r"), None)
    assert window.api.sent[-1][2] == {
        "build_type": "legacy",
        "source": {"branch": "main", "path": "/"},
    }
    site = ExploreRow("Pages site", "", "", "o/r", "pages")
    window = _Window(Api(), [False])
    window._do_pages_turn_off(None, site)
    assert window.api.sent == []
    assert isinstance(GitHubRestError("x", status=1), Exception)
