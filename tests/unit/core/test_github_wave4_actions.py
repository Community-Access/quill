"""Wave 4: repository actions, insights, releases and issue housekeeping, against fake GitHub."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from quill.core.github import (
    issue_housekeeping,
    release_admin,
    repo_actions,
    repo_insights,
)
from quill.core.github.explore import GitHubExploreClient
from quill.core.github.issue_housekeeping import GitHubIssueHousekeeping, SubIssue, move_plan
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.release_admin import (
    GitHubReleaseAdmin,
    ReleaseRecord,
    UploadProgress,
    release_change_sentence,
)
from quill.core.github.repo_actions import GitHubRepoActions, normalize_topics, sync_sentence
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class _Api:
    """Answers ``request_json`` calls from a table; records every call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []
        self.replies: dict[tuple[str, str], Any] = {}

    def __call__(self, token, method, path, *, body=None, query=None, **_kw):
        self.calls.append((method, path, body))
        reply = self.replies.get((method, path), RestResponse(200, {}, None))
        if isinstance(reply, list):
            reply = reply.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> _Api:
    fake = _Api()
    for module in (repo_actions, release_admin, issue_housekeeping):
        monkeypatch.setattr(module, "request_json", fake)
    return fake


# -- Repository actions -------------------------------------------------------------


def test_sync_fork_says_how_many_commits_it_merged(api: _Api) -> None:
    api.replies[("GET", "/repos/me/r")] = RestResponse(
        200,
        {},
        {
            "default_branch": "main",
            "owner": {"login": "me"},
            "parent": {"full_name": "up/r", "default_branch": "main"},
        },
    )
    api.replies[("GET", "/repos/up/r/compare/me:main...main")] = RestResponse(
        200, {}, {"ahead_by": 3}
    )
    api.replies[("POST", "/repos/me/r/merge-upstream")] = RestResponse(
        200, {}, {"merge_type": "fast-forward", "base_branch": "up:main"}
    )
    assert GitHubRepoActions("tok").sync_fork("me/r") == "Merged 3 commits from up:main."
    assert api.calls[-1] == ("POST", "/repos/me/r/merge-upstream", {"branch": "main"})


def test_sync_sentences() -> None:
    assert sync_sentence("none", 0, "up:main", "") == "Already up to date with up:main."
    assert sync_sentence("merge", 1, "up:main", "") == "Merged 1 commit from up:main."
    assert sync_sentence("fast-forward", None, "", "") == "GitHub fast-forwarded the fork."


def test_sync_refuses_a_repository_that_is_not_a_fork(api: _Api) -> None:
    api.replies[("GET", "/repos/me/r")] = RestResponse(200, {}, {"default_branch": "main"})
    with pytest.raises(GitHubItemsError, match="not a fork"):
        GitHubRepoActions("tok").sync_fork("me/r")


def test_caches_list_and_delete(api: _Api) -> None:
    api.replies[("GET", "/repos/o/r/actions/caches")] = RestResponse(
        200,
        {},
        {
            "total_count": 2,
            "actions_caches": [
                {
                    "id": 7,
                    "key": "pip-linux",
                    "ref": "refs/heads/main",
                    "size_in_bytes": 2048,
                    "last_accessed_at": "2026-11-07T10:00:00Z",
                }
            ],
        },
    )
    warnings: list[str] = []
    rows = GitHubRepoActions("tok").list_caches("o/r", limit=10, warnings=warnings)
    assert rows[0].label == "2 Actions caches in o/r, 2.0 KB listed"
    assert rows[1].label == "pip-linux, 2.0 KB, branch main, last used 2026-11-07 10:00"
    assert rows[1].key == "7" and warnings == ["showing 1 of 2 caches"]
    api.replies[("DELETE", "/repos/o/r/actions/caches/7")] = RestResponse(204, {}, None)
    GitHubRepoActions("tok").delete_cache("o/r", "7")
    assert api.calls[-1][:2] == ("DELETE", "/repos/o/r/actions/caches/7")


def test_secret_and_variable_names_never_carry_values(api: _Api) -> None:
    api.replies[("GET", "/repos/o/r/actions/secrets")] = RestResponse(
        200, {}, {"secrets": [{"name": "TOKEN", "updated_at": "2026-10-01T00:00:00Z"}]}
    )
    api.replies[("GET", "/repos/o/r/actions/variables")] = RestResponse(
        200, {}, {"variables": [{"name": "MODE", "value": "very-secret-value"}]}
    )
    api.replies[("GET", "/repos/o/r/environments")] = RestResponse(
        200, {}, {"environments": [{"name": "production"}]}
    )
    api.replies[("GET", "/repos/o/r/environments/production/secrets")] = RestResponse(
        200, {}, {"secrets": [{"name": "DEPLOY_KEY"}]}
    )
    api.replies[("GET", "/repos/o/r/environments/production/variables")] = GitHubRestError(
        "denied", status=403
    )
    warnings: list[str] = []
    rows = GitHubRepoActions("tok").list_secret_names("o/r", limit=50, warnings=warnings)
    labels = [row.label for row in rows]
    assert labels == [
        "Repository secret: TOKEN, updated 2026-10-01",
        "Repository variable: MODE",
        "Environment production secret: DEPLOY_KEY",
    ]
    assert all("very-secret-value" not in row.detail for row in rows)
    assert len(warnings) == 1 and "production" in warnings[0]


def test_topics_are_checked_before_sending(api: _Api) -> None:
    assert normalize_topics("Python, accessibility  python") == ("python", "accessibility")
    with pytest.raises(GitHubItemsError, match="lower-case"):
        normalize_topics("no_underscores")
    api.replies[("PUT", "/repos/o/r/topics")] = RestResponse(200, {}, {"names": ["python"]})
    assert GitHubRepoActions("tok").set_topics("o/r", "python") == ("python",)
    assert api.calls[-1][2] == {"names": ["python"]}


def test_archive_reports_a_reply_that_did_not_archive(api: _Api) -> None:
    api.replies[("PATCH", "/repos/o/r")] = RestResponse(200, {}, {"archived": False})
    with pytest.raises(GitHubItemsError, match="still not archived"):
        GitHubRepoActions("tok").set_archived("o/r", True)


def test_watch_levels_map_to_the_subscription_endpoint(api: _Api) -> None:
    actions = GitHubRepoActions("tok")
    api.replies[("GET", "/repos/o/r/subscription")] = GitHubRestError("nf", status=404)
    assert actions.get_watch_level("o/r") == "not_watching"
    api.replies[("PUT", "/repos/o/r/subscription")] = RestResponse(200, {}, {"ignored": True})
    actions.set_watch_level("o/r", "ignoring")
    assert api.calls[-1] == ("PUT", "/repos/o/r/subscription", {"ignored": True})
    api.replies[("DELETE", "/repos/o/r/subscription")] = RestResponse(204, {}, None)
    actions.set_watch_level("o/r", "not_watching")
    with pytest.raises(GitHubItemsError, match="Releases only"):
        actions.set_watch_level("o/r", "releases")


def test_follow_and_delete_need_github_to_confirm(api: _Api) -> None:
    actions = GitHubRepoActions("tok")
    api.replies[("PUT", "/user/following/alice")] = RestResponse(204, {}, None)
    actions.set_following("@alice", True)
    api.replies[("DELETE", "/repos/o/r")] = RestResponse(200, {}, None)
    with pytest.raises(GitHubItemsError, match="without confirming"):
        actions.delete_repository("o/r")
    api.replies[("DELETE", "/repos/o/r")] = GitHubRestError("Must have admin rights", status=403)
    with pytest.raises(GitHubItemsError, match="delete_repo scope"):
        actions.delete_repository("o/r")


def test_template_creation_returns_what_github_named(api: _Api) -> None:
    api.replies[("POST", "/repos/o/template/generate")] = RestResponse(
        201, {}, {"full_name": "me/new", "html_url": "https://github.com/me/new"}
    )
    assert GitHubRepoActions("tok").create_from_template("o/template", "new") == (
        "me/new",
        "https://github.com/me/new",
    )
    assert api.calls[-1][2] == {"name": "new", "private": True, "include_all_branches": False}


def test_writes_need_a_signed_in_account() -> None:
    with pytest.raises(GitHubItemsError, match="signed-in"):
        GitHubRepoActions(None).set_archived("o/r", True)


# -- Insights and community -------------------------------------------------------


def _reply(data: object, status: int = 200) -> Any:
    return type("R", (), {"data": data, "status": status})()


def test_insights_read_as_sentences_and_a_numbers_list() -> None:
    answers = {
        "/repos/o/r/traffic/views": {
            "count": 1234,
            "uniques": 210,
            "views": [{"timestamp": "2026-11-01T00:00:00Z", "count": 120, "uniques": 30}],
        },
        "/repos/o/r/traffic/clones": {"count": 56, "uniques": 12, "clones": []},
        "/repos/o/r/traffic/popular/referrers": [
            {"referrer": "google.com", "count": 9, "uniques": 1}
        ],
        "/repos/o/r/traffic/popular/paths": [{"path": "/o/r", "title": "o/r", "count": 4}],
        "/repos/o/r/contributors": [{"login": "jeff", "contributions": 41}],
    }
    rows = repo_insights.fetch_insights(
        "tok", "o/r", limit=10, warnings=[], get=lambda path, _q: _reply(answers[path])
    )
    labels = [row.label for row in rows]
    assert labels[0] == (
        "o/r: 1,234 views (210 unique) and 56 clones (12 unique) in the last 14 days, "
        "1 contributor."
    )
    assert "Views on 2026-11-01: 120 views, 30 unique visitors" in labels
    assert "Referring site google.com: 9 views, 1 unique visitor" in labels
    assert "Contributor jeff: 41 commits" in labels


def test_insights_say_push_access_is_needed_and_still_list_contributors() -> None:
    def get(path: str, _query: object) -> Any:
        if "/traffic/" in path:
            raise GitHubRestError("Must have push access", status=403)
        return _reply([{"login": "jeff", "contributions": 1}])

    warnings: list[str] = []
    rows = repo_insights.fetch_insights("tok", "o/r", limit=5, warnings=warnings, get=get)
    assert "Traffic needs push access to o/r" in rows[0].label
    assert rows[-1].label == "Contributor jeff: 1 commit"
    assert warnings and "push access" in warnings[0]


def test_community_profile_is_a_checklist_in_words() -> None:
    rows = repo_insights.community_rows(
        "o/r",
        {
            "health_percentage": 57,
            "files": {
                "readme": {"html_url": "https://github.com/o/r/blob/main/README.md"},
                "license": {"html_url": "https://github.com/o/r/blob/main/LICENSE"},
                "contributing": None,
                "code_of_conduct": None,
                "issue_template": None,
                "pull_request_template": None,
            },
        },
    )
    assert rows[0].label == (
        "Community profile for o/r: 57 percent. Present: README, License. Missing: "
        "Contributing guide, Code of conduct, Issue templates, Pull request template."
    )
    assert rows[1].label == "README: present" and rows[3].label == "Contributing guide: missing"


def test_explore_routes_the_new_views(monkeypatch) -> None:
    class Provider:
        is_authenticated = True
        token = "tok"
        _gh = None

    from quill.core.github import explore_extra_views

    monkeypatch.setattr(
        explore_extra_views,
        "fetch_community_profile",
        lambda token, repo: [repo_insights.community_rows(repo, {})[0]],
    )
    rows = GitHubExploreClient(Provider()).fetch("community", repo="o/r")  # type: ignore[arg-type]
    assert rows[0].label.startswith("Community profile for o/r: 0 percent.")


# -- Releases -----------------------------------------------------------------------


RELEASE = {
    "id": 5,
    "tag_name": "v1.0",
    "name": "One",
    "body": "Notes",
    "draft": True,
    "prerelease": False,
    "assets": [{"id": 9, "name": "app.zip", "size": 10}],
}


def test_find_release_reaches_drafts_and_edit_says_what_changed(api: _Api) -> None:
    api.replies[("GET", "/repos/o/r/releases")] = RestResponse(200, {}, [RELEASE])
    admin = GitHubReleaseAdmin("tok")
    record = admin.find_release("o/r", "v1.0")
    assert record.id == 5 and record.asset_named("app.zip") is not None
    api.replies[("PATCH", "/repos/o/r/releases/5")] = RestResponse(
        200, {}, {**RELEASE, "draft": False, "prerelease": True}
    )
    after, sentence = admin.edit_release(
        "o/r", record, name="One", body="Notes", draft=False, prerelease=True
    )
    assert not after.draft
    assert sentence == "Release One: published, marked a prerelease."


def test_edit_refuses_to_claim_a_publish_github_did_not_do(api: _Api) -> None:
    record = release_admin.parse_release(RELEASE)
    api.replies[("PATCH", "/repos/o/r/releases/5")] = RestResponse(200, {}, RELEASE)
    with pytest.raises(GitHubItemsError, match="still a draft"):
        GitHubReleaseAdmin("tok").edit_release(
            "o/r", record, name="One", body="Notes", draft=False, prerelease=False
        )


def test_release_change_sentence_with_no_change() -> None:
    record = release_admin.parse_release(RELEASE)
    assert release_change_sentence(record, record) == (
        "Release One: GitHub confirmed it with no changes."
    )


def test_delete_asset_hits_its_endpoint(api: _Api) -> None:
    record = release_admin.parse_release(RELEASE)
    api.replies[("DELETE", "/repos/o/r/releases/assets/9")] = RestResponse(204, {}, None)
    GitHubReleaseAdmin("tok").delete_asset("o/r", record.assets[0])
    assert api.calls[-1][:2] == ("DELETE", "/repos/o/r/releases/assets/9")


def test_upload_progress_is_said_at_quarter_steps() -> None:
    said: list[int] = []
    progress = UploadProgress(1000, said.append)
    for _ in range(10):
        progress.advance(100)
    assert said == [25, 50, 75]


class _UploadResponse:
    status = 201

    def read(self, _limit: int) -> bytes:
        return json.dumps({"id": 77, "name": "notes.txt", "size": 4}).encode()

    def __enter__(self) -> _UploadResponse:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class _UploadOpener:
    def __init__(self) -> None:
        self.request: Any = None
        self.sent = b""

    def open(self, request: Any, timeout: int) -> _UploadResponse:
        self.request = request
        while chunk := request.data.read(2):
            self.sent += chunk
        return _UploadResponse()


def test_upload_goes_to_the_uploads_host_and_reports_the_stored_asset(tmp_path) -> None:
    source = tmp_path / "notes.txt"
    source.write_bytes(b"abcd")
    opener = _UploadOpener()
    said: list[int] = []
    record = ReleaseRecord(id=5, tag="v1.0")
    asset = GitHubReleaseAdmin("tok").upload_release_asset(
        "o/r", record, source, progress=said.append, opener=opener
    )
    assert asset.id == 77 and opener.sent == b"abcd"
    assert opener.request.full_url == (
        "https://uploads.github.com/repos/o/r/releases/5/assets?name=notes.txt"
    )
    assert opener.request.get_header("Content-length") == "4"
    assert said == [50]


def test_upload_refuses_a_name_already_on_the_release(tmp_path) -> None:
    source = tmp_path / "app.zip"
    source.write_bytes(b"x")
    record = release_admin.parse_release(RELEASE)
    with pytest.raises(GitHubItemsError, match="already has an asset named app.zip"):
        GitHubReleaseAdmin("tok").upload_release_asset("o/r", record, source, opener=object())


def test_upload_failure_is_put_in_words(tmp_path) -> None:
    from email.message import Message
    from urllib.error import HTTPError

    source = tmp_path / "a.bin"
    source.write_bytes(b"x")

    class Failing:
        def open(self, request: Any, timeout: int) -> Any:
            raise HTTPError(
                request.full_url,
                422,
                "bad",
                Message(),
                io.BytesIO(b'{"message": "Validation Failed"}'),
            )

    with pytest.raises(GitHubItemsError, match="GitHub refused it: Validation Failed"):
        GitHubReleaseAdmin("tok").upload_release_asset(
            "o/r", ReleaseRecord(id=5, tag="v1"), source, opener=Failing()
        )


# -- Issue housekeeping -----------------------------------------------------------


def _graphql(data: dict[str, Any]) -> RestResponse:
    return RestResponse(200, {}, {"data": data})


def test_lock_and_unlock(api: _Api) -> None:
    api.replies[("PUT", "/repos/o/r/issues/3/lock")] = RestResponse(204, {}, None)
    api.replies[("DELETE", "/repos/o/r/issues/3/lock")] = RestResponse(204, {}, None)
    housekeeping = GitHubIssueHousekeeping("tok")
    housekeeping.lock("o/r", 3, "too heated")
    assert api.calls[-1] == ("PUT", "/repos/o/r/issues/3/lock", {"lock_reason": "too heated"})
    housekeeping.unlock("o/r", 3)
    with pytest.raises(GitHubItemsError, match="lock reason"):
        housekeeping.lock("o/r", 3, "boring")


def test_transfer_reports_the_new_address(api: _Api) -> None:
    api.replies[("POST", "/graphql")] = [
        _graphql({"repository": {"issue": {"id": "I_1"}}}),
        _graphql({"repository": {"id": "R_2"}}),
        _graphql({
            "transferIssue": {
                "issue": {
                    "number": 40,
                    "url": "https://github.com/o/other/issues/40",
                    "repository": {"nameWithOwner": "o/other"},
                }
            }
        }),
    ]
    message = GitHubIssueHousekeeping("tok").transfer("o/r", 3, "o/other")
    assert message == "Moved to o/other as #40: https://github.com/o/other/issues/40"
    assert api.calls[-1][2]["variables"] == {"issue": "I_1", "repo": "R_2"}


def test_pin_says_when_github_did_not_pin(api: _Api) -> None:
    api.replies[("POST", "/graphql")] = [
        _graphql({"repository": {"issue": {"id": "I_1"}}}),
        _graphql({"pinIssue": {"issue": {"isPinned": False}}}),
    ]
    with pytest.raises(GitHubItemsError, match="still not pinned"):
        GitHubIssueHousekeeping("tok").set_pinned("o/r", 3, True)


def test_graphql_errors_are_said(api: _Api) -> None:
    api.replies[("POST", "/graphql")] = RestResponse(
        200, {}, {"errors": [{"message": "Pinned issues limit reached"}]}
    )
    with pytest.raises(GitHubItemsError, match="Pinned issues limit reached"):
        GitHubIssueHousekeeping("tok").set_pinned("o/r", 3, True)


def test_issue_types_and_setting_one(api: _Api) -> None:
    api.replies[("POST", "/graphql")] = [
        _graphql({
            "repository": {
                "issueTypes": {
                    "nodes": [
                        {"id": "T1", "name": "Bug", "description": "Broken", "isEnabled": True},
                        {"id": "T2", "name": "Old", "isEnabled": False},
                    ]
                }
            }
        }),
        _graphql({"repository": {"issue": {"id": "I_1"}}}),
        _graphql({"updateIssueIssueType": {"issue": {"issueType": {"name": "Bug"}}}}),
    ]
    housekeeping = GitHubIssueHousekeeping("tok")
    types = housekeeping.issue_types("o/r")
    assert [t.label for t in types] == ["Bug: Broken"]
    assert housekeeping.set_issue_type("o/r", 3, types[0]) == "Bug"


def test_sub_issue_moves_and_the_order_is_read_back(api: _Api) -> None:
    order = [SubIssue(1, 10, "a"), SubIssue(2, 11, "b"), SubIssue(3, 12, "c")]
    body, expected = move_plan(order, 2, -1)
    assert body == {"sub_issue_id": 3, "before_id": 2}
    assert [item.number for item in expected] == [10, 12, 11]
    body, _ = move_plan(order, 0, 1)
    assert body == {"sub_issue_id": 1, "after_id": 2}
    with pytest.raises(GitHubItemsError, match="already first"):
        move_plan(order, 0, -1)
    api.replies[("GET", "/repos/o/r/issues/5/sub_issues")] = RestResponse(
        200,
        {},
        [
            {"id": 1, "number": 10, "title": "a"},
            {"id": 3, "number": 12, "title": "c"},
            {"id": 2, "number": 11, "title": "b"},
        ],
    )
    result = GitHubIssueHousekeeping("tok").move_sub_issue("o/r", 5, order, 2, -1)
    assert [item.number for item in result] == [10, 12, 11]
    assert ("PATCH", "/repos/o/r/issues/5/sub_issues/priority") in [c[:2] for c in api.calls]
