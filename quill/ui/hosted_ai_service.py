"""QuillLite's half of the hosted AI: what it knows, and how it waits.

The shared capability lives in :mod:`quill.core.ai.gateway_client`,
:mod:`~quill.core.ai.gateway_session` and :mod:`~quill.core.ai.gateway_context`
-- all wx-free, all usable by QUILL. This module is the part that is QuillLite's
own: one object per app that holds the session, caches what the service allows,
and runs every request off the UI thread.

**The editor never waits.** Every call here returns immediately and answers on a
worker thread, marshalled back with ``wx.CallAfter``. A person can keep typing,
save, switch documents or close the window while an answer is on its way, and
nothing about a slow network reaches the caret. That is not a nicety for a tool
people write in; an editor that stops accepting keystrokes because a server is
thinking is an editor that has lost the thing it is for.

**Nothing happens until somebody asks.** No request on launch, on typing, on
save, on idle or on focus. The limits are fetched once, lazily, the first time a
window actually needs them -- so an install with the feature switched on but
never used makes no network call at all.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.ai.gateway_client import GatewayClient, GatewayLimits, GatewayQuota
from quill.core.ai.gateway_errors import GatewayError
from quill.core.ai.gateway_session import (
    GatewaySession,
    base_url,
    clear_token,
    load_session,
    load_token,
    save_session,
    save_token,
    support_id_for,
)

__all__ = ["AiService", "SignInCode"]


@dataclass(frozen=True, slots=True)
class SignInCode:
    """The code a person reads into a web page, and where to read it."""

    user_code: str
    verification_uri: str
    expires_in: float = 900.0
    #: The same page with the code already filled in, when the service offers
    #: one. What Open the Connect Page opens, so the only thing left to do in
    #: the browser is press Confirm.
    verification_uri_complete: str = ""

    @property
    def spoken(self) -> str:
        """The code as separate characters, for a reader that would otherwise
        run them together.

        ``BKRT-3927`` read as a word is a word nobody can type back. Spaced out,
        it is nine things a person can hear one at a time -- and they are going
        to be typing it into a different device with the reader still talking.
        """
        return " ".join(self.user_code.replace("-", " dash "))


class AiService:
    """One per running QuillLite. Holds the session and does the waiting."""

    def __init__(self, app: Any) -> None:
        self._app = app
        self._limits: GatewayLimits | None = None
        self._session: GatewaySession | None = None

    # -- what this computer knows --------------------------------------- #

    @property
    def data_dir(self):
        return self._app.data_dir

    @property
    def session(self) -> GatewaySession:
        if self._session is None:
            self._session = load_session(self.data_dir)
        return self._session

    @property
    def token(self) -> str:
        return load_token()

    @property
    def signed_in(self) -> bool:
        return bool(self.token and self.session.signed_in)

    @property
    def support_id(self) -> str:
        return support_id_for(self.session.device_id)

    def client(self) -> GatewayClient:
        return GatewayClient(self.session.base_url or base_url(), self.token)

    # -- what the service allows ----------------------------------------- #

    @property
    def limits(self) -> GatewayLimits:
        """The cached limits, or the shipped defaults until they are fetched.

        Never fetches on access: a property that opens a socket is a property
        that stalls a menu. :meth:`refresh_limits` is the explicit one, and the
        defaults are honest in the meantime -- they are the values the service
        actually ships with.
        """
        return self._limits or GatewayLimits()

    def refresh_limits(self, on_done: Callable[[GatewayLimits], None] | None = None) -> None:
        """Fetch the limits in the background. Failure is silent by design.

        If the service cannot be reached the defaults stand, the pad still opens
        and the first real request reports the problem properly. Putting an
        error in front of somebody because a *background* refresh failed would
        be reporting our housekeeping as their problem.
        """

        def work(**_kwargs: Any) -> GatewayLimits:
            return GatewayClient(self.session.base_url or base_url()).fetch_limits()

        def done(_name: str, limits: Any) -> None:
            self._limits = limits
            if on_done is not None:
                _call_after(on_done, limits)

        _submit("quill-ai-limits", work, on_success=done, on_failure=_ignore)

    # -- availability, answered without a round trip ---------------------- #

    def unavailable_reason(self, feature: str = "") -> str:
        """Why a request would fail right now, or "" if it would not.

        Answered from local state only. The authoritative answer always comes
        from the server on the next real request; this exists so the pad can say
        "you are not connected" without a network call, and so a menu never
        stalls.
        """
        if not self.signed_in:
            return (
                "This computer is not connected to QUILL's free AI. "
                "Choose Connect or Sign Out in the AI menu to connect it."
            )
        if self._limits is not None and not self._limits.hosted_ai_enabled:
            return (
                "QUILL's free AI is paused for everyone right now. "
                "Your own API key still works if you have one."
            )
        if feature and self._limits is not None and not self._limits.feature_available(feature):
            return f"{feature.replace('_', ' ').capitalize()} is not available right now."
        return ""

    # -- the one that costs something ------------------------------------- #

    def ask(
        self,
        feature: str,
        prompt: str,
        chunks: list[str] | None,
        *,
        on_done: Callable[[str, GatewayQuota | None], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Run one AI request. Returns at once; answers on the UI thread.

        *on_error* receives a finished sentence, never an exception. Every
        failure in the client is already a coded error whose text was written
        for a person to hear, so rendering one at a user is the whole job.
        """
        client = self.client()

        def work(**_kwargs: Any) -> tuple[str, GatewayQuota | None]:
            return client.ask(feature, prompt, chunks)

        def done(_name: str, result: Any) -> None:
            text, quota = result
            _call_after(on_done, text, quota)

        def failed(_name: str, error: BaseException) -> None:
            _call_after(on_error, _sentence(error))

        _submit("quill-ai-ask", work, on_success=done, on_failure=failed)

    def fetch_quota(
        self,
        *,
        on_done: Callable[[GatewayQuota], None],
        on_error: Callable[[str], None],
    ) -> None:
        client = self.client()

        def work(**_kwargs: Any) -> GatewayQuota:
            return client.fetch_quota()

        def done(_name: str, quota: Any) -> None:
            _call_after(on_done, quota)

        def failed(_name: str, error: BaseException) -> None:
            _call_after(on_error, _sentence(error))

        _submit("quill-ai-quota", work, on_success=done, on_failure=failed)

    # -- connecting and disconnecting -------------------------------------- #

    def start_sign_in(
        self,
        *,
        on_code: Callable[[SignInCode], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Begin the device-code flow.

        Two callbacks rather than one because there are two moments worth
        announcing and they are minutes apart: the code appearing, and the
        connection completing. Polling in between says nothing at all -- a
        progress noise every five seconds while somebody is typing a code into
        a phone is the loudest possible way to be unhelpful.
        """
        from quill.core.ai.device_login import (
            STATUS_AUTHORIZED,
            DeviceFlowConfig,
            request_device_code,
            run_device_login,
        )
        from quill.core.ai.gateway_client import device_flow_poster

        url = base_url()
        poster = device_flow_poster(url)
        config = DeviceFlowConfig(
            client_id="quill-lite",
            device_authorization_url=f"{url}/device/code",
            token_url=f"{url}/device/token",
        )

        def work(**_kwargs: Any) -> Any:
            import time

            grant = request_device_code(config, poster=poster)
            _call_after(
                on_code,
                SignInCode(
                    grant.user_code,
                    grant.verification_uri,
                    grant.expires_in,
                    grant.verification_uri_complete or "",
                ),
            )
            return run_device_login(
                config, grant, poster=poster, clock=time.monotonic, sleeper=time.sleep
            )

        def done(_name: str, result: Any) -> None:
            if result.status != STATUS_AUTHORIZED or not result.tokens:
                _call_after(on_error, _sign_in_failure(result))
                return
            token = str(result.tokens.get("access_token", ""))
            device_id = str(result.tokens.get("device_id", ""))
            if not save_token(token):
                _call_after(
                    on_error,
                    "QUILL connected, but could not store the sign-in securely on "
                    "this computer, so it would be forgotten when you close "
                    "QuillLite. Nothing was saved.",
                )
                return
            session = GatewaySession(device_id=device_id, base_url=url, connected_at=_now())
            save_session(self.data_dir, session)
            self._session = session
            _call_after(on_done, support_id_for(device_id))

        def failed(_name: str, error: BaseException) -> None:
            _call_after(on_error, _sentence(error))

        _submit("quill-ai-signin", work, on_success=done, on_failure=failed)

    def sign_out(self) -> None:
        """Forget this account locally, and tell the server if we can.

        The local half always succeeds. Somebody who asks to sign out ends up
        signed out whether or not they have a network connection, and a token
        the server still believes in that nothing holds any more is revocable
        from the console.
        """
        device_id = self.session.device_id
        client = self.client()

        def work(**_kwargs: Any) -> None:
            client.revoke(device_id)

        if device_id and client.token:
            _submit("quill-ai-revoke", work, on_success=_ignore2, on_failure=_ignore)

        clear_token()
        save_session(self.data_dir, GatewaySession())
        self._session = GatewaySession()


# --------------------------------------------------------------------------- #
# Small helpers, kept at the bottom so the class reads as one thing
# --------------------------------------------------------------------------- #


def _sentence(error: BaseException) -> str:
    """A finished sentence for a person, from whatever went wrong.

    A coded gateway error already carries one, plus a hint saying what to do
    next -- both are worth speaking, and the hint is usually the more useful
    half. Anything else gets a generic sentence rather than a traceback: a
    ``ConnectionResetError`` rendered at a listener tells them nothing they can
    act on.
    """
    if isinstance(error, GatewayError):
        # The sentence first and the code last. str(error) leads with
        # "[QUILL-AI-GATEWAY-QUOTA]", which a screen reader spells out before
        # the person hears what happened; support still gets the code.
        message = str(error.args[0]) if error.args else ""
        hint = getattr(error, "user_hint", "")
        code = getattr(error, "code", "")
        parts = [message, hint, f"Error code {code}." if code else ""]
        return " ".join(part.strip() for part in parts if part and part.strip())
    return "QUILL's free AI is not answering right now. Try again in a moment. Nothing was used."


def _sign_in_failure(result: Any) -> str:
    from quill.core.ai.device_login import STATUS_DENIED, STATUS_EXPIRED

    if result.status == STATUS_EXPIRED:
        return "That code expired before it was used. Choose Get a New Code for a fresh one."
    if result.status == STATUS_DENIED:
        return "The connection was refused at the web page. Choose Get a New Code to try again."
    return str(getattr(result, "error", "")) or "QUILL could not connect this computer."


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def _call_after(func: Callable[..., None], *args: Any) -> None:
    import wx

    wx.CallAfter(func, *args)


def _submit(name: str, func: Callable[..., Any], *, on_success: Any, on_failure: Any) -> None:
    """One background job. QuillLite has no task manager, so this is the
    family's ``thread_submit`` -- the same one the update check uses."""
    from quill.ui.update_download import thread_submit

    thread_submit(name, func, on_success=on_success, on_failure=on_failure)


def _ignore(_name: str, _error: BaseException) -> None:
    """A background failure nobody needs to hear about."""


def _ignore2(_name: str, _result: Any) -> None:
    """A background success nobody needs to hear about."""
