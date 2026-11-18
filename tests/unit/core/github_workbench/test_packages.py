"""Repositories > My Packages (GitHub PRD 14.2)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import packages as pk
from quill.core.github.rest_transport import GitHubRestError, RestResponse

ENGINE = {
    "name": "quill-engine",
    "package_type": "container",
    "visibility": "private",
    "version_count": 12,
    "repository": {"full_name": "community-access/quill"},
    "updated_at": "2026-11-12T10:00:00Z",
    "html_url": "https://github.com/users/jeff/packages/container/package/quill-engine",
}
VERSIONS = [
    {"id": 1, "name": "sha256:aaa", "updated_at": "2026-10-01T00:00:00Z"},
    {
        "id": 2,
        "name": "sha256:bbb",
        "updated_at": "2026-11-12T00:00:00Z",
        "metadata": {"container": {"tags": ["latest", "1.2"]}},
    },
]


class FakeApi:
    def __init__(self, status: dict[str, int] | None = None) -> None:
        self.status = status or {}
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, query))
        for part, code in self.status.items():
            if part in f"{method} {path} {query}":
                raise GitHubRestError("no", status=code)
        if path == "/user/packages":
            return RestResponse(200, {}, [ENGINE] if query["package_type"] == "container" else [])
        if path.endswith("/versions"):
            return RestResponse(200, {}, VERSIONS)
        return RestResponse(204, {}, None)

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_every_type_is_asked_for_and_each_package_reads_whole() -> None:
    api = FakeApi({"'docker'": 400})
    rows = pk.fetch_packages(api)
    asked = [q["package_type"] for _m, p, q in api.sent if p == "/user/packages"]
    assert asked == list(pk.PACKAGE_TYPES)
    assert [row.label for row in rows] == [
        "container quill-engine: private, 12 versions, from community-access/quill, "
        "updated 2026-11-12."
    ]
    assert rows[0].kind == "package" and rows[0].key == "container/quill-engine"


def test_without_the_scope_the_sentence_says_which_permission() -> None:
    with pytest.raises(pk.PackageError, match="needs the read:packages permission"):
        pk.fetch_packages(FakeApi({"/user/packages": 403}))


def test_versions_newest_first_with_tags_and_deleting_one() -> None:
    api = FakeApi()
    versions = pk.fetch_versions(api, "container", "quill-engine")
    assert [v.label for v in versions] == [
        "sha256:bbb, tagged latest, 1.2, updated 2026-11-12",
        "sha256:aaa, untagged, updated 2026-10-01",
    ]
    said = pk.delete_version(api, "container", "quill-engine", versions[1])
    assert said == "Deleted version sha256:aaa of quill-engine. GitHub can restore it for 30 days."
    assert api.sent[-1][:2] == ("DELETE", "/user/packages/container/quill-engine/versions/1")


def test_the_last_version_cannot_go_and_a_package_can() -> None:
    version = pk.PackageVersion(1, "1.0.0", (), "")
    with pytest.raises(pk.PackageError, match="only version"):
        pk.delete_version(FakeApi({"DELETE": 400}), "npm", "left-pad", version)
    api = FakeApi()
    assert pk.delete_package(api, "npm", "left-pad") == (
        "Deleted the npm package left-pad. GitHub can restore it for 30 days."
    )
    assert api.sent[-1][:2] == ("DELETE", "/user/packages/npm/left-pad")
    with pytest.raises(pk.PackageError, match="delete:packages"):
        pk.delete_package(FakeApi({"DELETE": 403}), "npm", "left-pad")
    assert pk.PackageError.code == "QUILL-GITHUB-PACKAGES"


def test_the_my_packages_node_reaches_its_loader(monkeypatch: Any) -> None:
    """The node's view must be one fetch_extra_view answers, or the node never loads."""
    from types import SimpleNamespace

    from quill.core.github.explore_extra_views import fetch_extra_view
    from quill.core.github.workbench_tree import GITHUB_TREE

    loaders = {node.loader for _template, node in GITHUB_TREE.all_nodes()}
    assert "explore:my_packages" in loaders
    monkeypatch.setattr(pk, "fetch_packages", lambda _api, limit: ["a row"])
    provider = SimpleNamespace(token="t", is_authenticated=True)
    rows = fetch_extra_view(provider, "my_packages", repo="", query="", limit=5, warnings=[])
    assert rows == ["a row"]
