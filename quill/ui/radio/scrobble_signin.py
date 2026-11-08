"""Sign in to last.fm or Libre.fm from Preferences, through the browser.

last.fm's desktop sign-in (:mod:`quill.core.radio.lastfm`): Quill Radio asks
for a token on a worker, opens the service's own "allow Quill Radio?" page in
the listener's browser, and waits in a plain message box until they come back
and choose OK. Only then is the token traded for a session key, again on a
worker. The password is typed into the service's page, never into Quill Radio.

Pressed again while signed in, the same button offers to sign out, with No as
the default so a reflexive Enter changes nothing. Credit: BlindRadio by
serrebidev (MIT) for scrobbling from a radio player.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from typing import Any

from quill.core.radio import lastfm, radio_credentials


def _title(service: lastfm.Service) -> str:
    return f"Sign In to {service.name}"


def approve_message(service: lastfm.Service, url: str) -> str:
    return (
        f"{service.name} is open in your web browser, asking whether Quill Radio may "
        "scrobble for you. Sign in there if it asks, choose Yes, allow access, then "
        "come back here and choose OK.\n\n"
        f"If the page did not open, go to this address: {url}"
    )


def sign_in(
    app: Any,
    service: lastfm.Service,
    own_pair: Callable[[], tuple[str, str]],
    *,
    after: Callable[[], None] | None = None,
) -> None:
    """The Sign In button. *own_pair* reads the key and secret boxes as they are now."""
    wx = app._wx
    if bool(getattr(app, "_safe_mode", False)):
        app._announce(f"Signing in to {service.name} is unavailable in Safe Mode.")
        return
    stored = radio_credentials.load(service.session_target)
    if stored.secret:
        who = f" as {stored.user_name}" if stored.user_name else ""
        answer = app._show_message_box(
            f"Quill Radio is signed in to {service.name}{who}. Sign out of "
            f"{service.name} on this computer? Songs stop going there until you "
            "sign in again.",
            f"{service.name} Sign-in",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        if answer == wx.YES:
            radio_credentials.save(service.session_target, "")
            if after is not None:
                after()
            app._announce(f"Signed out of {service.name}.")
        return
    typed_key, typed_secret = own_pair()
    key, secret = lastfm.app_credentials(typed_key, typed_secret)
    if not (key and secret):
        app._show_message_box(lastfm.NO_APP_KEY, _title(service), wx.OK | wx.ICON_INFORMATION)
        return
    own = (
        (typed_key.strip(), typed_secret.strip())
        if typed_key.strip() and typed_secret.strip()
        else None
    )
    safe_mode = bool(getattr(app, "_safe_mode", False))
    app._announce(f"Asking {service.name} for a sign-in page...")

    def _work(**_kwargs: Any) -> Any:
        return lastfm.get_token(service, api_key=key, secret=secret, safe_mode=safe_mode)

    def _done(_op: str, token: Any) -> None:
        wx.CallAfter(_approve, app, service, key, secret, str(token), own, after)

    def _failed(_op: str, error: BaseException) -> None:
        wx.CallAfter(app._announce, _sentence(error, f"{service.name} sign-in did not start."))

    app._task_manager.submit("radio-lastfm-token", _work, on_success=_done, on_failure=_failed)


def _sentence(error: BaseException, fallback: str) -> str:
    if isinstance(error, lastfm.LastFmError) and error.args:
        return str(error.args[0])
    return fallback


def _approve(
    app: Any,
    service: lastfm.Service,
    key: str,
    secret: str,
    token: str,
    own: tuple[str, str] | None,
    after: Callable[[], None] | None,
) -> None:
    """Open the service's page, wait for OK, then fetch the session on a worker."""
    wx = app._wx
    url = lastfm.auth_page_url(service, api_key=key, token=token)
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001 - the box below gives the address anyway
        pass
    answer = app._show_message_box(
        approve_message(service, url), _title(service), wx.OK | wx.CANCEL | wx.ICON_INFORMATION
    )
    if answer != wx.OK:
        app._announce(f"Signing in to {service.name} cancelled.")
        return
    safe_mode = bool(getattr(app, "_safe_mode", False))

    def _work(**_kwargs: Any) -> Any:
        return lastfm.get_session(
            service, api_key=key, secret=secret, token=token, safe_mode=safe_mode
        )

    def _done(_op: str, result: Any) -> None:
        user, session = result
        wx.CallAfter(_signed_in, app, service, str(user), str(session), own, after)

    def _failed(_op: str, error: BaseException) -> None:
        if isinstance(error, lastfm.LastFmError) and error.error_code == lastfm.NOT_AUTHORISED_CODE:
            text = (
                f"{service.name} has not been told yes yet. Choose Sign In to "
                f"{service.name} again, and choose Yes, allow access on its page "
                "before you come back."
            )
        else:
            text = _sentence(error, f"Signing in to {service.name} did not finish.")
        wx.CallAfter(app._announce, text)

    app._task_manager.submit("radio-lastfm-session", _work, on_success=_done, on_failure=_failed)


def _signed_in(
    app: Any,
    service: lastfm.Service,
    user: str,
    session: str,
    own: tuple[str, str] | None,
    after: Callable[[], None] | None,
) -> None:
    if own is not None:
        # The session belongs to the key that asked for it, so keep that key.
        radio_credentials.save(radio_credentials.LASTFM_API_KEY, own[0])
        radio_credentials.save(radio_credentials.LASTFM_SECRET, own[1])
    if not radio_credentials.save(service.session_target, session, user_name=user):
        app._announce(f"The {service.name} sign-in could not be saved on this computer.")
        return
    if after is not None:
        after()
    who = f" as {user}" if user else ""
    app._announce(
        f"Signed in to {service.name}{who}. Check Send the songs I hear to "
        f"{service.name} and choose OK to start."
    )


__all__ = ["approve_message", "sign_in"]
