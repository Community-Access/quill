"""Making and deleting tags on their own (GitHub PRD 14.2)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import tags
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class FakeApi:
    def __init__(self, *, tags_there: tuple[str, ...] = (), release: str = "") -> None:
        self.tags, self.release = set(tags_there), release
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        if "/git/ref/tags/" in path:
            if path.rsplit("/", 1)[1] in self.tags:
                return RestResponse(200, {}, {})
            raise GitHubRestError("Not Found", status=404)
        if "/commits/" in path:
            if path.endswith("/nope"):
                raise GitHubRestError("Not Found", status=404)
            return RestResponse(200, {}, {"sha": "abc1234567"})
        if "/releases/tags/" in path:
            if self.release:
                return RestResponse(200, {}, {"name": self.release})
            raise GitHubRestError("Not Found", status=404)
        return RestResponse(201, {}, {})

    def graphql(self, query: str, variables: Any) -> Any:
        raise AssertionError


def test_a_tag_is_made_on_what_was_named() -> None:
    api = FakeApi()
    assert (
        tags.create_tag(api, "o/r", "v1.2.0", "main") == "Made tag v1.2.0 on main, commit abc1234."
    )
    assert api.sent[-1] == (
        "POST",
        "/repos/o/r/git/refs",
        {"ref": "refs/tags/v1.2.0", "sha": "abc1234567"},
    )


def test_bad_names_existing_tags_and_unknown_targets_are_refused_before_sending() -> None:
    assert "cannot be a tag name" in tags.valid_tag_name("v 1")
    assert tags.valid_tag_name("").startswith("A tag needs a name")
    with pytest.raises(tags.TagError, match="already has a tag called v1"):
        tags.create_tag(FakeApi(tags_there=("v1",)), "o/r", "v1", "main")
    api = FakeApi()
    with pytest.raises(tags.TagError, match="no branch, tag or commit called nope"):
        tags.create_tag(api, "o/r", "v2", "nope")
    assert not any(method == "POST" for method, _p, _b in api.sent)
    assert tags.TagError.code == "QUILL-GITHUB-TAGS"


def test_deleting_and_the_release_built_on_a_tag() -> None:
    assert tags.release_for_tag(FakeApi(release="Version 1"), "o/r", "v1") == "Version 1"
    assert tags.release_for_tag(FakeApi(), "o/r", "v1") == ""
    api = FakeApi()
    assert tags.delete_tag(api, "o/r", "v1") == "Deleted tag v1."
    assert api.sent[-1][:2] == ("DELETE", "/repos/o/r/git/refs/tags/v1")
