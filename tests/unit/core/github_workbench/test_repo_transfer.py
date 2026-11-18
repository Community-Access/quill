"""Transferring a repository (GitHub PRD 14.2)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import repo_transfer as rt
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class FakeApi:
    def __init__(self, data: Any = None, status: int = 0) -> None:
        self.data, self.status = data, status
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        if self.status:
            raise GitHubRestError("no", status=self.status)
        return RestResponse(202, {}, self.data)

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_a_transfer_to_an_organization_says_where_it_landed() -> None:
    api = FakeApi({"full_name": "community-access/r"})
    said = rt.transfer_repository(api, "jeff/r", "@community-access")
    assert said == "Transferred jeff/r; it is now community-access/r. The old address redirects."
    assert api.sent == [("POST", "/repos/jeff/r/transfer", {"new_owner": "community-access"})]


def test_a_transfer_to_a_person_waits_for_them() -> None:
    said = rt.transfer_repository(FakeApi({"full_name": "jeff/r"}), "jeff/r", "sam")
    assert "A person has a day to accept" in said


def test_bad_owners_and_refusals_are_said_and_nothing_is_sent() -> None:
    api = FakeApi()
    for owner, words in (
        ("", "needs the new owner"),
        ("a b", "not a GitHub account"),
        ("JEFF", "already belongs"),
    ):
        with pytest.raises(rt.TransferError, match=words):
            rt.transfer_repository(api, "jeff/r", owner)
    assert api.sent == []
    with pytest.raises(rt.TransferError, match="Only an owner or administrator"):
        rt.transfer_repository(FakeApi(status=403), "jeff/r", "sam")
    with pytest.raises(rt.TransferError, match="already have a repository called r"):
        rt.transfer_repository(FakeApi(status=422), "jeff/r", "sam")
    assert rt.TransferError.code == "QUILL-GITHUB-REPO-TRANSFER"
