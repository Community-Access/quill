"""Discussion browsing preserves answer context and pagination status."""

from __future__ import annotations

from types import SimpleNamespace
from urllib.error import HTTPError

from quill.core.github import discussions
from quill.core.github.explore import GitHubExploreClient, GitHubExploreError


def _payload(*, has_next: bool = False, cursor: str = "") -> dict:
    return {
        "repository": {
            "discussions": {
                "totalCount": 3,
                "pageInfo": {"hasNextPage": has_next, "endCursor": cursor or None},
                "nodes": [
                    {
                        "number": 18,
                        "title": "How do I configure this?",
                        "bodyText": "Question details",
                        "url": "https://github.com/owner/repo/discussions/18",
                        "createdAt": "2026-10-01T00:00:00Z",
                        "updatedAt": "2026-11-01T00:00:00Z",
                        "closed": False,
                        "author": {"login": "alice"},
                        "category": {
                            "name": "Q&A",
                            "emoji": "🙋",
                            "isAnswerable": True,
                        },
                        "answer": {
                            "bodyText": "Use the settings menu.",
                            "url": "https://github.com/owner/repo/discussions/18#answer",
                            "author": {"login": "bob"},
                        },
                    }
                ],
            }
        }
    }


def test_discussion_view_maps_category_answer_and_thread_context(monkeypatch) -> None:
    monkeypatch.setattr(
        discussions,
        "_request",
        lambda _token, _query, _variables: _payload(),
    )

    rows, complete, warning = discussions.list_discussions("token", "owner/repo")

    assert complete and not warning
    assert len(rows) == 1
    assert rows[0].kind == "discussion"
    assert rows[0].key == "18"
    assert "Q&A" in rows[0].label
    assert "Answered by bob" in rows[0].label
    assert "Use the settings menu" in rows[0].detail


def test_discussion_view_reports_more_results_when_page_is_capped(monkeypatch) -> None:
    monkeypatch.setattr(
        discussions,
        "_request",
        lambda _token, _query, _variables: _payload(has_next=True, cursor="next"),
    )

    rows, complete, warning = discussions.list_discussions("token", "owner/repo", limit=1)

    assert len(rows) == 1
    assert not complete
    assert "3 discussions" in warning


def test_direct_discussion_lookup_fetches_the_requested_number(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def _request(_token: str, _query: str, variables: dict[str, object]):
        calls.append(variables)
        discussion = _payload()["repository"]["discussions"]["nodes"][0]
        return {"repository": {"discussion": discussion}}

    monkeypatch.setattr(discussions, "_request", _request)

    row = discussions.fetch_discussion("token", "owner/repo", 18)

    assert calls == [{"owner": "owner", "repo": "repo", "number": 18}]
    assert row.key == "18"
    assert row.kind == "discussion"


def test_discussion_view_requires_a_signed_in_account() -> None:
    try:
        discussions.list_discussions(None, "owner/repo")
    except GitHubExploreError as exc:
        assert "Sign in" in str(exc)
    else:
        raise AssertionError("anonymous discussion requests must be refused")


def test_discussion_graphql_redirect_is_refused_without_forwarding_credentials(monkeypatch) -> None:
    requests = []

    class _Opener:
        def open(self, request, *, timeout):
            requests.append(request)
            raise HTTPError(
                request.full_url,
                302,
                "Moved",
                {"Location": "https://other.example/graphql"},
                None,
            )

    monkeypatch.setattr(discussions, "build_opener", lambda *_args: _Opener())

    try:
        discussions.list_discussions("secret", "owner/repo")
    except GitHubExploreError as exc:
        assert "credentials were not forwarded" in str(exc)
    else:
        raise AssertionError("a GraphQL redirect must be refused")
    assert len(requests) == 1
    assert requests[0].full_url == "https://api.github.com/graphql"
    assert requests[0].get_header("Authorization") == "Bearer secret"


def test_explore_exposes_discussions_as_an_authenticated_repository_view(monkeypatch) -> None:
    client = GitHubExploreClient(_Provider())  # type: ignore[arg-type]
    monkeypatch.setattr(
        "quill.core.github.explore.list_discussions",
        lambda token, repo, *, limit: ([_row(repo)], True, ""),
    )

    result = client.fetch_with_status("discussions", repo="owner/repo")

    assert result.items[0].kind == "discussion"
    anonymous = GitHubExploreClient(_Provider(authenticated=False))  # type: ignore[arg-type]
    try:
        anonymous.fetch_with_status("discussions", repo="owner/repo")
    except GitHubExploreError as exc:
        assert "Sign in" in str(exc)
    else:
        raise AssertionError("the Explore Discussions view must require sign-in")


def _row(repository: str):
    from quill.core.github.explore_models import ExploreRow

    return ExploreRow("Discussion", "Details", repo=repository, kind="discussion")


class _Provider:
    def __init__(self, authenticated: bool = True) -> None:
        self.is_authenticated = authenticated
        self.token = "token" if authenticated else None
        self._gh = object()

    def _repo(self, name: str):
        return SimpleNamespace(full_name=name)
