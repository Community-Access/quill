"""Sign in with GitHub for the Workbench: the device flow over a fake GitHub.

No network: every exchange goes through a scripted poster, and the clock and
the wait are the test's own. The cases are the ones GitHub actually sends --
success, ``slow_down``, ``expired_token``, ``access_denied`` -- plus Cancel and
a network failure, each of which must end in one sentence and no token.
"""

from __future__ import annotations

import threading
from typing import Any
from urllib.request import Request

import pytest

from quill.core.ai import copilot_auth
from quill.core.github import oauth_sign_in
from quill.core.github.oauth_sign_in import (
    WORKBENCH_SCOPE,
    WORKBENCH_SCOPES,
    GitHubSignInCancelled,
    GitHubSignInFailed,
    GitHubSignInUnavailable,
    WorkbenchSignIn,
    workbench_device_flow_config,
)

_CODE_REPLY = {
    "device_code": "dev-123",
    "user_code": "WDJB-MJHT",
    "verification_uri": "https://github.com/login/device",
    "interval": 5,
    "expires_in": 900,
}


class _GitHub:
    """A scripted GitHub: the device-code reply, then one token reply per poll."""

    def __init__(self, *polls: dict[str, Any]) -> None:
        self.polls = list(polls)
        self.posts: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, form: dict[str, str]) -> dict[str, Any]:
        self.posts.append((url, dict(form)))
        if url == copilot_auth.GITHUB_DEVICE_AUTH_URL:
            return dict(_CODE_REPLY)
        if not self.polls:
            return {"error": "authorization_pending"}
        return self.polls.pop(0)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def _no_client_id_override(monkeypatch) -> None:
    monkeypatch.delenv(copilot_auth.CLIENT_ID_OVERRIDE_ENV, raising=False)


def _sign_in(github: _GitHub, clock: _Clock, sleeps: list[float]) -> WorkbenchSignIn:
    flow = WorkbenchSignIn("QUILL", poster=github, clock=clock)

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock.now += seconds

    flow._sleep = sleep  # type: ignore[method-assign]
    return flow


def test_the_config_uses_copilots_client_id_table_and_the_workbench_scopes() -> None:
    for app in ("QUILL", "QUILL Lite"):
        config = workbench_device_flow_config(app)
        assert config.client_id == copilot_auth.CLIENT_IDS[app]
        assert config.device_authorization_url == "https://github.com/login/device/code"
        assert config.token_url == "https://github.com/login/oauth/access_token"
        assert config.scope == WORKBENCH_SCOPE
    # Copilot keeps its own, smaller scope (and its own token).
    assert copilot_auth.github_device_flow_config("QUILL").scope == "read:user"


def test_every_scope_says_which_feature_needs_it_and_delete_repo_is_not_asked() -> None:
    names = [name for name, _reason in WORKBENCH_SCOPES]
    assert WORKBENCH_SCOPE.split() == names
    assert len(set(names)) == len(names)
    assert all(reason.strip() for _name, reason in WORKBENCH_SCOPES)
    assert {"repo", "workflow", "gist", "read:org", "project", "security_events"} <= set(names)
    assert "delete_repo" not in names


def test_an_app_without_a_registration_is_unavailable_before_any_network(monkeypatch) -> None:
    github = _GitHub()
    flow = WorkbenchSignIn("QUILL Nowhere", poster=github)
    assert not flow.available()
    with pytest.raises(GitHubSignInUnavailable) as raised:
        flow.request_code()
    assert "Add Token" in raised.value.args[0]
    assert github.posts == []


def test_success_returns_the_token_and_sends_the_scopes() -> None:
    github = _GitHub({"error": "authorization_pending"}, {"access_token": "gho_new"})
    sleeps: list[float] = []
    flow = _sign_in(github, _Clock(), sleeps)

    grant = flow.request_code()
    assert grant.user_code == "WDJB-MJHT"
    assert flow.wait(grant) == "gho_new"

    device_url, device_form = github.posts[0]
    assert device_form == {"client_id": copilot_auth.CLIENT_IDS["QUILL"], "scope": WORKBENCH_SCOPE}
    assert all(url == copilot_auth.GITHUB_TOKEN_URL for url, _form in github.posts[1:])
    assert sleeps == [5.0]  # GitHub's interval, between the two polls


def test_slow_down_adds_five_seconds_to_the_interval() -> None:
    github = _GitHub({"error": "slow_down"}, {"access_token": "gho_new"})
    sleeps: list[float] = []
    flow = _sign_in(github, _Clock(), sleeps)

    assert flow.wait(flow.request_code()) == "gho_new"
    assert sleeps == [10.0]


@pytest.mark.parametrize(
    ("reply", "words"),
    [
        ({"error": "expired_token"}, "The code expired before it was used."),
        ({"error": "access_denied"}, "The sign-in was declined on GitHub's page."),
        ({"error": "device_flow_disabled", "error_description": "Off."}, "Off"),
    ],
)
def test_github_saying_no_is_one_sentence_and_no_token(reply, words) -> None:
    flow = _sign_in(_GitHub(reply), _Clock(), [])

    with pytest.raises(GitHubSignInFailed) as raised:
        flow.wait(flow.request_code())

    assert words in raised.value.args[0]


def test_the_code_running_out_while_still_pending_is_expiry() -> None:
    github = _GitHub(*([{"error": "authorization_pending"}] * 400))
    flow = _sign_in(github, _Clock(), [])

    with pytest.raises(GitHubSignInFailed) as raised:
        flow.wait(flow.request_code())

    assert "expired" in raised.value.args[0]


def test_cancel_stops_the_wait_at_once() -> None:
    flow = WorkbenchSignIn("QUILL", poster=_GitHub(*([{"error": "authorization_pending"}] * 3)))
    grant = flow.request_code()
    timer = threading.Timer(0.05, flow.cancel)
    timer.start()
    try:
        with pytest.raises(GitHubSignInCancelled):
            flow.wait(grant)  # would otherwise sleep five seconds between polls
    finally:
        timer.cancel()


def test_a_network_failure_is_one_plain_sentence() -> None:
    def broken(_url: str, _form: dict[str, str]) -> dict[str, Any]:
        raise OSError("connection reset")

    flow = WorkbenchSignIn("QUILL", poster=broken)
    with pytest.raises(GitHubSignInFailed) as raised:
        flow.request_code()
    assert raised.value.args[0] == (
        "GitHub did not give a sign-in code. Check your connection and try again."
    )


def test_the_opener_refuses_any_address_but_githubs_two() -> None:
    request = Request("https://example.com/login/oauth/access_token", data=b"x", method="POST")
    with pytest.raises(GitHubSignInFailed):
        oauth_sign_in._github_opener(request)


def test_the_spoken_code_is_one_character_at_a_time() -> None:
    assert oauth_sign_in.spoken_code("WDJB-MJHT") == "W D J B dash M J H T"
    assert oauth_sign_in.spoken_code("AB12") == "A B 1 2"
