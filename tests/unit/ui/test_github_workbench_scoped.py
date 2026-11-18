"""A gist's comments, history and forks, through the shared list chooser."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import resource_engine as engine
from quill.core.github.explore_models import ExploreRow
from quill.core.github.resource_engine import ResourceError
from quill.core.github.resource_specs_gist import fork_gist, gist_spec
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.ui.github_workbench_scoped import GitHubWorkbenchScopedListsMixin

GIST = ExploreRow("notes.md", "d", "u", "", "gist", "abc123", "", "Notes")


class _Api:
    def __init__(self, data: Any = None, fail: int = 0) -> None:
        self.data, self.fail, self.sent = data, fail, []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> RestResponse:
        self.sent.append((method, path, body))
        if self.fail:
            raise GitHubRestError("no", status=self.fail)
        return RestResponse(200, {}, self.data if method == "GET" else {"id": "new1"})


class _Host(GitHubWorkbenchScopedListsMixin):
    def __init__(self, api: _Api, answers: list[Any]) -> None:
        self.api, self.answers, self.said, self.signed_in = api, answers, [], True
        self._say = self.said.append  # type: ignore[assignment]
        self._background = lambda _w, work, done: done(work())  # type: ignore[assignment]
        self._choose = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._confirm = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._ask_fields = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]

    def github_api(self) -> Any:
        return self.api


def test_a_comment_is_added_to_the_gist() -> None:
    api = _Api([
        {"id": 1, "body": "Nice", "user": {"login": "kim"}, "created_at": "2026-11-01T00:00:00Z"}
    ])
    host = _Host(api, [0, {"body": "Thanks"}])
    host._do_gist_comments(None, GIST)
    assert api.sent[0][1] == "/gists/abc123/comments"
    assert api.sent[-1] == ("POST", "/gists/abc123/comments", {"body": "Thanks"})


def test_a_comment_is_deleted_only_after_yes() -> None:
    api = _Api([{"id": 9, "body": "Old", "user": {"login": "jeff"}}])
    _Host(api, [1, 1, False])._do_gist_comments(None, GIST)  # the comment, Delete..., No
    assert [m for m, _p, _b in api.sent] == ["GET"]
    _Host(api, [1, 1, True])._do_gist_comments(None, GIST)
    assert api.sent[-1][:2] == ("DELETE", "/gists/abc123/comments/9")


def test_history_reads_versions_and_says_the_chosen_one() -> None:
    api = _Api([
        {
            "version": "a1b2c3d4",
            "committed_at": "2026-11-02T00:00:00Z",
            "user": {"login": "jeff"},
            "change_status": {"additions": 3, "deletions": 1},
        }
    ])
    host = _Host(api, [0])
    host._do_gist_history(None, GIST)
    assert host.said == ["2026-11-02 by jeff: 3 lines added, 1 removed (version a1b2c3d)."]
    assert engine.fetch(_Api([]), gist_spec("gist_forks"), "abc123") == []


def test_forking_says_where_the_copy_is_and_explains_your_own() -> None:
    assert fork_gist(_Api(), "abc123") == "Forked the gist. Your copy new1 is in My Gists."
    with pytest.raises(ResourceError, match="your own"):
        fork_gist(_Api(fail=422), "abc123")
