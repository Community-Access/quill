"""Single commands on rows: deletes, webhooks, merges, dispatches and source downloads."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import row_admin as ra
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class _Api:
    def __init__(self, replies: dict[str, Any] | None = None) -> None:
        self.replies, self.sent = replies or {}, []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> RestResponse:
        self.sent.append((method, path, body))
        reply = self.replies.get(f"{method} {path}", RestResponse(200, {}, {}))
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, RestResponse) else RestResponse(200, {}, reply)


def test_a_release_is_found_by_tag_and_its_tag_goes_only_when_asked() -> None:
    api = _Api({"GET /repos/o/r/releases/tags/v1.0": {"id": 9}})
    assert ra.delete_release(api, "o/r", "v1.0") == "Deleted the release v1.0. The tag v1.0 stays."
    assert api.sent[-1][:2] == ("DELETE", "/repos/o/r/releases/9")
    assert ra.delete_release(api, "o/r", "v1.0", delete_tag=True).endswith("and its tag.")
    assert api.sent[-1][:2] == ("DELETE", "/repos/o/r/git/refs/tags/v1.0")


def test_a_milestone_is_deleted_by_title_and_its_issues_are_counted() -> None:
    api = _Api({
        "GET /repos/o/r/milestones": [
            {"title": "Spring", "number": 3, "open_issues": 2, "closed_issues": 1}
        ]
    })
    assert (
        ra.delete_milestone(api, "o/r", "Spring")
        == "Deleted the milestone Spring. Its 3 issues stay, with no milestone."
    )
    assert api.sent[-1][:2] == ("DELETE", "/repos/o/r/milestones/3")
    with pytest.raises(ra.RowAdminError, match="no milestone"):
        ra.delete_milestone(api, "o/r", "Autumn")


def test_an_active_deployment_is_explained_not_failed_plainly() -> None:
    api = _Api({"DELETE /repos/o/r/deployments/5": GitHubRestError("no", status=422)})
    with pytest.raises(ra.RowAdminError, match="only an inactive"):
        ra.delete_deployment(api, "o/r", "5")


def test_webhooks_test_push_and_turn_on_or_off_for_repos_and_organizations() -> None:
    api = _Api()
    ra.test_push(api, "o/r", "12")
    assert api.sent[-1][:2] == ("POST", "/repos/o/r/hooks/12/tests")
    assert ra.set_webhook_active(api, "acme", "7", False).startswith("The webhook is off")
    assert api.sent[-1] == ("PATCH", "/orgs/acme/hooks/7", {"active": False})


def test_a_merge_says_conflict_nothing_to_do_or_the_new_commit() -> None:
    api = _Api({"POST /repos/o/r/merges": RestResponse(201, {}, {"sha": "abcdef123"})})
    assert ra.merge_branch(api, "o/r", "main", "topic") == "Merged topic into main as abcdef1."
    api = _Api({"POST /repos/o/r/merges": RestResponse(204, {}, None)})
    assert "nothing to merge" in ra.merge_branch(api, "o/r", "main", "topic")
    api = _Api({"POST /repos/o/r/merges": GitHubRestError("c", status=409)})
    with pytest.raises(ra.RowAdminError, match="conflict"):
        ra.merge_branch(api, "o/r", "main", "topic")


def test_a_dispatch_needs_a_name_and_a_json_object() -> None:
    api = _Api()
    ra.repository_dispatch(api, "o/r", "deploy", '{"env": "test"}')
    assert api.sent[-1] == (
        "POST",
        "/repos/o/r/dispatches",
        {"event_type": "deploy", "client_payload": {"env": "test"}},
    )
    for bad in ("[1]", "{not json"):
        with pytest.raises(ra.RowAdminError):
            ra.repository_dispatch(api, "o/r", "deploy", bad)
    with pytest.raises(ra.RowAdminError):
        ra.repository_dispatch(api, "o/r", "  ")


def test_source_downloads_name_the_ref_and_use_the_api() -> None:
    zipped = ra.source_download("o/site", "release/2", "zip")
    assert zipped.archive_download_url == "https://api.github.com/repos/o/site/zipball/release%2F2"
    assert zipped.name == "site-release-2"
    assert ra.source_download("o/site", "v1", "tar").archive_download_url.endswith("/tarball/v1")
