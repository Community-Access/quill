"""Turning a workflow on or off, and invitations to repositories (GitHub PRD 14.1)."""

from __future__ import annotations

from typing import Any

from quill.core.github import repo_invitations as inv
from quill.core.github import workflow_state as ws
from quill.core.github.rest_transport import RestResponse


class FakeApi:
    def __init__(self, data: Any = None) -> None:
        self.data = data
        self.sent: list[tuple[str, str]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path))
        return RestResponse(200, {}, self.data)

    def graphql(self, query: str, variables: Any) -> Any:
        raise AssertionError


def test_state_in_words() -> None:
    assert ws.state_words("active") == "on"
    assert "60 days" in ws.state_words("disabled_inactivity")
    assert ws.state_words("something_new") == "something new"
    assert ws.is_enabled("active") and not ws.is_enabled("disabled_manually")


def test_turning_off_and_on_sends_the_documented_requests() -> None:
    api = FakeApi()
    assert ws.set_enabled(api, "o/r", 12, "CI", False).startswith("Turned off CI.")
    assert ws.set_enabled(api, "o/r", 12, "CI", True).startswith("Turned on CI.")
    assert api.sent == [
        ("PUT", "/repos/o/r/actions/workflows/12/disable"),
        ("PUT", "/repos/o/r/actions/workflows/12/enable"),
    ]


INVITE = {
    "id": 77,
    "repository": {"full_name": "octo/app"},
    "inviter": {"login": "ann"},
    "permissions": "write",
    "created_at": "2026-11-17T10:00:00Z",
    "html_url": "https://github.com/octo/app/invitations",
    "expired": False,
}


def test_an_invitation_reads_who_what_and_when() -> None:
    row = inv.invitation_row(INVITE)
    assert row.label == "octo/app: ann invited you, write access"
    assert row.detail.startswith(
        "Invitation to octo/app, from ann, for write access, on 2026-11-17"
    )
    assert row.kind == "invitation" and row.key == "77" and row.repo == "octo/app"
    old = inv.invitation_row({**INVITE, "expired": True})
    assert old.label.endswith(", expired") and "ask for a new one" in old.detail


def test_invitations_are_listed_accepted_and_declined() -> None:
    api = FakeApi([INVITE])
    assert [r.key for r in inv.fetch_invitations(api)] == ["77"]
    assert inv.accept(api, "77", "octo/app") == "Accepted. You can now work in octo/app."
    assert inv.decline(api, "77", "octo/app") == "Declined the invitation to octo/app."
    assert api.sent[-2:] == [
        ("PATCH", "/user/repository_invitations/77"),
        ("DELETE", "/user/repository_invitations/77"),
    ]
