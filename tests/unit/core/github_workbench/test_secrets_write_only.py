"""Secrets are sealed, write-only and never kept (GitHub PRD decision 12; complete.md 1.3).

Proves, for a repository's, an environment's and an organization's secrets:

* the value is sealed with *that owner's* public key, as a libsodium sealed box
  (what GitHub requires), and only the sealed form and the key's id are sent;
* the value is never read back (no GET of the secret itself), and the list
  says the value is never shown;
* nothing said, logged, cached, previewed or described by Dry Run carries it;
* the sheet's New value field is a write-only SECRET field;
* an organization's secret chooses all, private or selected repositories,
  Change can switch that without a new value, and Repositories Allowed adds
  and removes repositories one at a time.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import pytest
from nacl import encoding, public

from quill.core.github import resource_engine as engine
from quill.core.github.dry_run import DRY_RUN, DryRunStop
from quill.core.github.resource_specs import RESOURCE_SPECS, spec_for
from quill.core.github.rest_transport import RestResponse
from quill.core.github.sheet_catalog import SHEETS
from quill.core.github.sheet_engine import load, save
from quill.core.github.sheet_outcome import HIDDEN_CHANGE, mask_secrets, sentence
from quill.core.workbench.properties import FieldChange, FieldKind, as_text

VALUE = "hunter2-do-not-say"


def _keypair() -> tuple[public.PrivateKey, str]:
    private = public.PrivateKey.generate()
    return private, private.public_key.encode(encoding.Base64Encoder).decode("ascii")


class KeyedApi:
    """Answers each owner's public-key request with its own key, and records every call."""

    def __init__(self) -> None:
        self.keys: dict[str, tuple[public.PrivateKey, str]] = {}
        self.sent: list[tuple[str, str, Any, Any]] = []

    def key_for(self, prefix: str) -> public.PrivateKey:
        private, encoded = _keypair()
        self.keys[prefix] = (private, encoded)
        return private

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body, query))
        if method == "GET" and path.endswith("/public-key"):
            prefix = path.removesuffix("/public-key")
            _private, encoded = self.keys[prefix]
            return RestResponse(200, {}, {"key": encoded, "key_id": f"id-of:{prefix}"})
        if method == "GET":
            return RestResponse(200, {}, {"secrets": [{"name": "TOKEN"}], "total_count": 1})
        return RestResponse(201, {}, {})

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError("no GraphQL here")


def _opened(private: public.PrivateKey, body: dict[str, Any]) -> bytes:
    return bytes(public.SealedBox(private).decrypt(base64.b64decode(body["encrypted_value"])))


SCOPES = [
    ("actions_secrets", "o/r", "/repos/o/r/actions/secrets", {}),
    ("dependabot_secrets", "o/r", "/repos/o/r/dependabot/secrets", {}),
    ("codespaces_secrets", "o/r", "/repos/o/r/codespaces/secrets", {}),
    (
        "environment_secrets",
        "o/r/environments/prod",
        "/repos/o/r/environments/prod/secrets",
        {},
    ),
    ("org_actions_secrets", "acme", "/orgs/acme/actions/secrets", {"visibility": "private"}),
    (
        "org_dependabot_secrets",
        "acme",
        "/orgs/acme/dependabot/secrets",
        {"visibility": "selected"},
    ),
    ("org_codespaces_secrets", "acme", "/orgs/acme/codespaces/secrets", {"visibility": "all"}),
]


@pytest.mark.parametrize(("key", "target", "listed", "extra"), SCOPES)
def test_each_scope_seals_with_its_own_public_key_and_sends_only_the_sealed_form(
    key: str, target: str, listed: str, extra: dict[str, str]
) -> None:
    from quill.core.github.resource_specs_env import ENVIRONMENT_SPECS

    spec = next(s for s in (*RESOURCE_SPECS, *ENVIRONMENT_SPECS) if s.key == key)
    api = KeyedApi()
    api.key_for("/orgs/someone-else/actions/secrets")  # another owner's key, never used here
    private = api.key_for(listed)
    said = engine.create(api, spec, target, {"name": "TOKEN", "value": VALUE, **extra})
    assert VALUE not in said
    gets = [path for method, path, _b, _q in api.sent if method == "GET"]
    assert gets == [f"{listed}/public-key"]  # the owner's key; the secret itself is never read
    method, path, body, _query = api.sent[-1]
    assert (method, path) == ("PUT", f"{listed}/TOKEN")
    assert set(body) == {"encrypted_value", "key_id", *extra}
    assert body["key_id"] == f"id-of:{listed}"
    assert VALUE not in json.dumps(body)
    assert _opened(private, body) == VALUE.encode("utf-8")
    for name, value in extra.items():
        assert body[name] == value


def test_a_sealed_box_cannot_be_opened_with_another_owners_key() -> None:
    from nacl.exceptions import CryptoError

    from quill.core.github.sheets_deploy import seal_secret

    mine, encoded = _keypair()
    theirs, _other = _keypair()
    sealed = base64.b64decode(seal_secret(encoded, VALUE))
    assert public.SealedBox(mine).decrypt(sealed) == VALUE.encode()
    with pytest.raises(CryptoError):
        public.SealedBox(theirs).decrypt(sealed)
    # A sealed box is fresh each time, so two sends of one value never match.
    assert seal_secret(encoded, VALUE) != seal_secret(encoded, VALUE)


def test_a_secrets_list_never_reads_a_value_and_says_so() -> None:
    api = KeyedApi()
    rows = engine.fetch(api, spec_for("org_actions_secrets"), "acme")
    assert rows[0].label.endswith("Its value is never shown.")
    assert [(m, p) for m, p, _b, _q in api.sent] == [("GET", "/orgs/acme/actions/secrets")]


def test_nothing_said_or_logged_carries_the_value(caplog: pytest.LogCaptureFixture) -> None:
    api = KeyedApi()
    api.key_for("/orgs/acme/actions/secrets")
    spec = spec_for("org_actions_secrets")
    with caplog.at_level(logging.DEBUG):
        said = [
            engine.create(api, spec, "acme", {"name": "T", "value": VALUE, "visibility": "all"}),
            engine.edit(api, spec, "acme", "T", {"value": VALUE, "visibility": "all"}),
        ]
    assert all(VALUE not in text for text in said)
    assert VALUE not in caplog.text


def test_dry_run_names_the_fields_it_would_send_never_the_value() -> None:
    from quill.core.github.dry_run import describe_request

    words = describe_request("PUT", "/repos/o/r/actions/secrets/T", {"encrypted_value": "x"})
    assert words == "send PUT /repos/o/r/actions/secrets/T (encrypted_value)"
    from quill.core.github.rest_transport import request_json

    DRY_RUN.set(True)
    try:
        with pytest.raises(DryRunStop) as stopped:
            request_json("t", "PUT", "/repos/o/r/actions/secrets/T", body={"encrypted_value": "z"})
    finally:
        DRY_RUN.set(False)
    assert "encrypted_value" in stopped.value.sentence and "z)" not in stopped.value.sentence


def test_the_value_never_enters_the_read_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.github import workbench_api

    _private, encoded = _keypair()
    sent: list[Any] = []

    def fake(_token: Any, method: str, path: str, **kw: Any) -> RestResponse:
        sent.append((method, path, kw.get("body")))
        if path.endswith("/public-key"):
            return RestResponse(200, {"etag": '"k"'}, {"key": encoded, "key_id": "K"})
        return RestResponse(201, {}, {})

    monkeypatch.setattr(workbench_api, "request_json", fake)
    api = workbench_api.TokenApi("token-for-the-cache-test")
    engine.create(api, spec_for("actions_secrets"), "o/r", {"name": "T", "value": VALUE})
    cache = workbench_api._memory_cache("token-for-the-cache-test")
    assert VALUE not in repr(cache._entries)
    assert all(VALUE not in json.dumps(body or {}) for _m, _p, body in sent)


def test_every_write_only_sheet_field_is_a_secret_field() -> None:
    for kind, sheet in SHEETS.items():
        for key in sheet.secret_fields:
            assert sheet.sheet.field(key).kind is FieldKind.SECRET, (kind, key)
    assert SHEETS["secret"].secret_fields == ("secret_value",)


def test_the_secret_sheet_previews_copies_and_reports_hidden() -> None:
    sheet = SHEETS["secret"]
    typed = [FieldChange("secret_value", "New value", "", VALUE)]
    shown = mask_secrets(typed, sheet.secret_fields)
    assert shown == [FieldChange("secret_value", "New value", None, HIDDEN_CHANGE)]
    assert typed[0].after == VALUE  # the save itself still gets the value
    text = as_text(sheet.sheet, {"name": "TOKEN", "secret_value": VALUE})
    assert "New value: hidden" in text and VALUE not in text


def test_saving_the_sheet_seals_records_only_set_and_never_re_reads_the_value() -> None:
    from tests.github_api_fake import FakeGitHubApi

    private, encoded = _keypair()
    api = FakeGitHubApi()
    api.answer("GET", "/repos/o/r/actions/secrets/TOKEN", {"name": "TOKEN"})
    api.answer("GET", "/repos/o/r/actions/secrets/public-key", {"key_id": "k1", "key": encoded})
    ident = {"repo": "o/r", "name": "TOKEN"}
    loaded = load(api, SHEETS["secret"], ident)
    assert loaded.values["secret_value"] == ""
    outcome = save(
        api,
        SHEETS["secret"],
        ident,
        [FieldChange("secret_value", "New value", "", VALUE)],
        loaded=loaded.values,
        check_conflicts=False,
    )
    assert [(c.key, c.after) for c in outcome.done] == [("secret_value", "(set)")]
    assert VALUE not in sentence("Secret TOKEN", outcome)
    assert outcome.after["secret_value"] == ""
    (method, path, body), *_rest = api.writes()
    assert (method, path) == ("PUT", "/repos/o/r/actions/secrets/TOKEN")
    assert _opened(private, body) == VALUE.encode() and body["key_id"] == "k1"
    assert SHEETS["secret"].writes["secret_value"].undo is False


# -- an organization's secret: who may use it ----------------------------------------------


def test_an_organization_secret_offers_all_private_and_selected() -> None:
    for key in ("org_actions_secrets", "org_dependabot_secrets", "org_codespaces_secrets"):
        spec = spec_for(key)
        visibility = next(f for f in spec.create if f.key == "visibility")
        assert visibility.choices == ("all", "private", "selected")
        assert [f.key for f in spec.edit] == ["value", "visibility"]
        assert spec.edit_method == "PUT" and spec.repositories == "/repositories"
    assert [f.key for f in spec_for("actions_secrets").edit] == ["value"]


def test_change_switches_visibility_and_keeps_the_value_when_it_is_left_empty() -> None:
    api = KeyedApi()
    spec = spec_for("org_actions_secrets")
    said = engine.edit(api, spec, "acme", "TOKEN", {"value": "", "visibility": "selected"})
    assert said == "Changed the secret TOKEN."
    assert api.sent == [
        ("PUT", "/orgs/acme/actions/secrets/TOKEN", {"visibility": "selected"}, None)
    ]


def test_change_with_a_new_value_seals_it_again() -> None:
    api = KeyedApi()
    private = api.key_for("/orgs/acme/actions/secrets")
    engine.edit(
        api, spec_for("org_actions_secrets"), "acme", "TOKEN", {"value": VALUE, "visibility": "all"}
    )
    body = api.sent[-1][2]
    assert body["visibility"] == "all" and _opened(private, body) == VALUE.encode()


def test_selected_repositories_are_added_and_removed_one_at_a_time() -> None:
    from tests.unit.core.github_workbench.test_resource_engine import RepoApi

    for key, base in (
        ("org_actions_secrets", "/orgs/acme/actions/secrets"),
        ("org_dependabot_secrets", "/orgs/acme/dependabot/secrets"),
        ("org_codespaces_secrets", "/orgs/acme/codespaces/secrets"),
    ):
        spec = spec_for(key)
        api = RepoApi()
        had = engine.allowed_repositories(api, spec, "acme", "TOKEN")
        wanted = engine.candidate_repositories(api, spec, "acme")
        said = engine.set_repositories(api, spec, "acme", "TOKEN", had, wanted)
        assert said == "Added 1 repository for TOKEN."
        assert api.sent[-1] == ("PUT", f"{base}/TOKEN/repositories/2", None)
        engine.set_repositories(api, spec, "acme", "TOKEN", wanted, [])
        assert api.sent[-2:] == [
            ("DELETE", f"{base}/TOKEN/repositories/1", None),
            ("DELETE", f"{base}/TOKEN/repositories/2", None),
        ]


def test_choosing_repositories_for_a_secret_open_to_all_says_how_to_switch() -> None:
    from tests.unit.core.github_workbench.test_resource_engine import FakeApi

    with pytest.raises(engine.ResourceError, match="choose Selected repositories"):
        engine.allowed_repositories(
            FakeApi(status={"GET": 409}), spec_for("org_actions_secrets"), "acme", "TOKEN"
        )
