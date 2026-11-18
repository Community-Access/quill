"""The resource engine and its descriptions (GitHub PRD section 19)."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import resource_engine as engine
from quill.core.github.resource_specs import RESOURCE_SPECS, spec_for
from quill.core.github.rest_transport import GitHubRestError, RestResponse

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = base64.b64encode(bytes(range(32))).decode()


class FakeApi:
    def __init__(self, data: Any = None, status: dict[str, int] | None = None) -> None:
        self.data, self.status = data, status or {}
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        for part, code in self.status.items():
            if part in f"{method} {path}":
                raise GitHubRestError("no", status=code)
        if path.endswith("/public-key"):
            return RestResponse(200, {}, {"key": PUBLIC, "key_id": "K1"})
        return RestResponse(200, {}, self.data if method == "GET" else {})

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_every_description_names_real_endpoints_and_unique_nodes() -> None:
    snapshot = json.loads((ROOT / "quill/data/github_api/rest.json").read_text("utf-8"))
    real = {f"{op['method']} {op['path']}" for op in snapshot["operations"]}
    keys = [spec.key for spec in RESOURCE_SPECS]
    assert len(keys) == len(set(keys))
    for spec in RESOURCE_SPECS:
        assert set(spec.endpoints()) <= real, (spec.key, set(spec.endpoints()) - real)
        assert spec.help.endswith(".") and spec.sentence


def test_a_list_reads_as_sentences_and_an_empty_one_says_how_to_fill_it() -> None:
    spec = spec_for("actions_variables")
    api = FakeApi({
        "variables": [{"name": "CHANNEL", "value": "beta", "updated_at": "2026-11-17T00:00:00Z"}]
    })
    rows = engine.fetch(api, spec, "o/r")
    assert rows[0].label == "CHANNEL is beta, changed 2026-11-17."
    assert rows[0].kind == "resource" and rows[0].key == "actions_variables:CHANNEL"
    assert api.sent[0][1] == "/repos/o/r/actions/variables"
    warnings: list[str] = []
    assert engine.fetch(FakeApi({"variables": []}), spec, "o/r", warnings) == []
    assert warnings == ["No variables yet. Ctrl+N adds one."]


def test_a_secret_is_sealed_with_the_owners_key_before_it_is_sent() -> None:
    spec = spec_for("org_actions_secrets")
    api = FakeApi()
    said = engine.create(
        api, spec, "acme", {"name": "TOKEN", "value": "s3cret", "visibility": "private"}
    )
    assert said == "Added the secret TOKEN." and "s3cret" not in said
    method, path, body = api.sent[-1]
    assert (method, path) == ("PUT", "/orgs/acme/actions/secrets/TOKEN")
    assert body["key_id"] == "K1" and body["visibility"] == "private"
    assert "s3cret" not in json.dumps(body) and base64.b64decode(body["encrypted_value"])


def test_paths_from_the_base_bools_lists_and_deleting_by_body() -> None:
    api = FakeApi()
    engine.create(api, spec_for("org_members"), "acme", {"username": "sam", "role": "member"})
    assert api.sent[-1] == ("PUT", "/orgs/acme/memberships/sam", {"role": "member"})
    engine.create(
        api,
        spec_for("org_issue_types"),
        "acme",
        {"name": "Bug", "description": "", "is_enabled": "true"},
    )
    assert api.sent[-1][2] == {"name": "Bug", "is_enabled": True}
    engine.create(api, spec_for("my_emails"), "", {"emails": "a@b.org"})
    assert api.sent[-1] == ("POST", "/user/emails", {"emails": ["a@b.org"]})
    engine.delete(api, spec_for("my_emails"), "", "a@b.org")
    assert api.sent[-1] == ("DELETE", "/user/emails", {"emails": ["a@b.org"]})
    engine.delete(api, spec_for("security_managers"), "acme", "sec-team")
    assert api.sent[-1][:2] == ("DELETE", "/orgs/acme/security-managers/teams/sec-team")
    said = engine.edit(api, spec_for("actions_variables"), "o/r", "CHANNEL", {"value": "stable"})
    assert said == "Changed the variable CHANNEL."
    assert api.sent[-1] == ("PATCH", "/repos/o/r/actions/variables/CHANNEL", {"value": "stable"})


def test_missing_answers_and_refusals_are_said() -> None:
    with pytest.raises(engine.ResourceError, match="is needed"):
        engine.create(FakeApi(), spec_for("actions_variables"), "o/r", {"name": "X"})
    with pytest.raises(engine.ResourceError, match="administer"):
        engine.fetch(FakeApi(status={"GET": 403}), spec_for("org_members"), "acme")
    assert engine.ResourceError.code == "QUILL-GITHUB-RESOURCE"


def test_every_list_reaches_the_engine_through_explore(monkeypatch: Any) -> None:
    from quill.core.github.explore_extra_views import fetch_extra_view

    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(
        engine, "fetch", lambda _api, spec, target, warnings: seen.append((spec.key, target)) or []
    )
    provider = SimpleNamespace(token="t", is_authenticated=True)
    for spec in RESOURCE_SPECS:
        target = {"repository": "o/r", "organization": "acme", "user": ""}[spec.scope]
        rows = fetch_extra_view(
            provider, f"res_{spec.key}", repo=target, query="", limit=5, warnings=[]
        )
        assert rows == []
    assert len(seen) == len(RESOURCE_SPECS)
