"""Reactions on releases and commit comments, and React... on a release row."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.items_provider import GitHubRelease
from quill.core.github.reactions import REACTION_TARGETS, _collection
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_releases import RELEASE_VERBS, GitHubWorkbenchReleasesMixin


def test_releases_and_commit_comments_are_reaction_targets() -> None:
    assert _collection("o/r", "release", 9) == "/repos/o/r/releases/9/reactions"
    assert _collection("o/r", "commit_comment", 4) == "/repos/o/r/comments/4/reactions"
    assert {"issue", "issue_comment", "review_comment"} <= set(REACTION_TARGETS)


class _Window(GitHubWorkbenchReleasesMixin):
    signed_in = True

    def __init__(self) -> None:
        self.items = SimpleNamespace(token="t", is_authenticated=True)
        self.said: list[str] = []
        self.frame = SimpleNamespace(frame=None)

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())

    def _repo_for(self, _ref: Any) -> str:
        return "o/r"

    def _parent(self) -> Any:
        return None


def test_react_on_a_release_finds_its_id_then_starts_the_reaction_flow(monkeypatch: Any) -> None:
    from quill.core.github import workbench_api
    from quill.ui import github_reactions_ui

    class Api:
        def __init__(self, _token: Any) -> None:
            pass

        def rest(self, method: str, path: str, **_k: Any) -> Any:
            assert (method, path) == ("GET", "/repos/o/r/releases/tags/v1.0")
            return SimpleNamespace(data={"id": 77})

    seen: list[tuple[Any, ...]] = []
    monkeypatch.setattr(workbench_api, "TokenApi", Api)
    monkeypatch.setattr(
        github_reactions_ui,
        "start_reaction_flow",
        lambda _parent, _provider, repo, kind, target, **k: seen.append((
            repo,
            kind,
            target,
            k["what"],
        )),
    )
    window = _Window()
    release = GitHubRelease("v1.0", "First")
    assert window._fits_react_release(release) and "react_release" in RELEASE_VERBS
    assert "react_release" in DEVELOPMENT_VERBS or "react_release" in RELEASE_VERBS
    window._do_react_release(None, release)
    assert seen == [("o/r", "release", 77, "release v1.0")]
