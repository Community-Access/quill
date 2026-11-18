"""Dry Run: every GitHub write stops at the door and says what it would have sent (PRD 22.8)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from quill.core.github import dry_run
from quill.core.github.dry_run import DRY_RUN, DryRunStop, is_mutation, stop_request_if_dry
from quill.core.github.rest_transport import request_json


@pytest.fixture
def dry() -> Iterator[None]:
    DRY_RUN.set(True)
    yield
    DRY_RUN.set(False)


class _Refuse:
    """An opener that fails the test if anything reaches the network."""

    def open(self, *_a: object, **_k: object) -> object:
        raise AssertionError("a dry run reached the network")


def test_rest_writes_stop_before_the_network_and_say_what(dry: None) -> None:
    with pytest.raises(DryRunStop) as stopped:
        request_json(
            "t",
            "PATCH",
            "/repos/o/r/issues/7",
            body={"state": "closed", "state_reason": "not_planned"},
            opener=_Refuse(),
        )
    assert stopped.value.sentence == (
        "Dry run: QUILL would send PATCH /repos/o/r/issues/7 (state, state_reason). "
        "Nothing was changed."
    )
    assert stopped.value.code == "QUILL-GITHUB-DRY-RUN"


def test_graphql_mutations_stop_and_queries_pass(dry: None) -> None:
    mutation = "mutation($id: ID!) {\n  closeIssue(input: {issueId: $id}) { issue { id } }\n}"
    with pytest.raises(DryRunStop, match="QUILL would ask GitHub for closeIssue"):
        stop_request_if_dry("POST", "/graphql", {"query": mutation})
    stop_request_if_dry("POST", "/graphql", {"query": "query { viewer { login } }"})
    stop_request_if_dry("GET", "/repos/o/r", None)
    assert is_mutation("# a comment\nmutation { addStar(input: {}) { clientMutationId } }")
    assert not is_mutation("{ viewer { login } }")


def test_off_means_nothing_is_stopped() -> None:
    assert not DRY_RUN.on
    stop_request_if_dry("DELETE", "/repos/o/r", None)
    dry_run.stop_if_dry("delete everything")


def test_pygithub_writes_stop_at_the_write_check(dry: None) -> None:
    from quill.core.github.items_provider import GitHubItemsProvider

    provider = GitHubItemsProvider.__new__(GitHubItemsProvider)
    provider._token = "t"
    with pytest.raises(DryRunStop, match="QUILL would merge a pull request"):
        provider._require_write_access("merge a pull request")
