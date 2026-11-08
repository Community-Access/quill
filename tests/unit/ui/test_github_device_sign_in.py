"""Sign In with GitHub's step, on a real wx window over a fake GitHub.

The step is My GitHub Copilot's ``SignInStep``; what is tested here is what the
Workbench does with it: the code goes on the clipboard and into the field, the
page opens, one sentence is announced, the wait runs off the UI thread, and
each way GitHub can say no ends in one sentence in the What to do field.

Work submitted off the UI thread and ``call_after`` callbacks are queued and
run by the fake ``show_modal_dialog``, the way they arrive during a real modal
loop -- running them inline would let a failure be overwritten by the code that
follows it, which never happens in the app.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.ai import copilot_auth  # noqa: E402
from quill.core.github.oauth_sign_in import WorkbenchSignIn  # noqa: E402
from quill.ui import github_device_sign_in  # noqa: E402
from quill.ui.github_device_sign_in import TITLE, sign_in_with_github  # noqa: E402

_CODE_REPLY = {
    "device_code": "dev-123",
    "user_code": "WDJB-MJHT",
    "verification_uri": "https://github.com/login/device",
    "interval": 5,
    "expires_in": 900,
}


class _Harness:
    def __init__(self, monkeypatch, polls: list[dict[str, Any]], *, browser: bool = True) -> None:
        self.polls = list(polls)
        self.jobs: list[tuple[str, Any, Any, Any]] = []
        self.ui: list[tuple[Any, tuple[Any, ...]]] = []
        self.said: list[str] = []
        self.copied: list[str] = []
        self.opened: list[str] = []
        self.seen: dict[str, Any] = {}
        self.cancel_in_modal = False
        monkeypatch.setattr(
            github_device_sign_in, "_copy", lambda text: self.copied.append(text) or True
        )
        monkeypatch.setattr(
            github_device_sign_in, "_launch", lambda url: self.opened.append(url) or browser
        )
        monkeypatch.setattr("quill.ui.dialog_contract.show_modal_dialog", self.modal)
        self.flow = WorkbenchSignIn("QUILL", poster=self.post)
        self.flow._sleep = lambda _s: None  # type: ignore[method-assign]

    def post(self, url: str, _form: dict[str, str]) -> dict[str, Any]:
        if url == copilot_auth.GITHUB_DEVICE_AUTH_URL:
            return dict(_CODE_REPLY)
        reply = self.polls.pop(0) if self.polls else {"error": "authorization_pending"}
        if isinstance(reply, Exception):
            raise reply
        return reply

    def submit(self, name: str, func: Any, *, on_success: Any, on_failure: Any) -> None:
        self.jobs.append((name, func, on_success, on_failure))

    def call_after(self, fn: Any, *args: Any) -> None:
        self.ui.append((fn, args))

    def modal(self, step: Any, label: str) -> int:
        assert label == TITLE
        assert step.GetTitle() == TITLE
        while self.jobs or self.ui:
            if self.ui:
                fn, args = self.ui.pop(0)
                fn(*args)
                continue
            name, func, on_success, on_failure = self.jobs.pop(0)
            if self.cancel_in_modal and name.endswith("wait"):
                self.flow.cancel()
            try:
                result = func(cancellation_token=None)
            except BaseException as error:  # noqa: BLE001
                on_failure(name, error)
            else:
                on_success(name, result)
        self.seen = {
            "status": step.status.GetValue(),
            "code": step.code.GetValue(),
            "button": step.open_button.GetLabel(),
        }
        return wx.ID_CANCEL

    def run(self) -> str | None:
        return sign_in_with_github(
            None,
            "QUILL",
            self.said.append,
            submit=self.submit,
            call_after=self.call_after,
            sign_in=self.flow,
        )


@pytest.fixture(autouse=True)
def _app(wx_session_app, monkeypatch):
    monkeypatch.delenv(copilot_auth.CLIENT_ID_OVERRIDE_ENV, raising=False)
    return wx_session_app


def test_success_copies_the_code_opens_the_page_and_returns_the_token(monkeypatch) -> None:
    harness = _Harness(monkeypatch, [{"error": "authorization_pending"}, {"access_token": "gho_1"}])

    assert harness.run() == "gho_1"

    assert harness.copied == ["WDJB-MJHT"]
    assert harness.opened == ["https://github.com/login/device"]
    assert harness.seen["code"] == "W D J B dash M J H T"
    assert harness.seen["button"] == "&Open the Page Again"
    # Said once, and never the code: focus on the field already reads it.
    assert harness.said == [
        "The code is on the clipboard. GitHub's page is opening in your browser."
    ]
    assert [name for name, *_ in harness.jobs] == []  # every job ran off the modal loop


@pytest.mark.parametrize(
    ("reply", "sentence"),
    [
        (
            {"error": "access_denied"},
            "The sign-in was declined on GitHub's page. Nothing was saved.",
        ),
        (
            {"error": "expired_token"},
            "The code expired before it was used. Choose Sign In with GitHub for a new one.",
        ),
        (
            OSError("reset"),
            "GitHub stopped answering before the sign-in finished. "
            "Check your connection and try again.",
        ),
    ],
)
def test_github_saying_no_leaves_one_sentence_and_no_token(monkeypatch, reply, sentence) -> None:
    harness = _Harness(monkeypatch, [reply])

    assert harness.run() is None

    assert harness.seen["status"] == sentence
    assert len(harness.said) == 1  # the clipboard sentence only; the failure is in the field


def test_no_code_from_github_is_said_in_the_field(monkeypatch) -> None:
    harness = _Harness(monkeypatch, [])

    def broken(_url: str, _form: dict[str, str]) -> dict[str, Any]:
        raise OSError("no route")

    harness.flow._poster = broken  # type: ignore[assignment]

    assert harness.run() is None
    assert harness.seen["status"] == (
        "GitHub did not give a sign-in code. Check your connection and try again."
    )
    assert harness.copied == [] and harness.opened == [] and harness.said == []


def test_a_browser_that_does_not_open_names_the_address_instead(monkeypatch) -> None:
    harness = _Harness(monkeypatch, [{"error": "access_denied"}], browser=False)
    harness.polls = []  # still pending when the person gives up
    harness.cancel_in_modal = True

    assert harness.run() is None

    assert harness.seen["status"] == (
        "Your browser did not open. Go to https://github.com/login/device and type "
        "the code. It is on the clipboard."
    )
    assert harness.said == []  # the field took focus with that sentence


def test_cancel_stops_the_wait_and_saves_nothing(monkeypatch) -> None:
    harness = _Harness(monkeypatch, [{"error": "authorization_pending"}] * 5)
    harness.cancel_in_modal = True

    assert harness.run() is None
    assert harness.flow.cancelled.is_set()
    assert "declined" not in harness.seen["status"]


def test_an_app_with_no_registration_says_so_and_opens_nothing(monkeypatch) -> None:
    opened: list[object] = []
    monkeypatch.setattr("quill.ui.dialog_contract.show_modal_dialog", lambda *a: opened.append(a))
    said: list[str] = []

    token = sign_in_with_github(
        None,
        "QUILL Nowhere",
        said.append,
        submit=lambda *_a, **_k: None,
        call_after=lambda fn, *a: fn(*a),
    )

    assert token is None
    assert opened == []
    assert said == [
        "Sign in with GitHub is not available in this copy of QUILL Nowhere. "
        "Choose Add Token to sign in with a personal access token instead."
    ]


def _manage_dialog(**kwargs: Any) -> Any:
    from quill.ui.github_dialogs import GitHubManageAccountsDialog

    return GitHubManageAccountsDialog(None, **kwargs)


def test_manage_accounts_offers_sign_in_first_and_as_the_default(monkeypatch) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()  # SetHelpText stores nothing without one
    dialog = _manage_dialog()
    button = dialog._sign_in_btn
    assert button.GetLabel() == "&Sign In with GitHub..."
    assert button.GetHelpText()
    assert dialog.dialog.GetDefaultItem() is button
    assert dialog.dialog.FindWindowById(wx.ID_ADD).GetLabel() == "Add &Token (Advanced)..."
    monkeypatch.setattr(
        "quill.ui.github_dialogs.show_modal_dialog", lambda *_a: int(dialog._sign_in_id)
    )

    assert dialog.show() == "sign_in"


def test_with_an_account_enter_closes_rather_than_signing_in_again(monkeypatch) -> None:
    from types import SimpleNamespace

    account = SimpleNamespace(id="a", login="octocat", host="github.com")
    dialog = _manage_dialog(
        login="octocat", has_token=True, accounts=[account], active_account_id="a"
    )
    try:
        assert dialog.dialog.GetDefaultItem() is dialog.dialog.FindWindowById(wx.ID_OK)
    finally:
        dialog.dialog.Destroy()
