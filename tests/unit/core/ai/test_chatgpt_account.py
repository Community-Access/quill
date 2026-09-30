"""Sign in with ChatGPT: the flow, what is kept, and what a refresh does."""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from quill.core.ai import chatgpt_account as account_mod
from quill.core.ai.chatgpt_account import (
    API_BASE,
    AUTH_BASE,
    PLAN_SCOPE,
    ChatGptAccount,
    ChatGptState,
    decode_claims,
    load_state,
    save_state,
    slug_for,
)
from quill.core.ai.chatgpt_errors import ChatGptSignedOutError, ChatGptSignInError
from quill.core.secrets import SecretsManager


class _MemoryBackend:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def load(self, name: str) -> str:
        return self.store.get(name, "")

    def save(self, name: str, value: str) -> None:
        self.store[name] = value

    def delete(self, name: str) -> bool:
        return self.store.pop(name, None) is not None


def _jwt(claims: dict[str, Any]) -> str:
    def seg(data: dict[str, Any]) -> str:
        raw = json.dumps(data).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    return f"{seg({'alg': 'RS256'})}.{seg(claims)}.signature"


class _FakeListener:
    """Stands in for the loopback server: the fake browser fills in the answer."""

    answer: dict[str, str] = {}
    closed = False

    def __init__(self, host: str = "127.0.0.1") -> None:
        type(self).closed = False

    @property
    def redirect_uri(self) -> str:
        return "http://127.0.0.1:4321/auth/callback"

    def wait(self, timeout: float) -> dict[str, str]:
        return dict(type(self).answer)

    def cancel(self) -> None:
        type(self).answer = {}

    def close(self) -> None:
        type(self).closed = True


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """A fake OpenAI: a browser that answers the redirect, and a token endpoint."""
    monkeypatch.setattr(account_mod, "LoopbackListener", _FakeListener)
    backend = _MemoryBackend()
    posted: list[tuple[str, dict[str, str]]] = []
    opened: list[str] = []
    nonce_seen: dict[str, str] = {}
    now = {"t": 1_000_000.0}

    def browser(url: str) -> bool:
        opened.append(url)
        query = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
        nonce_seen["nonce"] = query["nonce"]
        _FakeListener.answer = {
            "code": "the-code",
            "state": query["state"],
            "client_id": "client-issued",
        }
        return True

    def poster(url: str, fields: dict[str, str]) -> dict[str, Any]:
        posted.append((url, dict(fields)))
        if fields.get("grant_type") == "authorization_code":
            return {
                "access_token": "access-1",
                "refresh_token": "refresh-1",
                "expires_in": 3600,
                "scope": " ".join(("openid", PLAN_SCOPE)),
                "id_token": _jwt({
                    "iss": AUTH_BASE,
                    "aud": fields["client_id"],
                    "nonce": nonce_seen["nonce"],
                    "sub": "user-123",
                    "email": "jeff@example.com",
                    "exp": now["t"] + 600,
                }),
            }
        if fields.get("grant_type") == "refresh_token":
            return {"access_token": "access-2", "refresh_token": "refresh-2", "expires_in": 3600}
        return {}

    account = ChatGptAccount(
        tmp_path,
        agent_name="QUILL Lite",
        secrets_manager=SecretsManager(backend=backend),
        poster=poster,
        browser=browser,
        now=lambda: now["t"],
    )
    return account, backend, posted, opened, now


def test_slugs_name_the_agent_in_the_secrets_store() -> None:
    assert slug_for("QUILL Lite") == "quill-lite"
    assert slug_for("QUILL Radio") == "quill-radio"
    assert slug_for("QUILL") == "quill"
    assert slug_for("  ") == "quill"


def test_state_round_trips_and_is_empty_when_missing(tmp_path) -> None:
    assert load_state(tmp_path) == ChatGptState()
    state = ChatGptState(host_id="urn:uuid:x", client_id="c", subject="s", model="gpt-6")
    save_state(tmp_path, state)
    assert load_state(tmp_path) == state
    assert state.signed_in
    assert not ChatGptState(client_id="c").signed_in


def test_claims_decode_from_the_payload_segment_only() -> None:
    assert decode_claims(_jwt({"sub": "u"})) == {"sub": "u"}
    assert decode_claims("not a token") == {}
    assert decode_claims("a.b") == {}


def test_signing_in_registers_the_app_and_keeps_only_the_refresh_token(harness) -> None:
    account, backend, posted, opened, _now = harness

    state = account.sign_in()

    assert state.signed_in
    assert state.client_id == "client-issued"
    assert state.email == "jeff@example.com"
    assert state.subject == "user-123"
    assert PLAN_SCOPE in state.scope
    assert account.signed_in
    # The first sign-in asks OpenAI to register this app under its own name.
    query = {k: v[0] for k, v in parse_qs(urlparse(opened[0]).query).items()}
    assert query["client_id"] == "dynamic_agent_client"
    assert query["agent_name_hint"] == "QUILL Lite"
    assert query["ext_agent_host_id"].startswith("urn:uuid:")
    assert query["resource"] == API_BASE
    assert query["code_challenge_method"] == "S256"
    # Only the refresh token reaches the OS store; the access token stays in memory.
    assert list(backend.store.values()) == ["refresh-1"] or "refresh-1" in backend.store.values()
    assert all("access-1" not in value for value in backend.store.values())
    assert posted[0][0].endswith("/oauth/token")
    assert posted[0][1]["resource"] == API_BASE
    assert account.access_token() == "access-1"
    assert _FakeListener.closed


def test_a_second_sign_in_reuses_the_issued_client_id(harness) -> None:
    account, _backend, _posted, opened, _now = harness
    account.sign_in()
    account.sign_in()
    query = {k: v[0] for k, v in parse_qs(urlparse(opened[1]).query).items()}
    assert query["client_id"] == "client-issued"
    assert "agent_name_hint" not in query
    assert query["login_hint"] == "jeff@example.com"


def test_a_refused_consent_is_a_sentence_and_changes_nothing(harness, monkeypatch) -> None:
    account, backend, _posted, _opened, _now = harness

    def refusing(url: str) -> bool:
        query = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
        _FakeListener.answer = {
            "state": query["state"],
            "error": "access_denied",
            "error_description": "You said no.",
        }
        return True

    account._browser = refusing
    with pytest.raises(ChatGptSignInError, match="You said no"):
        account.sign_in()
    assert not account.signed_in
    assert backend.store == {}


def test_a_browser_that_never_comes_back_is_a_sentence(harness) -> None:
    account, _backend, _posted, _opened, _now = harness

    def silent(url: str) -> bool:
        _FakeListener.answer = {}
        return False

    account._browser = silent
    with pytest.raises(ChatGptSignInError, match="did not come back"):
        account.sign_in()


def test_the_plan_scope_must_be_granted(harness) -> None:
    account, _backend, _posted, _opened, now = harness
    real = account._poster

    def without_plan(url: str, fields: dict[str, str]) -> dict[str, Any]:
        answer = real(url, fields)
        answer["scope"] = "openid"
        return answer

    account._poster = without_plan
    with pytest.raises(ChatGptSignInError, match="use your plan"):
        account.sign_in()
    assert not account.signed_in


@pytest.mark.parametrize(
    ("claim", "value", "said"),
    [
        ("iss", "https://evil.example", "did not come from OpenAI"),
        ("aud", "someone-else", "different app"),
        ("nonce", "stale", "did not match"),
        ("exp", 1.0, "already expired"),
        ("sub", "", "named no account"),
    ],
)
def test_the_id_token_is_checked(harness, claim: str, value: Any, said: str) -> None:
    account, _backend, _posted, _opened, now = harness
    real = account._poster

    def tampered(url: str, fields: dict[str, str]) -> dict[str, Any]:
        answer = real(url, fields)
        claims = decode_claims(answer["id_token"])
        claims[claim] = value
        answer["id_token"] = _jwt(claims)
        return answer

    account._poster = tampered
    with pytest.raises(ChatGptSignInError, match=said):
        account.sign_in()


def test_a_store_that_will_not_keep_the_token_keeps_nothing(harness) -> None:
    account, backend, _posted, _opened, _now = harness

    class Refusing(_MemoryBackend):
        def save(self, name: str, value: str) -> None:
            pass

    account._secrets = SecretsManager(backend=Refusing())
    with pytest.raises(ChatGptSignInError, match="could not be stored"):
        account.sign_in()
    assert not account.state.signed_in


def test_the_access_token_is_refreshed_once_it_expires_and_the_new_refresh_is_kept(
    harness,
) -> None:
    account, backend, posted, _opened, now = harness
    account.sign_in()
    assert account.access_token() == "access-1"
    now["t"] += 3600
    assert account.access_token() == "access-2"
    refreshes = [fields for _url, fields in posted if fields.get("grant_type") == "refresh_token"]
    assert refreshes == [
        {
            "grant_type": "refresh_token",
            "client_id": "client-issued",
            "refresh_token": "refresh-1",
            "resource": API_BASE,
        }
    ]
    assert "refresh-2" in backend.store.values()
    # Not refreshed again while the new one is fresh.
    assert account.access_token() == "access-2"
    assert len([f for _u, f in posted if f.get("grant_type") == "refresh_token"]) == 1


def test_a_fresh_launch_refreshes_from_the_stored_token(harness, tmp_path) -> None:
    account, backend, _posted, _opened, now = harness
    account.sign_in()
    again = ChatGptAccount(
        tmp_path,
        agent_name="QUILL Lite",
        secrets_manager=account._secrets,
        poster=account._poster,
        browser=account._browser,
        now=lambda: now["t"],
    )
    assert again.signed_in
    assert again.access_token() == "access-2"


def test_a_rejected_refresh_forgets_the_sign_in_and_says_so(harness) -> None:
    account, backend, _posted, _opened, now = harness
    account.sign_in()
    account._poster = lambda _url, _fields: {"error": "invalid_grant"}
    now["t"] += 3600
    with pytest.raises(ChatGptSignedOutError):
        account.access_token()
    assert not account.signed_in
    assert backend.store == {}
    # The registration is kept so the next sign-in does not make a second "QUILL Lite".
    assert account.state.client_id == "client-issued"


def test_forget_is_local_only_and_keeps_the_preferences(harness) -> None:
    account, backend, posted, _opened, _now = harness
    account.sign_in()
    account.set_model("gpt-6-luna")
    account.set_web_search(True)
    before = len(posted)

    account.forget()

    assert not account.signed_in
    assert backend.store == {}
    assert len(posted) == before
    assert account.model == "gpt-6-luna"
    assert account.web_search is True
    with pytest.raises(ChatGptSignedOutError):
        account.access_token()


def test_sign_out_revokes_when_openai_names_an_endpoint(harness) -> None:
    account, backend, posted, _opened, _now = harness
    account.sign_in()

    def opener(request):  # noqa: ANN001, ANN202 - the http module's opener shape
        body = json.dumps({"revocation_endpoint": f"{AUTH_BASE}/oauth/revoke"}).encode()
        return 200, body

    assert account.sign_out(opener=opener) is True
    assert posted[-1][0] == f"{AUTH_BASE}/oauth/revoke"
    assert posted[-1][1]["token"] == "refresh-1"
    assert posted[-1][1]["token_type_hint"] == "refresh_token"
    assert not account.signed_in
    assert backend.store == {}


def test_sign_out_still_signs_out_when_openai_cannot_be_reached(harness) -> None:
    account, backend, _posted, _opened, _now = harness
    account.sign_in()

    def failing(request):  # noqa: ANN001, ANN202
        raise OSError("no network")

    assert account.sign_out(opener=failing) is False
    assert not account.signed_in
    assert backend.store == {}


def test_signed_out_when_nothing_was_ever_stored(tmp_path) -> None:
    account = ChatGptAccount(
        tmp_path, agent_name="QUILL Radio", secrets_manager=SecretsManager(backend=_MemoryBackend())
    )
    assert not account.signed_in
    assert account.slug == "quill-radio"
    with pytest.raises(ChatGptSignedOutError):
        account.access_token()


def test_the_loopback_listener_answers_only_the_callback_path() -> None:
    import threading
    import urllib.request

    listener = account_mod.LoopbackListener()
    try:
        uri = listener.redirect_uri
        assert uri.startswith("http://127.0.0.1:") and uri.endswith("/auth/callback")
        base = uri.rsplit("/auth/callback", 1)[0]
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(f"{base}/favicon.ico", timeout=5)  # noqa: S310 - loopback

        def come_back() -> None:
            urllib.request.urlopen(f"{uri}?code=abc&state=xyz&client_id=c1", timeout=5)  # noqa: S310

        threading.Thread(target=come_back, daemon=True).start()
        assert listener.wait(5) == {"code": "abc", "state": "xyz", "client_id": "c1"}
    finally:
        listener.close()


def test_cancelling_a_waiting_sign_in_ends_the_wait_with_nothing() -> None:
    import threading

    listener = account_mod.LoopbackListener()
    try:
        threading.Timer(0.1, listener.cancel).start()
        assert listener.wait(5) == {}
    finally:
        listener.close()
