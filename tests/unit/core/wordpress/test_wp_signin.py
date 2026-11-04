"""Sign-in flows for WordPress and WordPress.com (quill/core/wordpress/signin.py)."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import threading
import urllib.error
import urllib.request
import uuid
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from quill.core.error_codes import CodedError
from quill.core.wordpress import signin
from quill.core.wordpress.signin import (
    AppPasswordResult,
    AuthorizationDeniedError,
    ListenerError,
    LoopbackListener,
    MalformedRedirectError,
    PkcePair,
    Rejected,
    Secret,
    StateMismatchError,
    TokenResponseError,
    WpcomTokens,
    authorize_url_from_index,
    build_authorize_application_url,
    build_wpcom_authorize_url,
    exchange_code,
    looks_like_application_password,
    new_state,
    parse_authorize_application_redirect,
    parse_token_response,
    parse_wpcom_redirect,
    refresh_request,
    refresh_tokens,
    supports_loopback_success_url,
    token_request,
)

APP_ID = "1c0c2a52-6d6e-4a8e-9a34-7f2d3a8c1b11"
PASSWORD = "abcd EFGH 1234 ijkl MNOP 5678"


def _q(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query, keep_blank_values=True)


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


def test_error_classes_are_coded_and_unique() -> None:
    classes = [
        signin.SignInError,
        StateMismatchError,
        MalformedRedirectError,
        AuthorizationDeniedError,
        TokenResponseError,
        ListenerError,
    ]
    codes = [cls.code for cls in classes]
    assert len(set(codes)) == len(codes)
    for cls in classes:
        assert issubclass(cls, CodedError)
        assert cls.code.startswith("QUILL-WORDPRESS-SIGNIN-")


# --------------------------------------------------------------------------
# Secret
# --------------------------------------------------------------------------


def test_secret_repr_and_str_are_redacted() -> None:
    secret = Secret("hunter2-very-secret")
    assert "hunter2" not in repr(secret)
    assert "hunter2" not in str(secret)
    assert f"{secret}" == "Secret('***')"
    assert secret.reveal() == "hunter2-very-secret"


def test_secret_equality_and_truthiness() -> None:
    assert Secret("a") == Secret("a")
    assert Secret("a") != Secret("b")
    assert Secret("a") != "a"
    assert not Secret("")
    assert hash(Secret("x")) == hash(Secret("x"))


# --------------------------------------------------------------------------
# REST index and authorize URL
# --------------------------------------------------------------------------

INDEX = {
    "name": "Community Radio",
    "authentication": {
        "application-passwords": {
            "endpoints": {"authorization": "https://example.org/wp-admin/authorize-application.php"}
        }
    },
}


def test_authorize_url_from_index_dict_and_json() -> None:
    expected = "https://example.org/wp-admin/authorize-application.php"
    assert authorize_url_from_index(INDEX) == expected
    assert authorize_url_from_index(json.dumps(INDEX)) == expected
    assert authorize_url_from_index(json.dumps(INDEX).encode()) == expected


@pytest.mark.parametrize(
    "index",
    [
        {},
        {"authentication": []},
        {"authentication": {}},
        {"authentication": {"application-passwords": {"endpoints": {}}}},
        {"authentication": {"application-passwords": {"endpoints": {"authorization": ""}}}},
        {"authentication": {"application-passwords": {"endpoints": {"authorization": 5}}}},
        "not json",
        "[]",
    ],
)
def test_authorize_url_from_index_absent(index: Any) -> None:
    assert authorize_url_from_index(index) is None


def test_build_authorize_application_url_carries_state_on_both_urls() -> None:
    url = build_authorize_application_url(
        "https://example.org/wp-admin/authorize-application.php",
        app_name="QUILL",
        app_id=APP_ID,
        success_url="http://127.0.0.1:5000/wordpress-done",
        reject_url="http://127.0.0.1:5000/wordpress-done",
        state="st4te",
    )
    parts = urlsplit(url)
    assert parts.path == "/wp-admin/authorize-application.php"
    query = _q(url)
    assert query["app_name"] == ["QUILL"]
    assert query["app_id"] == [APP_ID]
    for key in ("success_url", "reject_url"):
        inner = query[key][0]
        assert inner.startswith("http://127.0.0.1:5000/wordpress-done?")
        assert _q(inner)["state"] == ["st4te"]


def test_build_authorize_application_url_tier_two_has_no_success_url() -> None:
    url = build_authorize_application_url(
        "https://example.org/wp-admin/authorize-application.php?lang=fr",
        app_name="QUILL",
        app_id=APP_ID,
        success_url=None,
        reject_url=None,
        state="s",
    )
    query = _q(url)
    assert "success_url" not in query
    assert "reject_url" not in query
    assert query["lang"] == ["fr"]


def test_build_authorize_application_url_validates_inputs() -> None:
    with pytest.raises(ValueError):
        build_authorize_application_url(
            "https://e/x", app_name="Q", app_id="nope", success_url=None, reject_url=None, state="s"
        )
    with pytest.raises(ValueError):
        build_authorize_application_url(
            "https://e/x", app_name="Q", app_id=APP_ID, success_url=None, reject_url=None, state=""
        )


def test_state_replaces_existing_state_on_success_url() -> None:
    url = build_authorize_application_url(
        "https://e/x",
        app_name="Q",
        app_id=APP_ID,
        success_url="http://127.0.0.1:1/d?state=old&keep=1",
        reject_url=None,
        state="new",
    )
    inner = _q(_q(url)["success_url"][0])
    assert inner["state"] == ["new"]
    assert inner["keep"] == ["1"]


def test_new_state_is_random_and_url_safe() -> None:
    a, b = new_state(), new_state()
    assert a != b
    assert len(a) >= 40
    assert all(c.isalnum() or c in "-_" for c in a)


# --------------------------------------------------------------------------
# Version gate
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("7.0", True),
        ("7.0.1", True),
        ("7.0-RC1", True),
        ("7.1", True),
        ("8", True),
        ("10.2.3", True),
        ("6.9.4", False),
        ("6.2", False),
        ("5.6", False),
        ("", False),
        ("unknown", False),
    ],
)
def test_supports_loopback_success_url(version: str, expected: bool) -> None:
    assert supports_loopback_success_url(version) is expected


def test_module_docstring_records_the_unconfirmed_release() -> None:
    doc = signin.__doc__ or ""
    assert "r62096" in doc
    assert "Not yet confirmed" in doc


# --------------------------------------------------------------------------
# Authorize Application handback
# --------------------------------------------------------------------------


def _success_url(state: str = "abc", **extra: str) -> str:
    from urllib.parse import urlencode

    params = {
        "state": state,
        "site_url": "https://example.org",
        "user_login": "jeff",
        "password": PASSWORD,
        **extra,
    }
    return "http://127.0.0.1:5000/wordpress-done?" + urlencode(params)


def test_parse_authorize_application_redirect_success() -> None:
    result = parse_authorize_application_redirect(_success_url(), "abc")
    assert isinstance(result, AppPasswordResult)
    assert result.site_url == "https://example.org"
    assert result.user_login == "jeff"
    assert result.password.reveal() == PASSWORD
    assert "abcd" not in repr(result)
    assert "jeff" in repr(result)


def test_parse_authorize_application_redirect_rejected() -> None:
    url = "http://127.0.0.1:5000/wordpress-done?state=abc&success=false"
    assert isinstance(parse_authorize_application_redirect(url, "abc"), Rejected)


@pytest.mark.parametrize(
    "url",
    [
        _success_url(state="wrong"),
        "http://127.0.0.1:5000/wordpress-done?site_url=x&user_login=y&password=z",
        "http://127.0.0.1:5000/wordpress-done?state=wrong&success=false",
    ],
)
def test_parse_authorize_application_redirect_state_mismatch(url: str) -> None:
    with pytest.raises(StateMismatchError) as info:
        parse_authorize_application_redirect(url, "abc")
    assert "abcd" not in str(info.value)


def test_parse_authorize_application_redirect_empty_expected_state_refuses() -> None:
    with pytest.raises(StateMismatchError):
        parse_authorize_application_redirect(_success_url(state=""), "")


def test_parse_authorize_application_redirect_missing_fields() -> None:
    url = "http://127.0.0.1:5000/wordpress-done?state=abc&user_login=jeff"
    with pytest.raises(MalformedRedirectError) as info:
        parse_authorize_application_redirect(url, "abc")
    assert "password" in str(info.value)
    assert info.value.code == "QUILL-WORDPRESS-SIGNIN-MALFORMED-REDIRECT"


# --------------------------------------------------------------------------
# Password shape
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "abcdEFGH1234ijklMNOP5678",
        "abcd EFGH 1234 ijkl MNOP 5678",
        "  abcd EFGH 1234 ijkl MNOP 5678\n",
        "AAAAAAAAAAAAAAAAAAAAAAAA",
    ],
)
def test_looks_like_application_password_accepts(text: str) -> None:
    assert looks_like_application_password(text)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "abcdEFGH1234ijklMNOP567",
        "abcdEFGH1234ijklMNOP56789",
        "abcd EFGH 1234 ijkl MNOP 567",
        "abcd  EFGH 1234 ijkl MNOP 5678",
        "abcd-EFGH-1234-ijkl-MNOP-5678",
        "abcdEFGH 1234ijklMNOP5678",
        "abcd EFGH 1234 ijkl MNOP 567!",
        "abcd\tEFGH 1234 ijkl MNOP 5678",
        "correct horse battery staple",
    ],
)
def test_looks_like_application_password_rejects(text: str) -> None:
    assert not looks_like_application_password(text)


def test_looks_like_application_password_non_string() -> None:
    assert not looks_like_application_password(None)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# PKCE
# --------------------------------------------------------------------------


def test_pkce_rfc7636_appendix_b_vector() -> None:
    pair = PkcePair.from_verifier("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")
    assert pair.challenge == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert pair.method == "S256"


def test_pkce_generate_shape() -> None:
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
    seen = set()
    for _ in range(20):
        pair = PkcePair.generate()
        assert 43 <= len(pair.verifier) <= 128
        assert set(pair.verifier) <= allowed
        digest = hashlib.sha256(pair.verifier.encode()).digest()
        assert pair.challenge == base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        assert "=" not in pair.challenge
        seen.add(pair.verifier)
    assert len(seen) == 20


def test_pkce_generate_minimum_length() -> None:
    assert len(PkcePair.generate(32).verifier) == 43


@pytest.mark.parametrize("verifier", ["short", "a" * 42, "a" * 129, "a" * 42 + "!", "a" * 42 + " "])
def test_pkce_rejects_bad_verifier(verifier: str) -> None:
    with pytest.raises(ValueError):
        PkcePair.from_verifier(verifier)


def test_pkce_repr_hides_verifier() -> None:
    pair = PkcePair.generate()
    assert pair.verifier not in repr(pair)
    assert pair.challenge in repr(pair)


# --------------------------------------------------------------------------
# WordPress.com authorize and redirect
# --------------------------------------------------------------------------


def test_build_wpcom_authorize_url() -> None:
    url = build_wpcom_authorize_url(
        "12345",
        "http://127.0.0.1:5000/wordpress-done",
        signin.WPCOM_SCOPES,
        "st",
        "chal",
    )
    assert url.startswith("https://public-api.wordpress.com/oauth2-1/authorize?")
    query = _q(url)
    assert query == {
        "response_type": ["code"],
        "client_id": ["12345"],
        "redirect_uri": ["http://127.0.0.1:5000/wordpress-done"],
        "scope": ["sites posts media taxonomy comments"],
        "state": ["st"],
        "code_challenge": ["chal"],
        "code_challenge_method": ["S256"],
    }


def test_build_wpcom_authorize_url_accepts_scope_string_and_needs_state() -> None:
    url = build_wpcom_authorize_url("1", "http://127.0.0.1/x", "  posts   media ", "s", "c")
    assert _q(url)["scope"] == ["posts media"]
    with pytest.raises(ValueError):
        build_wpcom_authorize_url("1", "http://127.0.0.1/x", "posts", "", "c")


def test_wpcom_scopes_exclude_global() -> None:
    assert "global" not in signin.WPCOM_SCOPES


def test_parse_wpcom_redirect_success() -> None:
    assert parse_wpcom_redirect("http://127.0.0.1:1/d?code=xyz&state=s", "s") == "xyz"


def test_parse_wpcom_redirect_state_mismatch() -> None:
    with pytest.raises(StateMismatchError):
        parse_wpcom_redirect("http://127.0.0.1:1/d?code=xyz&state=other", "s")
    with pytest.raises(StateMismatchError):
        parse_wpcom_redirect("http://127.0.0.1:1/d?code=xyz", "s")


def test_parse_wpcom_redirect_denied() -> None:
    with pytest.raises(AuthorizationDeniedError) as info:
        parse_wpcom_redirect("http://127.0.0.1:1/d?error=access_denied&state=s", "s")
    assert info.value.code == "QUILL-WORDPRESS-SIGNIN-DENIED"
    with pytest.raises(AuthorizationDeniedError, match="invalid_scope"):
        parse_wpcom_redirect("http://127.0.0.1:1/d?error=invalid_scope&state=s", "s")


def test_parse_wpcom_redirect_missing_code() -> None:
    with pytest.raises(MalformedRedirectError):
        parse_wpcom_redirect("http://127.0.0.1:1/d?state=s", "s")


# --------------------------------------------------------------------------
# Token requests and responses
# --------------------------------------------------------------------------


def test_token_request_shape() -> None:
    url, body, headers = token_request("CODE", "VERIFIER", "123", "http://127.0.0.1:9/d")
    assert url == "https://public-api.wordpress.com/oauth2-1/token"
    assert parse_qs(body.decode()) == {
        "grant_type": ["authorization_code"],
        "code": ["CODE"],
        "code_verifier": ["VERIFIER"],
        "client_id": ["123"],
        "redirect_uri": ["http://127.0.0.1:9/d"],
    }
    assert "client_secret" not in body.decode()
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert headers["Accept"] == "application/json"


def test_refresh_request_shape_accepts_secret_or_str() -> None:
    for token in (Secret("RT"), "RT"):
        url, body, headers = refresh_request(token, "123")
        assert url == signin.WPCOM_TOKEN_ENDPOINT
        assert parse_qs(body.decode()) == {
            "grant_type": ["refresh_token"],
            "refresh_token": ["RT"],
            "client_id": ["123"],
        }
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"


TOKEN_BODY = {
    "access_token": "ACCESS-SECRET",
    "refresh_token": "REFRESH-SECRET",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "sites posts media",
    "blog_id": 98765,
    "blog_url": "https://example.wordpress.com",
}


def test_parse_token_response_full() -> None:
    tokens = parse_token_response(TOKEN_BODY, now=1000.0)
    assert tokens.access_token.reveal() == "ACCESS-SECRET"
    assert tokens.refresh_token is not None
    assert tokens.refresh_token.reveal() == "REFRESH-SECRET"
    assert tokens.expires_at == 4600.0
    assert tokens.scope == ("sites", "posts", "media")
    assert tokens.blog_id == "98765"
    assert tokens.token_type == "bearer"
    assert not tokens.expired(now=1000.0)
    assert tokens.expired(now=4590.0)


def test_parse_token_response_minimal_and_json_text() -> None:
    tokens = parse_token_response(json.dumps({"access_token": "A"}))
    assert tokens.refresh_token is None
    assert tokens.expires_at is None
    assert tokens.blog_id is None
    assert tokens.scope == ()
    assert not tokens.expired()
    tokens = parse_token_response(
        b'{"access_token": "A", "blog_id": "0", "expires_in": "60"}', now=0
    )
    assert tokens.blog_id is None
    assert tokens.expires_at == 60.0


def test_wpcom_tokens_repr_is_redacted() -> None:
    tokens = parse_token_response(TOKEN_BODY, now=0)
    text = repr(tokens)
    assert "ACCESS-SECRET" not in text
    assert "REFRESH-SECRET" not in text
    assert "98765" in text
    assert isinstance(tokens, WpcomTokens)


@pytest.mark.parametrize(
    "body",
    [
        {"error": "invalid_grant", "error_description": "bad code"},
        {"token_type": "bearer"},
        {"access_token": ""},
        "not json",
        "[1, 2]",
    ],
)
def test_parse_token_response_errors(body: Any) -> None:
    with pytest.raises(TokenResponseError):
        parse_token_response(body)


class _FakeResponse(io.BytesIO):
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def test_exchange_code_uses_injected_opener() -> None:
    calls: list[tuple[urllib.request.Request, float]] = []

    def opener(request: urllib.request.Request, timeout: float) -> _FakeResponse:
        calls.append((request, timeout))
        return _FakeResponse(json.dumps(TOKEN_BODY).encode())

    tokens = exchange_code("C", "V" * 43, "123", "http://127.0.0.1:9/d", opener=opener, now=0)
    assert tokens.access_token.reveal() == "ACCESS-SECRET"
    ((request, timeout),) = calls
    assert request.full_url == signin.WPCOM_TOKEN_ENDPOINT
    assert request.get_method() == "POST"
    assert isinstance(request.data, bytes)
    assert parse_qs(request.data.decode())["code_verifier"] == ["V" * 43]
    assert timeout == 30.0


def test_refresh_tokens_uses_injected_opener() -> None:
    seen: list[bytes] = []

    def opener(request: urllib.request.Request, timeout: float) -> _FakeResponse:
        assert isinstance(request.data, bytes)
        seen.append(request.data)
        return _FakeResponse(b'{"access_token": "NEW"}')

    tokens = refresh_tokens(Secret("RT"), "123", opener=opener)
    assert tokens.access_token.reveal() == "NEW"
    assert parse_qs(seen[0].decode())["grant_type"] == ["refresh_token"]


def test_exchange_code_http_error_names_oauth_error_without_secrets() -> None:
    def opener(request: urllib.request.Request, timeout: float) -> Any:
        raise urllib.error.HTTPError(
            request.full_url,
            400,
            "Bad Request",
            {},  # type: ignore[arg-type]
            io.BytesIO(b'{"error": "invalid_grant", "error_description": "x"}'),
        )

    with pytest.raises(TokenResponseError, match="invalid_grant") as info:
        exchange_code("SECRET-CODE", "V" * 43, "1", "http://127.0.0.1/d", opener=opener)
    assert "SECRET-CODE" not in str(info.value)


def test_exchange_code_http_error_without_json_names_status() -> None:
    def opener(request: urllib.request.Request, timeout: float) -> Any:
        raise urllib.error.HTTPError(
            request.full_url,
            503,
            "Unavailable",
            {},  # type: ignore[arg-type]
            io.BytesIO(b"<html>down</html>"),
        )

    with pytest.raises(TokenResponseError, match="503"):
        exchange_code("C", "V" * 43, "1", "http://127.0.0.1/d", opener=opener)


def test_exchange_code_network_failure() -> None:
    def opener(request: urllib.request.Request, timeout: float) -> Any:
        raise urllib.error.URLError("no route")

    with pytest.raises(TokenResponseError, match="no route"):
        exchange_code("C", "V" * 43, "1", "http://127.0.0.1/d", opener=opener)


# --------------------------------------------------------------------------
# Loopback listener, for real on 127.0.0.1
# --------------------------------------------------------------------------


def _get(url: str) -> tuple[int, dict[str, str], str]:
    # A bare opener: no proxy may intercept a loopback request.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=5) as response:
            return response.status, dict(response.headers), response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        exc.close()
        return exc.code, dict(exc.headers), body


def test_listener_binds_loopback_ip_never_localhost() -> None:
    listener = LoopbackListener(timeout=5)
    try:
        uri = listener.start()
        assert uri.startswith("http://127.0.0.1:")
        assert "localhost" not in uri
        assert uri.endswith("/wordpress-done")
        assert listener.port > 0
    finally:
        listener.cancel()
    assert listener.wait(5) is None
    assert listener.outcome == "cancelled"


def test_listener_real_round_trip_with_authorize_application() -> None:
    received: list[str] = []
    state = new_state()
    listener = LoopbackListener(on_request=received.append, timeout=10)
    redirect = listener.start()
    authorize = build_authorize_application_url(
        "https://example.org/wp-admin/authorize-application.php",
        app_name="QUILL",
        app_id=str(uuid.uuid4()),
        success_url=redirect,
        reject_url=redirect,
        state=state,
    )
    success_url = _q(authorize)["success_url"][0]
    # Simulate WordPress appending its fields to our success_url.
    from urllib.parse import urlencode

    back = (
        success_url
        + "&"
        + urlencode({"site_url": "https://example.org", "user_login": "jeff", "password": PASSWORD})
    )

    # A stray favicon request first: 404, and it does not count.
    status, _, _ = _get(f"http://127.0.0.1:{listener.port}/favicon.ico")
    assert status == 404
    assert not listener.done

    status, headers, body = _get(back)
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    assert headers["Cache-Control"] == "no-store"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert '<html lang="en">' in body
    assert "<title>" in body and "</title>" in body
    assert "<h1>" in body
    assert "You can close this tab and go back to QUILL" in body
    assert PASSWORD not in body

    url = listener.wait(5)
    assert url == back
    assert received == [back]
    assert listener.outcome == "received"
    assert "abcd" not in repr(listener)

    result = parse_authorize_application_redirect(url, state)
    assert isinstance(result, AppPasswordResult)
    assert result.password.reveal() == PASSWORD

    # It shut down after the one request.
    with pytest.raises(urllib.error.URLError):
        urllib.request.build_opener(urllib.request.ProxyHandler({})).open(back, timeout=2)


def test_listener_rejected_page_says_not_connected() -> None:
    with LoopbackListener(timeout=10) as listener:
        status, _, body = _get(listener.redirect_uri + "?state=s&success=false")
        assert status == 200
        assert "not connected" in body
        assert "You can close this tab and go back to QUILL" in body
        url = listener.wait(5)
    assert url is not None
    assert isinstance(parse_authorize_application_redirect(url, "s"), Rejected)


def test_listener_custom_path_and_wpcom_code() -> None:
    with LoopbackListener("/wpcom-done", timeout=10) as listener:
        assert listener.redirect_uri.endswith("/wpcom-done")
        status, _, _ = _get(f"http://127.0.0.1:{listener.port}/wordpress-done?code=x&state=s")
        assert status == 404
        status, _, _ = _get(listener.redirect_uri + "?code=the-code&state=s")
        assert status == 200
        url = listener.wait(5)
    assert url is not None
    assert parse_wpcom_redirect(url, "s") == "the-code"


def test_listener_times_out() -> None:
    listener = LoopbackListener(timeout=0.3)
    listener.start()
    assert listener.wait(5) is None
    assert listener.outcome == "timed_out"
    assert listener.done


def test_listener_cancel_from_another_thread_unblocks_wait() -> None:
    listener = LoopbackListener(timeout=60)
    listener.start()
    timer = threading.Timer(0.2, listener.cancel)
    timer.start()
    try:
        assert listener.wait(10) is None
    finally:
        timer.cancel()
    assert listener.outcome == "cancelled"
    assert listener.done


def test_listener_cancel_before_start_and_twice() -> None:
    listener = LoopbackListener()
    listener.cancel()
    listener.cancel()
    assert listener.done
    assert listener.wait(1) is None


def test_listener_cannot_start_twice_or_report_port_before_start() -> None:
    listener = LoopbackListener(timeout=5)
    with pytest.raises(ListenerError):
        _ = listener.port
    listener.start()
    try:
        with pytest.raises(ListenerError):
            listener.start()
    finally:
        listener.cancel()
        listener.wait(5)


def test_listener_survives_a_failing_callback() -> None:
    def boom(url: str) -> None:
        raise RuntimeError("callback bug")

    with LoopbackListener(on_request=boom, timeout=10) as listener:
        status, _, _ = _get(listener.redirect_uri + "?state=s&code=c")
        assert status == 200
        assert listener.wait(5) is not None
    assert listener.outcome == "received"


def test_listener_rejects_relative_path() -> None:
    with pytest.raises(ValueError):
        LoopbackListener("wordpress-done")
