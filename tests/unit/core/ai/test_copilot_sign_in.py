"""Signing an app in to My GitHub Copilot with GitHub's device code (codex.md 10A.12).

A fake poster stands in for GitHub; the secure store is replaced, so nothing
here touches the network or Windows' credential store.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

from quill.core.ai import copilot_auth, copilot_state
from quill.core.ai.copilot_sign_in import (
    CopilotSignIn,
    CopilotSignInFailed,
    SignInCancelled,
    spoken_code,
)

_CODE = {
    "device_code": "dev-1",
    "user_code": "ABCD-1234",
    "verification_uri": "https://github.com/login/device",
    "interval": 1,
    "expires_in": 900,
}


class _GitHub:
    """Answers the device-code request, then each poll from a script."""

    def __init__(self, polls: list[dict[str, Any]]) -> None:
        self.polls = list(polls)
        self.calls: list[str] = []

    def __call__(self, url: str, form: dict[str, str]) -> dict[str, Any]:
        self.calls.append(url)
        if url == copilot_auth.GITHUB_DEVICE_AUTH_URL:
            return dict(_CODE)
        return self.polls.pop(0)


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, str]:
    saved: dict[str, str] = {}
    monkeypatch.setattr(copilot_auth, "client_id", lambda agent="QUILL": "Iv1.test")
    monkeypatch.setattr(
        copilot_auth,
        "persist_token",
        lambda token, agent="QUILL": saved.__setitem__(agent, token) or True,
    )
    return saved


def _flow(poster: _GitHub, tmp_path: Path, agent: str = "QUILL Lite") -> CopilotSignIn:
    flow = CopilotSignIn(agent, data_dir=tmp_path, poster=poster)
    flow._sleep = lambda _s: None  # type: ignore[method-assign]  # no real waiting
    return flow


def test_the_code_is_spaced_for_the_reader_as_the_free_ais_code_is() -> None:
    from quill.ui.hosted_ai_service import SignInCode

    assert spoken_code("ABCD-1234") == SignInCode("ABCD-1234", "").spoken
    assert spoken_code("AB12").split() == ["A", "B", "1", "2"]


def test_an_approved_code_keeps_this_apps_token_and_clears_githubs_marks(
    store: dict[str, str], tmp_path: Path
) -> None:
    copilot_state.mark_ended_by_github("QUILL Lite", data_dir=tmp_path)
    github = _GitHub([{"error": "authorization_pending"}, {"access_token": "gho_x"}])
    flow = _flow(github, tmp_path)

    grant = flow.request_code()
    flow.wait(grant)

    assert grant.user_code == "ABCD-1234"
    assert store == {"QUILL Lite": "gho_x"}  # its own entry, under its own name
    assert copilot_state.load_marks("QUILL Lite", data_dir=tmp_path).ended_by_github is False


@pytest.mark.parametrize(
    ("poll", "words"),
    [
        ({"error": "access_denied"}, "refused on GitHub's page"),
        ({"error": "expired_token"}, "expired"),
    ],
)
def test_a_refused_or_expired_code_says_so_and_saves_nothing(
    store: dict[str, str], tmp_path: Path, poll: dict[str, Any], words: str
) -> None:
    flow = _flow(_GitHub([poll]), tmp_path)
    with pytest.raises(CopilotSignInFailed) as raised:
        flow.wait(flow.request_code())
    assert words in str(raised.value.args[0])
    assert store == {}


def test_cancel_stops_the_wait_at_once(store: dict[str, str], tmp_path: Path) -> None:
    github = _GitHub([{"error": "authorization_pending"}] * 50)
    flow = CopilotSignIn("QUILL", data_dir=tmp_path, poster=github)
    grant = flow.request_code()
    outcome: dict[str, Any] = {}

    def wait() -> None:
        try:
            flow.wait(grant)
        except SignInCancelled as error:
            outcome["cancelled"] = error

    worker = threading.Thread(target=wait)
    worker.start()
    flow.cancel()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert "cancelled" in outcome
    assert store == {}


def test_no_client_id_means_no_sign_in_and_no_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(copilot_auth, "client_id", lambda agent="QUILL": "")
    github = _GitHub([])
    flow = CopilotSignIn("QUILL", data_dir=tmp_path, poster=github)

    assert flow.available() is False
    with pytest.raises(copilot_auth.CopilotSignInUnavailable):
        flow.request_code()
    assert github.calls == []
