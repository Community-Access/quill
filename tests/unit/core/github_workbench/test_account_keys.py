"""People > My Keys: SSH, GPG and signing keys (GitHub PRD 14.3)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import account_keys as ak
from quill.core.github.rest_transport import GitHubRestError, RestResponse

PUB = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4f jeff@laptop"
PRINT = "SHA256:ZkAslGjFiUHdGf/WUL8rQvkib4PTvQatUV0OUQSncCA"
GPG = "-----BEGIN PGP PUBLIC KEY BLOCK-----\n\nmQINBF...\n-----END PGP PUBLIC KEY BLOCK-----\n"


class FakeApi:
    def __init__(self, status: dict[str, int] | None = None) -> None:
        self.status = status or {}
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        for part, code in self.status.items():
            if part in f"{method} {path}":
                raise GitHubRestError("no", status=code)
        if method != "GET":
            return RestResponse(201, {}, {})
        if path == "/user/keys":
            return RestResponse(
                200,
                {},
                [
                    {
                        "id": 1,
                        "title": "Laptop",
                        "key": PUB,
                        "created_at": "2025-01-02T00:00:00Z",
                        "last_used": "2026-11-17T09:00:00Z",
                    }
                ],
            )
        if path == "/user/gpg_keys":
            return RestResponse(
                200,
                {},
                [
                    {
                        "id": 2,
                        "key_id": "3AA5C34371567BD2",
                        "emails": [{"email": "jeff@example.org"}],
                        "can_sign": True,
                        "expires_at": "2027-01-01T00:00:00Z",
                    }
                ],
            )
        return RestResponse(
            200,
            {},
            [{"id": 3, "title": "Laptop", "key": PUB, "created_at": "2025-01-02T00:00:00Z"}],
        )

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_fingerprints_match_openssh_and_kinds_are_told_apart() -> None:
    assert ak.fingerprint(PUB) == PRINT
    assert ak.fingerprint("not a key") == ""
    assert ak.key_kind(PUB) == "ssh" and ak.key_kind(GPG) == "gpg" and ak.key_kind("x") == ""


def test_every_kind_of_key_reads_as_a_sentence() -> None:
    labels = [row.label for row in ak.fetch_keys(FakeApi())]
    assert labels == [
        f"SSH key Laptop, ED25519, {PRINT}, added 2025-01-02, last used 2026-11-17.",
        "GPG key 3AA5C34371567BD2, for jeff@example.org, signs commits, expires 2027-01-01.",
        f"SSH signing key Laptop, ED25519, {PRINT}, added 2025-01-02.",
    ]


def test_a_refused_kind_is_a_warning_and_the_others_still_list() -> None:
    warnings: list[str] = []
    rows = ak.fetch_keys(FakeApi({"GET /user/gpg_keys": 403}), warnings)
    assert len(rows) == 2 and "admin:gpg_key permission" in warnings[0]


def test_adding_checks_the_key_first_and_says_its_fingerprint() -> None:
    api = FakeApi()
    assert ak.add_key(api, "ssh", "Laptop", PUB) == f"Added SSH key Laptop, {PRINT}."
    assert api.sent[-1] == ("POST", "/user/keys", {"title": "Laptop", "key": PUB})
    assert ak.add_key(api, "gpg", "Work", GPG) == "Added GPG key Work."
    assert api.sent[-1][2]["armored_public_key"].startswith("-----BEGIN PGP")
    with pytest.raises(ak.AccountKeyError, match="not an SSH public key"):
        ak.add_key(api, "signing", "x", GPG)
    with pytest.raises(ak.AccountKeyError, match="private key"):
        ak.add_key(api, "ssh", "x", PUB + "\n-----BEGIN OPENSSH PRIVATE KEY-----")
    with pytest.raises(ak.AccountKeyError, match="already be on an account"):
        ak.add_key(FakeApi({"POST": 422}), "ssh", "x", PUB)


def test_deleting_goes_to_the_kinds_own_path() -> None:
    api = FakeApi()
    assert ak.delete_key(api, "signing:3") == "Deleted the SSH signing key."
    assert api.sent[-1][:2] == ("DELETE", "/user/ssh_signing_keys/3")
    with pytest.raises(ak.AccountKeyError):
        ak.delete_key(api, "other:3")
    assert ak.AccountKeyError.code == "QUILL-GITHUB-ACCOUNT-KEYS"


def test_the_node_reaches_its_loader(monkeypatch: Any) -> None:
    from quill.core.github.explore_extra_views import fetch_extra_view

    monkeypatch.setattr(ak, "fetch_keys", lambda _api, warnings: ["keys"])
    provider = SimpleNamespace(token="t", is_authenticated=True)
    rows = fetch_extra_view(provider, "my_keys", repo="", query="", limit=5, warnings=[])
    assert rows == ["keys"]
