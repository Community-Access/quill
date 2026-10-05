"""Write actions ask for the extra permission once, refuse plainly, and say outcomes once."""

from __future__ import annotations

import pytest

from quill.core.auth.token_bundle import TokenBundle
from quill.core.radio import youtube_account_api as api
from quill.core.radio import youtube_oauth as oauth
from quill.core.radio import youtube_write_scope as ws
from quill.ui.radio import youtube_account_ui as ui


class _Tasks:
    def submit(self, name, work, *, on_success=None, on_failure=None):
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            on_failure(name, error)
            return
        on_success(name, result)


class _Features:
    def __init__(self, on: bool) -> None:
        self.on = on

    def is_enabled(self, _name: str) -> bool:
        return self.on


class _App:
    def __init__(self, *, feature: bool = True) -> None:
        self.said: list[str] = []
        self._announce = self.said.append
        self._task_manager = _Tasks()
        self.features = _Features(feature)
        self._safe_mode = False


@pytest.fixture
def session(monkeypatch):
    state = {
        "bundle": TokenBundle(
            access_token="AT", refresh_token="RT", expires_at=9e12, scope=oauth.SCOPE
        )
    }
    monkeypatch.setattr(oauth, "available", lambda: True)
    monkeypatch.setattr(oauth, "load_tokens", lambda: state["bundle"])
    monkeypatch.setattr(ui, "record_problem", lambda *_a: None)
    asked: list[bool] = []

    def consent(_host):
        asked.append(True)
        return True

    def grant(**_kwargs):
        state["bundle"] = TokenBundle(
            access_token="AT2",
            refresh_token="RT",
            expires_at=9e12,
            scope=f"{oauth.SCOPE} {ws.WRITE_SCOPE}",
        )

    monkeypatch.setattr(ui, "ask_write_consent", consent)
    monkeypatch.setattr(ws, "grant_write_access", grant)
    return state, asked


def test_first_write_asks_for_permission_then_never_again(session) -> None:
    _state, asked = session
    app = _App()
    tokens: list[str] = []
    ui.run_write(app, "Like", lambda t: tokens.append(t), lambda _r: app._announce("Liked."))
    ui.run_write(app, "Like", lambda t: tokens.append(t), lambda _r: app._announce("Liked."))
    assert asked == [True]
    assert tokens == ["AT2", "AT2"]
    assert app.said.count("Liked.") == 2


def test_declining_the_permission_changes_nothing(session, monkeypatch) -> None:
    monkeypatch.setattr(ui, "ask_write_consent", lambda _h: False)
    app = _App()
    ran: list[str] = []
    assert ui.run_write(app, "Like", ran.append, lambda _r: None) is False
    assert ran == [] and app.said == ["Nothing was changed on YouTube."]


def test_quota_is_one_plain_sentence(session) -> None:
    state, _asked = session
    state["bundle"] = TokenBundle(
        access_token="AT", expires_at=9e12, scope=f"{oauth.SCOPE} {ws.WRITE_SCOPE}"
    )
    app = _App()
    failures: list[str] = []

    def work(_token):
        raise api.QuotaExceeded(api.QUOTA_SENTENCE)

    ui.run_write(app, "Subscribe", work, lambda _r: None, on_failed=failures.append)
    assert app.said == [api.QUOTA_SENTENCE] and failures == [api.QUOTA_SENTENCE]


def test_not_connected_and_unavailable_are_explained(monkeypatch) -> None:
    monkeypatch.setattr(oauth, "available", lambda: True)
    monkeypatch.setattr(oauth, "load_tokens", lambda: TokenBundle())
    app = _App()
    assert ui.run_write(app, "x", lambda _t: None, lambda _r: None) is False
    assert app.said == [ui.NOT_CONNECTED]
    locked = _App(feature=False)
    ui.run_write(locked, "x", lambda _t: None, lambda _r: None)
    assert locked.said == [ui.UNAVAILABLE]


def test_subscribe_falls_back_to_the_confirm_page_without_a_session(monkeypatch) -> None:
    from quill.ui.radio import youtube_row_account

    monkeypatch.setattr(oauth, "available", lambda: False)
    opened: list[bool] = []
    youtube_row_account.subscribe(
        _App(), None, ["https://www.youtube.com/@x"], lambda: opened.append(True)
    )
    assert opened == [True]
