"""Global workbench views and account/repository action boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from quill.core.github import explore as explore_core
from quill.core.github.explore import GitHubExploreClient, GitHubExploreError


def _issue(number: int, url: str):
    return SimpleNamespace(
        number=number,
        title=f"Work {number}",
        html_url=url,
        repository=SimpleNamespace(full_name="o/r"),
        state="open",
        pull_request=SimpleNamespace() if "/pull/" in url else None,
    )


class _Provider:
    def __init__(self, authenticated: bool = True) -> None:
        self.is_authenticated = authenticated
        self.token = "secret" if authenticated else None
        self.searches: list[str] = []
        self.label_calls: list[tuple[str, ...]] = []
        user = SimpleNamespace(login="me")
        user.get_repos = lambda: [
            SimpleNamespace(full_name="o/r", description="Repo", html_url="https://github.com/o/r")
        ]
        user.get_starred = user.get_watched = user.get_repos
        user.get_following = user.get_followers = lambda: [
            SimpleNamespace(login="alice", html_url="https://github.com/alice")
        ]
        user.get_gists = lambda: []
        user.get_received_events = user.get_public_events = lambda: [
            SimpleNamespace(
                actor=SimpleNamespace(login="alice"),
                repo=SimpleNamespace(name="o/r"),
                type="PushEvent",
                created_at="2026-11-05",
            )
        ]
        user.add_to_watched = lambda _repo: self.label_calls.append(("watch",))
        user.remove_from_watched = lambda _repo: self.label_calls.append(("unwatch",))
        user.add_to_starred = lambda _repo: self.label_calls.append(("star",))
        user.remove_from_starred = lambda _repo: self.label_calls.append(("unstar",))
        self.user = user
        self._gh = SimpleNamespace(get_user=lambda *_args: user, search_issues=self._search)
        self.notifications_read: list[str] = []

    def _search(self, query: str):
        self.searches.append(query)
        return [_issue(7, "https://github.com/o/r/pull/7")]

    def _repo(self, _name: str):
        label = SimpleNamespace(name="bug", color="ff0000", description="A defect")
        label.delete = lambda: self.label_calls.append(("delete",))
        label.edit = lambda *args: self.label_calls.append(("edit", *args))
        return SimpleNamespace(
            full_name="o/r",
            get_labels=lambda: [label],
            get_label=lambda _name: label,
            create_label=lambda *args: self.label_calls.append(("create", *args)),
            get_forks=lambda: [],
            get_events=lambda: [],
            get_stargazers=lambda: [],
            get_watchers=lambda: [],
            get_contributors=lambda: [],
            html_url="https://github.com/o/r",
            description="Repo",
            default_branch="main",
            stargazers_count=3,
            forks_count=1,
            subscribers_count=2,
            open_issues_count=4,
        )

    def fetch_notification_inbox(self, *, include_read: bool, limit: int, if_modified_since=""):
        from quill.core.github.notification_triage import NotificationInbox
        from quill.core.github.notifications import GitHubNotification

        return NotificationInbox((
            GitHubNotification(
                id="N1",
                repository="o/r",
                reason="review_requested",
                subject_title="Review me",
                subject_type="PullRequest",
                unread=True,
                updated_at="2026-11-05",
                subject_url="https://github.com/o/r/pull/7",
            ),
        ))

    def mark_notification_read(self, notification_id: str) -> None:
        self.notifications_read.append(notification_id)

    def fetch_security_alerts(self, _repo: str, *, limit: int):
        return [
            SimpleNamespace(
                number=1,
                severity="high",
                package="lib",
                summary="Fix needed",
                state="open",
                created_at="2026-11-05",
                html_url="https://github.com/o/r/security/1",
            )
        ]


def test_my_work_combines_categories_without_duplicate_rows() -> None:
    provider = _Provider()
    rows = GitHubExploreClient(provider).fetch("my_work")  # type: ignore[arg-type]
    assert len(rows) == 1
    assert rows[0].kind == "pr"
    assert "Assigned" in rows[0].detail
    assert "Review requested" in rows[0].detail
    assert rows[0].title == "Work 7"
    assert len(provider.searches) == 4


def test_explore_reports_capped_results_but_not_an_exact_limit(monkeypatch) -> None:
    provider = _Provider()
    client = GitHubExploreClient(provider)  # type: ignore[arg-type]
    monkeypatch.setattr(
        provider._gh, "search_issues", lambda _query: [_issue(7, "https://github.com/o/r/issues/7")]
    )

    exact = client.fetch_with_status("search", query="is:issue", limit=1)

    assert exact.complete
    assert len(exact.items) == 1

    monkeypatch.setattr(
        provider._gh,
        "search_issues",
        lambda _query: [
            _issue(7, "https://github.com/o/r/issues/7"),
            _issue(8, "https://github.com/o/r/issues/8"),
        ],
    )
    capped = client.fetch_with_status("search", query="is:issue", limit=1)

    assert not capped.complete
    assert capped.items[0].key == "7"
    assert "showing the first 1 items" in capped.warning


def test_explore_preserves_rows_when_a_later_page_fails(monkeypatch) -> None:
    provider = _Provider()

    def partial_search(_query: str):
        yield _issue(7, "https://github.com/o/r/issues/7")
        raise RuntimeError("rate limit")

    monkeypatch.setattr(provider._gh, "search_issues", partial_search)
    result = GitHubExploreClient(provider).fetch_with_status(  # type: ignore[arg-type]
        "search", query="is:issue", limit=5
    )

    assert len(result.items) == 1
    assert not result.complete
    assert "rate limit" in result.warning


def test_my_work_keeps_successful_categories_when_one_query_fails(monkeypatch) -> None:
    provider = _Provider()
    original_search = provider._search

    def partial_search(query: str):
        if "review-requested" in query:
            raise RuntimeError("permission denied")
        return original_search(query)

    provider._gh.search_issues = partial_search
    result = GitHubExploreClient(provider).fetch_with_status("my_work")  # type: ignore[arg-type]

    assert result.items
    assert not result.complete
    assert "Review requested" in result.warning
    assert "permission denied" in result.warning


def test_attention_queue_combines_categories_and_deduplicates_by_url() -> None:
    provider = _Provider()
    result = GitHubExploreClient(provider).fetch_attention()  # type: ignore[arg-type]

    assert result.complete
    assert len(result.items) == 1
    assert len(provider.searches) == 4
    assert "status:failure" in provider.searches[-1]
    assert "Also:" in result.items[0].detail
    assert result.items[0].title == "Work 7"


def test_attention_queue_scopes_failed_checks_to_selected_repositories() -> None:
    provider = _Provider()
    result = GitHubExploreClient(provider).fetch_attention(  # type: ignore[arg-type]
        repositories=["o/r"], categories=["failed_checks"]
    )

    assert result.complete
    assert len(result.items) == 1
    assert provider.searches == ["is:open is:pr status:failure repo:o/r"]


def test_attention_queue_keeps_results_and_reports_a_failed_source(monkeypatch) -> None:
    provider = _Provider()
    original_search = provider._search

    def partial_search(query: str):
        if "review-requested" in query:
            raise RuntimeError("permission denied")
        return original_search(query)

    provider._gh.search_issues = partial_search
    result = GitHubExploreClient(provider).fetch_attention(  # type: ignore[arg-type]
        categories=["assigned", "review_requested"]
    )

    assert result.items
    assert not result.complete
    assert "Review requested" in result.warning
    assert "permission denied" in result.warning


def test_global_search_and_repository_discovery() -> None:
    provider = _Provider()
    client = GitHubExploreClient(provider)  # type: ignore[arg-type]
    assert client.fetch("search", query="is:issue label:bug")[0].kind == "pr"
    assert provider.searches == ["is:issue label:bug"]
    assert client.fetch("starred")[0].repo == "o/r"
    assert client.fetch("following")[0].key == "alice"
    assert client.fetch("labels", repo="o/r")[0].detail.startswith("Label: bug")
    with pytest.raises(GitHubExploreError, match="repository"):
        client.fetch("pages")


def test_account_write_actions_require_auth_and_map_to_provider() -> None:
    provider = _Provider()
    client = GitHubExploreClient(provider)  # type: ignore[arg-type]
    client.set_watched("o/r", True)
    client.set_starred("o/r", False)
    client.create_label("o/r", "triage", "abcdef", "Needs review")
    client.edit_label("o/r", "bug", "defect", "123456", "Updated")
    client.delete_label("o/r", "bug")
    assert provider.label_calls == [
        ("watch",),
        ("unstar",),
        ("create", "triage", "abcdef", "Needs review"),
        ("edit", "defect", "123456", "Updated"),
        ("delete",),
    ]
    anonymous = GitHubExploreClient(_Provider(False))  # type: ignore[arg-type]
    with pytest.raises(GitHubExploreError, match="Sign in"):
        anonymous.set_watched("o/r", True)


def test_pages_site_and_builds_are_readable(monkeypatch) -> None:
    client = GitHubExploreClient(_Provider())  # type: ignore[arg-type]
    monkeypatch.setattr(
        client,
        "_api_get",
        lambda path: (
            {"html_url": "https://o.github.io/r/", "status": "built", "source": {"branch": "main"}}
            if path.endswith("/pages")
            else [{"status": "built", "created_at": "2026-11-05", "error": None}]
        ),
    )
    rows = client.fetch("pages", repo="o/r")
    assert [row.kind for row in rows] == ["pages", "pages_build"]
    assert "built" in rows[1].detail


@pytest.mark.parametrize(
    ("status", "headers", "message"),
    [
        (401, {}, "invalid or expired"),
        (403, {}, "permissions"),
        (403, {"X-RateLimit-Remaining": "0", "Retry-After": "60"}, "rate limit"),
        (429, {"Retry-After": "60"}, "asked QUILL to wait 60 seconds"),
    ],
)
def test_pages_api_reports_auth_permission_and_rate_limit_errors(
    monkeypatch, status: int, headers: dict[str, str], message: str
) -> None:
    client = GitHubExploreClient(_Provider())  # type: ignore[arg-type]

    class Opener:
        def open(self, request, *, timeout):
            raise HTTPError(request.full_url, status, "API error", headers, None)

    monkeypatch.setattr(explore_core, "build_opener", lambda *_args: Opener())
    with pytest.raises(GitHubExploreError, match=message):
        client._api_get("/repos/o/r/pages")


def test_pages_api_redirect_is_not_followed_with_bearer_token(monkeypatch) -> None:
    client = GitHubExploreClient(_Provider())  # type: ignore[arg-type]
    requests = []

    class Opener:
        def open(self, request, *, timeout):
            requests.append(request)
            raise HTTPError(
                request.full_url,
                302,
                "Moved",
                {"Location": "https://other.example/pages"},
                None,
            )

    monkeypatch.setattr(explore_core, "build_opener", lambda *_args: Opener())
    with pytest.raises(GitHubExploreError, match="was not followed"):
        client._api_get("/repos/o/r/pages")

    assert len(requests) == 1
    assert requests[0].get_header("Authorization") == "Bearer secret"


def test_inbox_activity_chooser_people_and_security_views() -> None:
    provider = _Provider()
    client = GitHubExploreClient(provider)  # type: ignore[arg-type]
    assert client.fetch("notifications")[0].key == "N1"
    client.mark_notification_read("N1")
    assert provider.notifications_read == ["N1"]
    assert client.fetch("activity")[0].kind == "event"
    assert client.fetch("chooser")[0].repo == "o/r"
    assert client.fetch("person_activity", person="alice")[0].kind == "event"
    assert client.fetch("repo_overview", repo="o/r")[0].kind == "repo"
    assert client.fetch("security", repo="o/r")[0].kind == "security"


def test_security_view_names_permission_gaps_instead_of_reporting_no_findings() -> None:
    provider = _Provider()
    provider.fetch_security_alerts = lambda _repo, *, limit: [
        SimpleNamespace(
            number=0,
            state="unavailable",
            severity="",
            package="",
            summary="Code scanning alerts unavailable: 403 permission denied",
            alert_type="Code scanning",
            html_url="https://github.com/o/r",
            created_at="",
        )
    ]

    row = GitHubExploreClient(provider).fetch("security", repo="o/r")[0]  # type: ignore[arg-type]

    assert row.label == "Code scanning alerts unavailable"
    assert "403 permission denied" in row.detail


def test_repository_access_view_lists_collaborator_and_team_permissions(monkeypatch) -> None:
    provider = _Provider()
    client = GitHubExploreClient(provider)  # type: ignore[arg-type]
    target = SimpleNamespace(
        get_collaborators=lambda: [
            SimpleNamespace(
                login="alice",
                permissions={"admin": False, "maintain": False, "push": True, "pull": True},
                html_url="https://github.com/alice",
            )
        ],
        get_teams=lambda: [
            SimpleNamespace(
                name="maintainers",
                slug="maintainers",
                permission="admin",
                html_url="https://github.com/orgs/o/teams/maintainers",
            )
        ],
    )
    monkeypatch.setattr(client, "_repo", lambda _repo: target)

    rows = client.fetch("repo_access", repo="o/r")

    assert len(rows) == 2
    assert "Collaborator: alice — push" in rows[0].label
    assert "Permission: push" in rows[0].detail
    assert "Team: maintainers — admin" in rows[1].label


def test_repository_access_view_requires_sign_in() -> None:
    anonymous = GitHubExploreClient(_Provider(False))  # type: ignore[arg-type]

    with pytest.raises(GitHubExploreError, match="Sign in"):
        anonymous.fetch("repo_access", repo="o/r")


def test_opt_in_repository_metrics_include_health_counts_without_people_rankings(
    monkeypatch,
) -> None:
    provider = _Provider()

    class CountedRows(list):
        totalCount = 7

    target = SimpleNamespace(
        full_name="o/r",
        html_url="https://github.com/o/r",
        open_issues_count=12,
        get_pulls=lambda **_kwargs: CountedRows(),
        get_workflow_runs=lambda **_kwargs: CountedRows(),
        get_deployments=lambda: CountedRows(),
    )
    client = GitHubExploreClient(provider)  # type: ignore[arg-type]
    monkeypatch.setattr(client, "_repo", lambda _repo: target)
    provider.fetch_security_alerts = lambda _repo, *, limit: [
        SimpleNamespace(state="open", alert_type="Dependabot"),
        SimpleNamespace(state="open", alert_type="Code scanning"),
        SimpleNamespace(state="unavailable", alert_type="Secret scanning"),
    ]

    result = client.fetch_with_status("metrics", repo="o/r")

    assert len(result.items) == 1
    assert not result.complete
    assert result.items[0].kind == "metrics"
    assert "Open issues and pull requests: 12" in result.items[0].detail
    assert "Open pull requests: 7" in result.items[0].detail
    assert "Failed workflow runs: 7" in result.items[0].detail
    assert "Security alerts: 2 open" in result.items[0].detail
    assert "unavailable: Secret scanning" in result.items[0].detail
    assert "does not rank contributors" in result.items[0].detail


def test_repository_metrics_require_sign_in() -> None:
    anonymous = GitHubExploreClient(_Provider(False))  # type: ignore[arg-type]

    with pytest.raises(GitHubExploreError, match="Sign in"):
        anonymous.fetch("metrics", repo="o/r")


def test_deployment_view_shows_latest_environment_status_and_sha(monkeypatch) -> None:
    client = GitHubExploreClient(_Provider())  # type: ignore[arg-type]
    latest = SimpleNamespace(
        state="success",
        updated_at="2026-11-06T12:30:00Z",
        created_at="2026-11-06T12:29:00Z",
        creator=SimpleNamespace(login="deployer"),
        description="Deployment finished.",
        target_url="https://ci.example/deploy/42",
        environment_url="https://app.example/",
    )
    deployment = SimpleNamespace(
        id=42,
        environment="production",
        task="deploy",
        sha="a" * 40,
        created_at="2026-11-06T12:00:00Z",
        creator=SimpleNamespace(login="alice"),
        get_statuses=lambda: [latest],
    )
    monkeypatch.setattr(
        client,
        "_repo",
        lambda _repo: SimpleNamespace(get_deployments=lambda: [deployment]),
    )

    row = client.fetch("deployments", repo="o/r")[0]

    assert row.kind == "deployment"
    assert row.label == "production: success"
    assert "Commit: aaaaaaaaaaaa" in row.detail
    assert "Deployment finished." in row.detail
    assert row.url == "https://ci.example/deploy/42"


def test_deployment_view_hides_urls_with_credentials_or_token_queries(monkeypatch) -> None:
    client = GitHubExploreClient(_Provider())  # type: ignore[arg-type]
    status = SimpleNamespace(
        state="in_progress",
        updated_at="",
        created_at="",
        creator=None,
        description="",
        target_url="https://ci.example/deploy/42?access_token=secret",
        environment_url="http://staging.example/",
    )
    deployment = SimpleNamespace(
        id=8,
        environment="staging",
        task="deploy",
        sha="b" * 40,
        created_at="",
        creator=None,
        get_statuses=lambda: [status],
    )
    monkeypatch.setattr(
        client,
        "_repo",
        lambda _repo: SimpleNamespace(get_deployments=lambda: [deployment]),
    )

    row = client.fetch("deployments", repo="o/r")[0]

    assert not row.url
    assert "hidden because it is not a safe HTTPS link" in row.detail
