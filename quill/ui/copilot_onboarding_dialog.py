"""Signing in to My GitHub Copilot: the one sign-in step, with a device code.

The Copilot row of Choose Your AI (codex.md 10A.3, 10A.12) signs in through the
window's one sign-in step (:class:`quill.ui.hosted_ai_connections.SignInStep`),
the same layout every connection uses, with one more field for GitHub's code:

* one sentence -- "To use My GitHub Copilot, approve QUILL on GitHub's page.";
* the code, read-only and spaced out so a reader says each character, and
  already on the clipboard when it arrives (said once, because a field that
  changes without focus is something the reader does not say);
* **Open the Page** (the default) opens GitHub's page; **Cancel** stops the
  wait at once;
* on success the step closes itself, and the window says "Signed in to My
  GitHub Copilot. It is now in use."

**The Install step is retired.** The Copilot SDK and CLI ship in the shared
runtime since Phase 2 (10A.12), so sign-in is the only step there is. This
module used to hold a two-step "Set Up GitHub Copilot" dialog; the AI Hub's
Engines tab and the engine status cell now open this same step.

**Per app, and only with a registration.** Each app signs in under its own name
and keeps its own token (:mod:`quill.core.ai.copilot_sign_in`). With no GitHub
client id for this app the step never opens: the caller hears
:func:`quill.core.ai.copilot_auth.sign_in_unavailable_message` in one sentence.

The waiting happens on worker threads and comes back with ``wx.CallAfter``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai import copilot_auth
from quill.core.ai.connection_caps import COPILOT

__all__ = ["copilot_sign_in", "sign_in_copilot_for_app"]


def _copy(text: str) -> bool:
    """Put *text* on the clipboard; False when the clipboard is busy."""
    clipboard = wx.TheClipboard
    if not clipboard.Open():
        return False
    try:
        return bool(clipboard.SetData(wx.TextDataObject(text)))
    finally:
        clipboard.Close()


def copilot_sign_in(parent: Any, service: Any, announce: Callable[[str], None]) -> bool:
    """Run the Copilot sign-in step for *service*'s app. True when signed in.

    *announce* says the one thing the step itself cannot show the reader: the
    code arriving in a field that does not have focus. Every other outcome is
    the caller's to say.
    """
    return sign_in_copilot_for_app(
        parent,
        str(getattr(service, "agent_name", "") or copilot_auth.DEFAULT_AGENT_NAME),
        announce,
        data_dir=getattr(service, "data_dir", None),
    )


def sign_in_copilot_for_app(
    parent: Any,
    agent_name: str,
    announce: Callable[[str], None],
    *,
    data_dir: Any = None,
) -> bool:
    """The step for *agent_name*; the AI Hub and the engine status cell call this too."""
    from quill.core.ai.connection_words import sign_in_sentence
    from quill.core.ai.copilot_sign_in import CopilotSignIn, SignInCancelled, spoken_code
    from quill.ui.dialog_contract import show_modal_dialog
    from quill.ui.hosted_ai_connections import SIGN_IN_TITLE, SignInStep
    from quill.ui.update_download import thread_submit

    if not copilot_auth.is_configured(agent_name):
        announce(copilot_auth.sign_in_unavailable_message(agent_name))
        return False
    flow = CopilotSignIn(agent_name, data_dir=data_dir)
    state: dict[str, Any] = {"grant": None, "open_when_ready": False}

    def open_page(step: SignInStep) -> None:
        grant = state["grant"]
        if grant is None:
            state["open_when_ready"] = True  # opened as soon as the code arrives
            return
        url = grant.verification_uri
        if not wx.LaunchDefaultBrowser(url):
            step.failed(f"Your browser did not open. Go to {url} and type the code.")

    step = SignInStep(parent, sign_in_sentence(COPILOT, agent_name), open_page, with_code=True)

    def failed(message: str) -> None:
        if step:
            step.failed(message)

    def code_arrived(grant: Any) -> None:
        if not step:
            return
        state["grant"] = grant
        spaced = spoken_code(grant.user_code)
        step.code.SetValue(spaced)
        copied = _copy(grant.user_code)
        where = " It is on the clipboard." if copied else ""
        announce(f"The code is {spaced}.{where}")
        thread_submit(
            "quill-ai-copilot-wait",
            lambda **_k: flow.wait(grant),
            on_success=lambda _n, _r: wx.CallAfter(step.succeeded),
            on_failure=lambda _n, error: (
                None
                if isinstance(error, SignInCancelled)
                else wx.CallAfter(failed, str(error.args[0]) if error.args else str(error))
            ),
        )
        if state["open_when_ready"]:
            open_page(step)

    thread_submit(
        "quill-ai-copilot-code",
        lambda **_k: flow.request_code(),
        on_success=lambda _n, grant: wx.CallAfter(code_arrived, grant),
        on_failure=lambda _n, error: wx.CallAfter(
            failed, str(error.args[0]) if error.args else str(error)
        ),
    )
    try:
        result = show_modal_dialog(step, SIGN_IN_TITLE)
    finally:
        flow.cancel()  # a wait still running stops now; after success it is a no-op
        step.Destroy()
    return result == wx.ID_OK and bool(copilot_auth.stored_token(agent_name))
