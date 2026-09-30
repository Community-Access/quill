"""Use My ChatGPT Subscription: built for real, in every state."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

from quill.ui import hosted_ai_chatgpt as module  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Account:
    def __init__(self, *, signed_in: bool, model: str = "", web: bool = False) -> None:
        self.agent_name = "QUILL Lite"
        self.signed_in = signed_in
        self.model = model
        self.web_search = web
        self.state = SimpleNamespace(account_label="jeff@example.com", web_search=web)
        self.forgotten = 0
        self.signed_out = 0
        self.cancelled = 0

    def set_model(self, model: str) -> None:
        self.model = model

    def set_web_search(self, allowed: bool) -> None:
        self.web_search = allowed

    def forget(self) -> None:
        self.forgotten += 1
        self.signed_in = False

    def sign_out(self) -> bool:
        self.signed_out += 1
        self.signed_in = False
        return True

    def cancel_sign_in(self) -> None:
        self.cancelled += 1


@pytest.fixture
def run_now(monkeypatch):
    import quill.ui.update_download as download

    def submit(name, work, *, on_success, on_failure):
        try:
            on_success(name, work())
        except Exception as error:  # noqa: BLE001 - the harness stands in for the thread
            on_failure(name, error)

    monkeypatch.setattr(download, "thread_submit", submit)
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *args: fn(*args))


def _labels(frame) -> list[str]:
    found = []
    pending = list(frame.GetChildren())
    while pending:
        window = pending.pop(0)
        pending.extend(window.GetChildren())
        if isinstance(window, wx.Button):
            found.append(window.GetLabel().replace("&", ""))
    return found


def test_signed_out_offers_only_continue_and_close(wx_app, run_now) -> None:
    frame = module.ChatGptFrame(None, _Account(signed_in=False), lambda _t: None)
    try:
        labels = _labels(frame)
        assert "Continue with ChatGPT" in labels
        assert "Close" in labels
        assert not any("Sign Out" in label or "Forget" in label for label in labels)
    finally:
        frame.Destroy()


def test_signed_in_lists_the_models_saves_the_first_and_offers_the_way_out(wx_app, run_now) -> None:
    account = _Account(signed_in=True)
    said = []
    models = [
        SimpleNamespace(slug="gpt-6-luna", label="Luna 6"),
        SimpleNamespace(slug="gpt-6", label="gpt-6"),
    ]
    frame = module.ChatGptFrame(None, account, said.append, list_models=lambda: models)
    try:
        labels = _labels(frame)
        assert "Sign Out" in labels
        assert "Forget on This Computer" in labels
        assert "Open ChatGPT Usage" in labels
        assert frame._model.GetCount() == 2
        assert frame._model.GetString(0) == "Luna 6 (gpt-6-luna)"
        # No model chosen before: the plan's first is saved so the next request needs no visit here.
        assert account.model == "gpt-6-luna"
        frame._model.SetSelection(1)
        frame._on_model_chosen()
        assert account.model == "gpt-6"
        frame._web.SetValue(True)
        frame._on_web_changed()
        assert account.web_search is True
    finally:
        frame.Destroy()


def test_a_saved_model_stays_selected_when_the_list_arrives(wx_app, run_now) -> None:
    account = _Account(signed_in=True, model="gpt-6")
    models = [
        SimpleNamespace(slug="gpt-6-luna", label="Luna 6"),
        SimpleNamespace(slug="gpt-6", label="gpt-6"),
    ]
    frame = module.ChatGptFrame(None, account, lambda _t: None, list_models=lambda: models)
    try:
        assert frame._model.GetSelection() == 1
        assert account.model == "gpt-6"
    finally:
        frame.Destroy()


def test_sign_out_takes_two_presses_and_returns_to_the_signed_out_state(wx_app, run_now) -> None:
    account = _Account(signed_in=True, model="gpt-6")
    said = []
    changes = []
    frame = module.ChatGptFrame(
        None, account, said.append, on_change=lambda: changes.append(1), list_models=lambda: []
    )
    try:
        frame._on_sign_out()
        assert account.signed_out == 0
        assert any("Press again" in s for s in said)
        frame._on_sign_out()
        assert account.signed_out == 1
        assert changes
        labels = _labels(frame)
        assert "Continue with ChatGPT" in labels
        assert "Sign Out" not in labels
        assert any(s == "Signed out of ChatGPT." for s in said)
    finally:
        frame.Destroy()


def test_forget_is_local_and_names_where_the_app_still_appears(wx_app, run_now) -> None:
    account = _Account(signed_in=True, model="gpt-6")
    said = []
    frame = module.ChatGptFrame(None, account, said.append, list_models=lambda: [])
    try:
        frame._on_forget()
        assert account.forgotten == 1
        assert account.signed_out == 0
        assert any("ChatGPT's settings" in s for s in said)
        assert "Continue with ChatGPT" in _labels(frame)
    finally:
        frame.Destroy()


def test_continue_signs_in_and_lands_on_the_model_list(wx_app, run_now, monkeypatch) -> None:
    account = _Account(signed_in=False)

    def sign_in(*, on_waiting=None):
        if on_waiting is not None:
            on_waiting("")
        account.signed_in = True
        return account.state

    account.sign_in = sign_in
    said = []
    models = [SimpleNamespace(slug="gpt-6", label="gpt-6")]
    frame = module.ChatGptFrame(None, account, said.append, list_models=lambda: models)
    try:
        frame._on_continue()
        assert "Sign Out" in _labels(frame)
        assert any("Signed in with ChatGPT as jeff@example.com" in s for s in said)
        assert account.model == "gpt-6"
    finally:
        frame.Destroy()


def test_a_refused_sign_in_is_said_and_offers_to_try_again(wx_app, run_now) -> None:
    from quill.core.ai.chatgpt_errors import ChatGptSignInError

    account = _Account(signed_in=False)

    def sign_in(*, on_waiting=None):
        raise ChatGptSignInError("You said no.")

    account.sign_in = sign_in
    said = []
    frame = module.ChatGptFrame(None, account, said.append)
    try:
        frame._on_continue()
        assert "Continue with ChatGPT" in _labels(frame)
        assert any("You said no." in s for s in said)
        assert "QUILL-AI-CHATGPT-SIGNIN" in frame._status.GetValue()
    finally:
        frame.Destroy()


def test_the_about_text_names_the_agent_and_the_model() -> None:
    account = _Account(signed_in=True, model="gpt-6")
    text = module.chatgpt_about_text(account)
    assert "jeff@example.com" in text
    assert "gpt-6" in text
    assert "chatgpt.com" in text


def test_escape_closes_the_window(wx_app, run_now) -> None:
    frame = module.ChatGptFrame(None, _Account(signed_in=False), lambda _t: None)
    closed = []
    frame.Bind(wx.EVT_CLOSE, lambda event: (closed.append(True), event.Skip()))
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_ESCAPE)
    frame.GetEventHandler().ProcessEvent(event)
    assert closed
