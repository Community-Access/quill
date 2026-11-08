"""Sign In with GitHub: the device code in the one sign-in step, for both editors.

The default way into the GitHub Workbench since 2026-11-07, opened from Manage
GitHub Accounts in QUILL and QUILL Lite alike (the shared
:mod:`quill.ui.github_accounts_flow`). It is My GitHub Copilot's sign-in step
(:class:`quill.ui.hosted_ai_connections.SignInStep`, as
:mod:`quill.ui.copilot_onboarding_dialog` uses it) with the Workbench's own
title and scopes, so a person who has signed in to one has already learned the
other:

* one sentence saying what to do, read-only;
* the code, read-only and spaced out so a reader says each character. When it
  arrives it is put on the clipboard, GitHub's page opens in the browser, and
  focus moves to the code, so the reader says the code itself. The one thing
  announced is what the reader cannot know -- that the code is on the
  clipboard and the page is opening (GATE-13; through the host's announcement
  service, so it is brailled too, GATE-BRAILLE);
* **Open the Page Again** (the default) opens the page again; **Cancel** stops
  the wait at once.

The waiting runs on the host's task submitter, never the UI thread
(:class:`quill.core.github.oauth_sign_in.WorkbenchSignIn` polls at GitHub's
interval and backs off on ``slow_down``). A failure -- the code expiring, the
request declined, the network -- is one sentence in the What to do field, with
focus moved there so it is read. On success the step closes itself and hands
the token back; the account flow then asks GitHub whose it is and saves it the
same way a pasted token is saved.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.github import oauth_sign_in

__all__ = ["TITLE", "sign_in_with_github"]

TITLE = "Sign In with GitHub"

Submit = Callable[..., Any]


def _launch(url: str) -> bool:
    """Open *url* in the default browser; False when nothing opened."""
    return bool(wx.LaunchDefaultBrowser(url))


def _copy(text: str) -> bool:
    from quill.ui.say_commands import set_clipboard_text

    return set_clipboard_text(text)


def _message(error: BaseException) -> str:
    return str(error.args[0]) if error.args else str(error)


def sign_in_with_github(
    parent: Any,
    app_name: str,
    announce: Callable[[str], None],
    *,
    submit: Submit,
    call_after: Callable[..., None],
    sign_in: oauth_sign_in.WorkbenchSignIn | None = None,
) -> str | None:
    """Run the step for *app_name*. The new token, or None when nothing was approved.

    *submit* runs blocking work off the UI thread with the task manager's
    shape (``name, func, on_success=, on_failure=``); its callbacks may arrive
    on any thread, so everything that touches the step goes through
    *call_after*.
    """
    from quill.ui.dialog_contract import show_modal_dialog
    from quill.ui.hosted_ai_connections import SignInStep

    if not oauth_sign_in.is_available(app_name):
        announce(oauth_sign_in.sign_in_unavailable_message(app_name))
        return None
    flow = sign_in or oauth_sign_in.WorkbenchSignIn(app_name)
    state: dict[str, Any] = {"grant": None, "token": None}

    def page_url() -> str:
        grant = state["grant"]
        return str(getattr(grant, "verification_uri", "") or oauth_sign_in.DEVICE_PAGE)

    def open_page(step: SignInStep) -> None:
        # The step disabled its button for the wait; this page can be opened again.
        step.open_button.SetLabel("&Open the Page Again")
        step.open_button.Enable()
        if state["grant"] is None:
            return  # still asking for a code; it opens the page when it arrives
        if not _launch(page_url()):
            step.failed(f"Your browser did not open. Go to {page_url()} and type the code.")

    sentence = (
        f"To sign in to the GitHub Workbench, approve {app_name} on GitHub's page "
        "and type the code below there."
    )
    step = SignInStep(parent, sentence, open_page, with_code=True)
    step.SetTitle(TITLE)

    def failed(message: str) -> None:
        if step:
            step.failed(message)

    def finished(token: str) -> None:
        state["token"] = token
        if step:
            step.succeeded()

    def code_arrived(grant: Any) -> None:
        if not step:
            return
        state["grant"] = grant
        step.code.SetValue(oauth_sign_in.spoken_code(grant.user_code))
        copied = _copy(grant.user_code)
        submit(
            "quill-github-sign-in-wait",
            lambda **_k: flow.wait(grant),
            on_success=lambda _n, token: call_after(finished, token),
            on_failure=lambda _n, error: (
                None
                if isinstance(error, oauth_sign_in.GitHubSignInCancelled)
                else call_after(failed, _message(error))
            ),
        )
        if not step:
            return  # the wait already finished (and closed the step)
        step.open_button.SetLabel("&Open the Page Again")
        if not _launch(page_url()):
            where = " It is on the clipboard." if copied else ""
            step.failed(f"Your browser did not open. Go to {page_url()} and type the code.{where}")
            return
        step.status.SetValue(f"Waiting for you to approve {app_name} on GitHub's page...")
        step.code.SetFocus()  # the reader says the code as the field takes focus
        if copied:
            announce("The code is on the clipboard. GitHub's page is opening in your browser.")
        else:
            announce("GitHub's page is opening in your browser. Type the code there.")

    submit(
        "quill-github-sign-in-code",
        lambda **_k: flow.request_code(),
        on_success=lambda _n, grant: call_after(code_arrived, grant),
        on_failure=lambda _n, error: call_after(failed, _message(error)),
    )
    try:
        show_modal_dialog(step, TITLE)
    finally:
        flow.cancel()  # a wait still running stops now; after success it is a no-op
        step.Destroy()
    token = state["token"]
    return str(token) if token else None
