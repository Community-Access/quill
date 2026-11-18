"""Settings > Webhooks, Deploy Keys and Autolinks (GitHub PRD 14.3)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import repo_settings_lists as sl
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from tests.unit.core.github_workbench.test_account_keys import PRINT, PUB

HOOK = {
    "id": 9,
    "active": True,
    "events": ["push", "pull_request"],
    "config": {"url": "https://ci.example.org/hook", "content_type": "json"},
    "last_response": {"code": 200, "status": "active", "message": "OK"},
}
DELIVERIES = [
    {
        "id": 5,
        "event": "push",
        "status": "OK",
        "status_code": 200,
        "delivered_at": "2026-11-18T09:30:00Z",
        "redelivery": False,
    },
    {
        "id": 4,
        "event": "pull_request",
        "action": "opened",
        "status": "Invalid",
        "status_code": 502,
        "delivered_at": "2026-11-18T09:00:00Z",
        "redelivery": True,
    },
]


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
        if path.endswith("/hooks"):
            return RestResponse(
                200,
                {},
                [
                    HOOK,
                    {
                        **HOOK,
                        "id": 10,
                        "active": False,
                        "events": ["*"],
                        "last_response": {"code": None},
                    },
                ],
            )
        if path.endswith("/deliveries"):
            return RestResponse(200, {}, DELIVERIES)
        if path.endswith("/keys"):
            return RestResponse(
                200,
                {},
                [
                    {
                        "id": 3,
                        "title": "CI",
                        "key": PUB,
                        "read_only": True,
                        "created_at": "2026-01-02T00:00:00Z",
                    }
                ],
            )
        return RestResponse(
            200,
            {},
            [
                {
                    "id": 7,
                    "key_prefix": "TICKET-",
                    "url_template": "https://jira.example.org/browse/TICKET-<num>",
                    "is_alphanumeric": False,
                }
            ],
        )

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_each_list_reads_as_sentences() -> None:
    api = FakeApi()
    hooks = [row.label for row in sl.fetch_webhooks(api, "o/r")]
    assert hooks == [
        "https://ci.example.org/hook: on, JSON, push and pull_request, "
        "last delivery succeeded (200).",
        "https://ci.example.org/hook: off, JSON, every event, never delivered.",
    ]
    keys = sl.fetch_deploy_keys(api, "o/r")
    assert keys[0].label == f"Deploy key CI, read only, {PRINT}, added 2026-01-02, never used."
    links = sl.fetch_autolinks(api, "o/r")
    assert links[0].label == (
        "TICKET- links to https://jira.example.org/browse/TICKET-<num>, numbers only."
    )
    assert [row.kind for row in (sl.fetch_webhooks(api, "o/r")[0], keys[0], links[0])] == [
        "webhook",
        "deploy_key",
        "autolink",
    ]


def test_adding_a_webhook_sends_the_secret_once_and_never_says_it() -> None:
    api = FakeApi()
    said = sl.add_webhook(api, "o/r", "https://x.org/h", events=["push"], secret="s3cret")
    assert "s3cret" not in said
    assert api.sent[-1][2]["config"]["secret"] == "s3cret"
    assert api.sent[-1][2]["events"] == ["push"]
    with pytest.raises(sl.SettingsListError, match="starts with https://"):
        sl.add_webhook(api, "o/r", "ftp://x", events=["push"])
    with pytest.raises(sl.SettingsListError, match="at least one event"):
        sl.add_webhook(api, "o/r", "https://x.org/h", events=[])


def test_ping_deliveries_redeliver_change_and_delete() -> None:
    api = FakeApi()
    assert "Sent a ping" in sl.ping_webhook(api, "o/r", "9")
    found = sl.fetch_deliveries(api, "o/r", "9")
    assert [d.label for d in found] == [
        "push at 2026-11-18 09:30: succeeded (200)",
        "pull_request opened at 2026-11-18 09:00: failed (502), a redelivery",
    ]
    assert "deliver the pull_request opened event again" in sl.redeliver(api, "o/r", "9", found[1])
    assert api.sent[-1][1] == "/repos/o/r/hooks/9/deliveries/4/attempts"
    said = sl.change_webhook(api, "o/r", "9", secret="new")
    assert said == "Changed the webhook's secret." and "new" not in said
    with pytest.raises(sl.SettingsListError, match="Nothing to change"):
        sl.change_webhook(api, "o/r", "9")
    assert sl.delete_webhook(api, "o/r", "9").startswith("Deleted the webhook")


def test_deploy_keys_and_autolinks_are_checked_before_sending() -> None:
    api = FakeApi()
    said = sl.add_deploy_key(api, "o/r", "CI", PUB, read_only=False)
    assert said == f"Added deploy key CI, read and write, {PRINT}."
    with pytest.raises(sl.SettingsListError, match="never a private key"):
        sl.add_deploy_key(api, "o/r", "CI", "-----BEGIN OPENSSH PRIVATE KEY-----")
    assert sl.add_autolink(
        api, "o/r", "T-", "https://t.example.org/<num>", alphanumeric=True
    ).startswith("Added an autolink: T-")
    with pytest.raises(sl.SettingsListError, match="<num>"):
        sl.add_autolink(api, "o/r", "T-", "https://t.example.org/", alphanumeric=True)
    with pytest.raises(sl.SettingsListError, match="administration"):
        sl.fetch_webhooks(FakeApi({"GET": 404}), "o/r")
    assert sl.SettingsListError.code == "QUILL-GITHUB-SETTINGS-LISTS"


def test_the_three_nodes_reach_their_loader(monkeypatch: Any) -> None:
    from quill.core.github.explore_extra_views import fetch_extra_view

    for name in ("fetch_webhooks", "fetch_deploy_keys", "fetch_autolinks"):
        monkeypatch.setattr(sl, name, lambda _api, repo, name=name: [name])
    provider = SimpleNamespace(token="t", is_authenticated=True)
    ask = {"repo": "o/r", "query": "", "limit": 5, "warnings": []}
    assert fetch_extra_view(provider, "webhooks", **ask) == ["fetch_webhooks"]
    assert fetch_extra_view(provider, "deploy_keys", **ask) == ["fetch_deploy_keys"]
    assert fetch_extra_view(provider, "autolinks", **ask) == ["fetch_autolinks"]
