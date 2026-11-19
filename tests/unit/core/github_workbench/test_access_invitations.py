"""Pending invitations on an Access page: cancel, change role, invite (GH-R-063)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github import access_invitations as ai
from quill.core.github.permissions import WriteTier
from quill.ui.github_workbench_invitations import GitHubWorkbenchInvitationsMixin

_REPO = {"repo": "o/web"}
_ORG = {"org": "o"}
_REPO_LIST = [
    {"id": 7, "invitee": {"login": "Kelly"}, "permissions": "write"},
    {"id": 8, "invitee": None, "email": "sam@example.com", "permissions": "read"},
]
_KELLY = "kelly, invited, write, pending"
_ANN = "ann@example.com, invited, , pending"
_ORG_LIST = [{"id": 31, "login": None, "email": "ann@example.com", "role": "direct_member"}]


def test_the_invitation_is_found_by_login_or_email_whatever_the_case() -> None:
    assert ai.find_invitation(_REPO_LIST, "@kelly") == 7
    assert ai.find_invitation(_REPO_LIST, "SAM@example.com") == 8
    assert ai.find_invitation(_ORG_LIST, "ann@example.com") == 31
    assert ai.find_invitation(_REPO_LIST, "nobody") is None


def test_cancel_is_one_delete_previewed_in_words() -> None:
    change = ai.plan_cancel_invitation("repository", _REPO, 7, "kelly")
    assert (change.method, change.path, change.body) == (
        "DELETE",
        "/repos/o/web/invitations/7",
        None,
    )
    assert change.words == "Cancel the invitation to kelly for o/web. They can be invited again."
    assert change.tier == WriteTier.ACCESS
    org = ai.plan_cancel_invitation("organization", _ORG, 31, "ann@example.com")
    assert org.path == "/orgs/o/invitations/31"


def test_a_repository_invitation_role_is_patched_with_githubs_own_words() -> None:
    change = ai.plan_invitation_role(_REPO, 7, "kelly", "write")
    assert (change.method, change.path, change.body) == (
        "PATCH",
        "/repos/o/web/invitations/7",
        {"permissions": "write"},
    )


def test_only_repositories_and_organizations_list_invitations() -> None:
    assert ai.invitations_path("team", {"org": "o", "team": "docs"}) == ""


class _Api:
    def __init__(self, found: list[dict[str, Any]]) -> None:
        self.found = found
        self.calls: list[tuple[str, str]] = []

    def rest(self, method: str, path: str, **_kw: Any) -> Any:
        self.calls.append((method, path))
        return SimpleNamespace(data=self.found)


class _Provider(GitHubWorkbenchInvitationsMixin):
    def __init__(self, found: list[dict[str, Any]], answers: list[Any]) -> None:
        self.api = _Api(found)
        self.answers = answers
        self.said: list[str] = []
        self.sent: list[Any] = []

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _ask_text(self, *_a: Any) -> str:
        return str(self.answers.pop(0))

    def _choose(self, *_a: Any) -> int:
        return int(self.answers.pop(0))

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())

    def _run_changes(self, changes: list[Any], _title: str) -> None:
        self.sent.extend(changes)

    def github_api(self) -> _Api:
        return self.api


def test_remove_on_an_invitation_row_cancels_it() -> None:
    provider = _Provider(_REPO_LIST, [])
    provider.act_on_invitation(
        "repository", _REPO, "remove", "kelly, invited, write, pending", "o/web"
    )
    assert provider.api.calls == [("GET", "/repos/o/web/invitations")]
    sent = [(c.method, c.path) for c in provider.sent]
    assert sent == [("DELETE", "/repos/o/web/invitations/7")]


def test_change_on_a_repository_invitation_offers_another_role() -> None:
    provider = _Provider(_REPO_LIST, [0])  # the first role: read
    provider.act_on_invitation(
        "repository", _REPO, "change", "kelly, invited, write, pending", "o/web"
    )
    assert [(c.method, c.body) for c in provider.sent] == [("PATCH", {"permissions": "read"})]


def test_an_organization_invitation_role_cannot_change_in_place() -> None:
    provider = _Provider(_ORG_LIST, [])
    provider.act_on_invitation(
        "organization", _ORG, "change", "ann@example.com, invited, , pending", "o"
    )
    assert provider.sent == [] and "Remove it and invite them again" in provider.said[0]


def test_an_invitation_answered_meanwhile_is_said_not_sent() -> None:
    provider = _Provider([], [])
    provider.act_on_invitation(
        "repository", _REPO, "remove", "kelly, invited, write, pending", "o/web"
    )
    assert provider.sent == []
    assert provider.said == ["There is no pending invitation for kelly any more."]


def test_add_on_the_invitations_list_invites_with_a_role() -> None:
    provider = _Provider([], ["kelly", 2])  # login, then the third role: write
    provider.act_on_invitation("repository", _REPO, "add", "", "o/web")
    assert [(c.method, c.path, c.body) for c in provider.sent] == [
        ("PUT", "/repos/o/web/collaborators/kelly", {"permission": "push"})
    ]
