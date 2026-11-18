"""Repository > Wiki and Clone Wiki... (GitHub PRD GX12)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github import wiki
from quill.core.github.clone import parse_clone_source
from quill.core.github.rest_transport import RestResponse


class FakeApi:
    def __init__(self, on: bool) -> None:
        self.on = on

    def rest(self, method: str, path: str, **_k: Any) -> Any:
        return RestResponse(200, {}, {"has_wiki": self.on})

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_the_wiki_node_says_whether_it_is_on_and_how_to_edit_it() -> None:
    rows = wiki.fetch_wiki(FakeApi(True), "o/r")
    assert rows[0].label == "o/r has a wiki. Enter opens it on GitHub."
    assert rows[0].url == "https://github.com/o/r/wiki"
    assert "Clone Wiki (Ctrl+Alt+W)" in rows[1].label and "o/r.wiki" in rows[1].label
    off = wiki.fetch_wiki(FakeApi(False), "o/r")
    assert off[0].label.startswith("o/r's wiki is turned off.")


def test_the_wiki_address_is_one_the_clone_already_understands() -> None:
    source = parse_clone_source(wiki.wiki_address("o/r"))
    assert source.url == "https://github.com/o/r.wiki.git"
    assert source.full_name == "o/r.wiki" and source.on_github


def test_clone_wiki_fills_in_the_wikis_address(monkeypatch: Any) -> None:
    from quill.ui.github_workbench_tier2 import GitHubWorkbenchTier2Mixin

    seen: list[Any] = []
    monkeypatch.setattr("quill.ui.github_clone.start_clone", lambda host, **_k: seen.append(host))
    window = GitHubWorkbenchTier2Mixin.__new__(GitHubWorkbenchTier2Mixin)
    window.frame = SimpleNamespace(frame=None, current=SimpleNamespace(template="repository"))
    window.items = SimpleNamespace(token="t")
    window._say = lambda _text: None
    assert window._fits_clone_wiki(None)
    window._do_clone_wiki(SimpleNamespace(instance="o/r"), None)
    assert seen[0].initial_repo == "o/r.wiki"
