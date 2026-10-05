"""Disconnect YouTube Account: revoke off the UI thread, forget always, say one thing."""

from __future__ import annotations

import json
import urllib.error

import pytest

from quill.core.auth.token_bundle import TokenBundle
from quill.core.radio import youtube_oauth as oauth
from quill.ui.radio import youtube_oauth_ui as ui


class _Vault:
    def __init__(self) -> None:
        self.values: dict[object, str] = {}

    def get(self, ref: object) -> str | None:
        return self.values.get(ref)

    def set(self, ref: object, value: str) -> None:
        self.values[ref] = value

    def delete(self, ref: object) -> None:
        self.values.pop(ref, None)


class _Wx:
    YES, NO = 5103, 5104
    ICON_QUESTION, YES_NO, NO_DEFAULT = 1, 2, 4

    @staticmethod
    def CallAfter(func, *args) -> None:  # noqa: N802 - wx API
        func(*args)


class _Tasks:
    def __init__(self) -> None:
        self.names: list[str] = []

    def submit(self, name, work, *, on_success=None, on_failure=None):
        self.names.append(name)
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            on_failure(name, error)
            return
        on_success(name, result)


class _Host:
    def __init__(self, answer: int) -> None:
        self._wx = _Wx()
        self._task_manager = _Tasks()
        self.said: list[str] = []
        self._announce = self.said.append
        self.answer = answer
        self.asked: list[int] = []

    def _show_message_box(self, _message: str, _title: str, style: int) -> int:
        self.asked.append(style)
        return self.answer


@pytest.fixture
def vault(monkeypatch) -> _Vault:
    fake = _Vault()
    monkeypatch.setattr(oauth, "_SECRETS", fake)
    oauth.save_tokens(
        TokenBundle(
            access_token="ya29.access-secret",
            refresh_token="1//refresh-secret",
            expires_at=9e12,
            scope=oauth.SCOPE,
        )
    )
    return fake


def _google_answers(monkeypatch, status: int, payload: object = None) -> list[object]:
    sent: list[object] = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> None:
            return None

        def read(self) -> bytes:
            return b"" if payload is None else json.dumps(payload).encode("utf-8")

    def urlopen(request, **_kwargs):
        sent.append(request)
        if status != 200:
            import io

            raise urllib.error.HTTPError(
                request.full_url, status, "error", {}, io.BytesIO(_Response().read())
            )
        response = _Response()
        response.status = 200  # type: ignore[attr-defined]
        return response

    monkeypatch.setattr(oauth.urllib.request, "urlopen", urlopen)
    return sent


def test_revoked_at_google_says_disconnected_once(vault, monkeypatch) -> None:
    sent = _google_answers(monkeypatch, 200)
    host = _Host(_Wx.YES)
    ui.disconnect_youtube_account(host)
    assert host._task_manager.names == ["youtube-oauth-disconnect"]
    assert len(sent) == 1
    assert host.said == [ui.DISCONNECTED]
    assert vault.values == {}


def test_already_revoked_is_the_same_as_revoked(vault, monkeypatch) -> None:
    _google_answers(monkeypatch, 400, {"error": "invalid_token"})
    host = _Host(_Wx.YES)
    ui.disconnect_youtube_account(host)
    assert host.said == [ui.DISCONNECTED]
    assert vault.values == {}


def test_a_server_error_forgets_locally_and_says_how_to_finish(vault, monkeypatch) -> None:
    _google_answers(monkeypatch, 500)
    host = _Host(_Wx.YES)
    ui.disconnect_youtube_account(host)
    assert host.said == [ui.DISCONNECTED_LOCALLY]
    assert "myaccount.google.com/permissions" in host.said[0]
    assert vault.values == {}


def test_no_connection_forgets_locally_and_says_how_to_finish(vault, monkeypatch) -> None:
    def offline(_request, **_kwargs):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(oauth.urllib.request, "urlopen", offline)
    host = _Host(_Wx.YES)
    ui.disconnect_youtube_account(host)
    assert host.said == [ui.DISCONNECTED_LOCALLY]
    assert vault.values == {}


def test_an_unexpected_failure_still_forgets_the_session(vault, monkeypatch) -> None:
    def broken(**_kwargs):
        raise RuntimeError("vault locked")

    monkeypatch.setattr(oauth, "sign_out", broken)
    host = _Host(_Wx.YES)
    ui.disconnect_youtube_account(host)
    assert host.said == [ui.DISCONNECTED_LOCALLY]
    assert vault.values == {}


def test_no_is_the_default_and_answering_no_changes_nothing(vault, monkeypatch) -> None:
    sent = _google_answers(monkeypatch, 200)
    host = _Host(_Wx.NO)
    ui.disconnect_youtube_account(host)
    assert host.asked == [_Wx.ICON_QUESTION | _Wx.YES_NO | _Wx.NO_DEFAULT]
    assert sent == []
    assert host.said == []
    assert oauth.is_signed_in()


def test_the_token_is_never_spoken(vault, monkeypatch) -> None:
    _google_answers(monkeypatch, 500)
    host = _Host(_Wx.YES)
    ui.disconnect_youtube_account(host)
    assert host.said
    assert not any("secret" in line for line in host.said)
