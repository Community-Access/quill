"""Running an action on YouTube for the listener, one consent at a time.

Every write action -- reply, comment, delete, chat, subscribe, rate, add to a
playlist -- goes through :func:`run_write` here, which:

1. refuses in Safe Mode, and explains in one sentence when this copy of Quill
   Radio cannot sign in to YouTube at all (Connect YouTube Account locked off
   or not configured) or the listener has not connected yet;
2. the first time, shows the plain-language consent for the extra permission
   (:data:`quill.core.radio.youtube_write_scope.CONSENT_TEXT`) and, on OK,
   opens the browser for it -- never before;
3. runs the request on the task manager, then speaks the outcome once:
   the action's own sentence on success, the API's plain sentence on failure
   (the daily-limit sentence for a spent quota), written to Recent Problems.

Nothing here retries.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

UNAVAILABLE = (
    "Acting on YouTube needs Connect YouTube Account, which this copy of Quill "
    "Radio does not offer yet."
)
NOT_CONNECTED = "Connect your YouTube account first: Station menu, Connect YouTube Account."


def app_of(host: Any) -> Any:
    """The app frame behind *host* (a browse window carries it as download host)."""
    return getattr(host, "_download_host", None) or getattr(host, "_app", None) or host


def can_sign_in(host: Any) -> bool:
    """Whether this build and this run can use the official YouTube sign-in."""
    from quill.core.radio import youtube_oauth

    app = app_of(host)
    if bool(getattr(app, "_safe_mode", False)):
        return False
    features = getattr(app, "features", None)
    enabled = getattr(features, "is_enabled", None)
    if not callable(enabled) or not enabled("future.youtube_oauth"):
        return False
    return youtube_oauth.available()


def is_ready(host: Any) -> bool:
    """Signed in with permission to act: the write actions can run now."""
    from quill.core.radio import youtube_oauth, youtube_write_scope

    return (
        can_sign_in(host) and youtube_oauth.is_signed_in() and youtube_write_scope.has_write_scope()
    )


def _refusal(host: Any) -> str:
    from quill.core.radio import youtube_oauth

    app = app_of(host)
    if bool(getattr(app, "_safe_mode", False)):
        return "YouTube is not available in Safe Mode."
    if not can_sign_in(host):
        return UNAVAILABLE
    if not youtube_oauth.is_signed_in():
        return NOT_CONNECTED
    return ""


def ask_write_consent(host: Any) -> bool:
    """The plain-language consent for the extra permission. True on OK."""
    from quill.core.radio.youtube_write_scope import CONSENT_TEXT, CONSENT_TITLE

    app = app_of(host)
    wx = getattr(app, "_wx", None) or getattr(host, "_wx", None)
    if wx is None:
        import wx as _wx

        wx = _wx
    parent = getattr(app, "frame", None) or getattr(host, "_win", None)
    dialog = wx.MessageDialog(
        parent, CONSENT_TEXT, CONSENT_TITLE, wx.OK | wx.CANCEL | wx.ICON_INFORMATION
    )
    try:
        shower = getattr(app, "_show_modal_dialog", None)
        answer = (
            shower(dialog, CONSENT_TITLE) if callable(shower) else dialog.ShowModal()
        )  # dialog_button_contract: exempt
        return answer == wx.ID_OK
    finally:
        dialog.Destroy()


def run_write(
    host: Any,
    subject: str,
    work: Callable[[str], object],
    on_done: Callable[[object], None],
    *,
    on_failed: Callable[[str], None] | None = None,
) -> bool:
    """Run *work(access_token)* once permission is in hand; see the module doc.

    *subject* names the action for Recent Problems ("Reply on YouTube").
    Returns False when the action was refused or cancelled before starting.
    """
    announce = host._announce
    refusal = _refusal(host)
    if refusal:
        announce(refusal)
        return False
    from quill.core.radio import youtube_write_scope

    app = app_of(host)
    needs_consent = not youtube_write_scope.has_write_scope()
    if needs_consent:
        if not ask_write_consent(host):
            announce("Nothing was changed on YouTube.")
            return False
        announce("Opening your browser to ask Google for permission...")

    safe_mode = bool(getattr(app, "_safe_mode", False))

    def _work(**_kwargs: object) -> object:
        from quill.core.radio.youtube_oauth import YouTubeOAuthError

        if needs_consent:
            youtube_write_scope.grant_write_access(safe_mode=safe_mode)
        token = youtube_write_scope.write_token()
        if not token:
            raise YouTubeOAuthError(
                "Your YouTube sign-in has expired. Connect your YouTube account again."
            )
        return work(token)

    def _ok(_op: str, result: object) -> None:
        on_done(result)

    def _bad(_op: str, error: BaseException) -> None:
        from quill.core.radio.youtube_account_api import plain

        reason = plain(error) or "YouTube did not answer."
        announce(reason)
        record_problem(subject, reason)
        if on_failed is not None:
            on_failed(reason)

    manager = getattr(host, "_task_manager", None) or app._task_manager
    manager.submit("radio-youtube-account", _work, on_success=_ok, on_failure=_bad)
    return True


def record_problem(subject: str, reason: str) -> None:
    """Into Recent Problems. Never raises."""
    try:
        from quill.core import problem_log
        from quill.core.paths import app_data_dir

        problem_log.record_problem(app_data_dir(), problem_log.KIND_OTHER, subject, reason)
    except Exception:  # noqa: BLE001 - a problem list is never worth a crash
        return


def ask_text(host: Any, title: str, prompt: str, *, multiline: bool = True) -> str:
    """A labelled text prompt through the host's modal helper; "" on cancel."""
    app = app_of(host)
    import wx

    parent = getattr(app, "frame", None) or getattr(host, "_win", None)
    style = wx.OK | wx.CANCEL | (wx.TE_MULTILINE if multiline else 0)
    dialog = wx.TextEntryDialog(parent, prompt, title, style=style)
    try:
        shower = getattr(app, "_show_modal_dialog", None)
        answer = (
            shower(dialog, title) if callable(shower) else dialog.ShowModal()
        )  # dialog_button_contract: exempt
        return dialog.GetValue().strip() if answer == wx.ID_OK else ""
    finally:
        dialog.Destroy()


def confirm(host: Any, title: str, question: str) -> bool:
    """A Yes/No question with No the default, through the host's message box."""
    app = app_of(host)
    import wx

    box = getattr(app, "_show_message_box", None)
    if callable(box):
        return box(question, title, wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT) == wx.YES
    from quill.ui.dialog_contract import show_message_box

    parent = getattr(app, "frame", None)
    style = wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT
    return show_message_box(question, title, style, parent, announce=host._announce) == wx.YES


__all__ = [
    "NOT_CONNECTED",
    "UNAVAILABLE",
    "app_of",
    "ask_text",
    "ask_write_consent",
    "can_sign_in",
    "confirm",
    "is_ready",
    "record_problem",
    "run_write",
]
