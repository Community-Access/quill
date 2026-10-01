"""QUILL Lite's half of the hosted AI: what it knows, and how it waits.

The shared capability lives in :mod:`quill.core.ai.gateway_client`,
:mod:`~quill.core.ai.gateway_session` and :mod:`~quill.core.ai.gateway_context`
-- all wx-free, all usable by QUILL. This module is the part that is QUILL Lite's
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
    """One per running QUILL Lite. Holds the session and does the waiting."""

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

    @property
    def own_key_active(self) -> bool:
        """Whether requests go to OpenAI or Google Gemini with the user's own key instead."""
        from quill.core.ai.own_key import own_key_active

        return own_key_active(getattr(self._app, "settings", None))

    @property
    def own_key_provider(self) -> str:
        """The active provider for own-key requests ('gemini' or 'openai')."""
        from quill.core.ai.own_key import active_own_key_provider

        return active_own_key_provider(getattr(self._app, "settings", None))

    @property
    def own_key_model(self) -> str:
        """The model own-key requests use: the chosen one, or the default."""
        from quill.core.ai.own_key import default_model

        chosen = getattr(getattr(self._app, "settings", None), "ai_own_key_model", "")
        return str(chosen or "").strip() or default_model(self.own_key_provider)

    # -- the ChatGPT subscription -------------------------------------------- #

    @property
    def chatgpt(self) -> Any:
        """This app's ChatGPT sign-in (:class:`quill.core.ai.chatgpt_account.ChatGptAccount`).

        Made on first use and kept: constructing it reads nothing, and the first
        question it is asked (``signed_in``) reads the credential store once.
        The agent name is the app's own -- "QUILL Lite", "QUILL" -- because
        OpenAI shows it on the consent page and in the person's ChatGPT settings,
        and each app signs in, and is revoked, on its own.
        """
        account = getattr(self, "_chatgpt", None)
        if account is None:
            from quill.core.ai.chatgpt_account import ChatGptAccount

            agent = str(getattr(self._app, "ai_agent_name", "") or "QUILL")
            account = ChatGptAccount(self.data_dir, agent_name=agent)
            self._chatgpt = account
        return account

    @property
    def chatgpt_active(self) -> bool:
        """Whether requests go to OpenAI on the person's ChatGPT plan.

        Whenever this app is signed in with ChatGPT -- there is no separate
        switch, for the same reason an own key has none: a sign-in somebody
        made is the choice, and Sign Out or Forget in the ChatGPT window is
        how it is unmade. A sign-in outranks a saved key: the plan is already
        paid for, where a key is billed per request.
        """
        try:
            return bool(self.chatgpt.signed_in)
        except Exception:  # noqa: BLE001 - an unreadable store is "not signed in"
            return False

    @property
    def route(self) -> str:
        """Which way requests travel: ``"chatgpt"``, ``"own_key"`` or ``"free"``."""
        if self.chatgpt_active:
            return "chatgpt"
        if self.own_key_active:
            return "own_key"
        return "free"

    @property
    def direct(self) -> bool:
        """Whether requests skip QUILL's service, and with it every QUILL limit."""
        return self.route != "free"

    @property
    def route_label(self) -> str:
        """The route as a person hears it: "your ChatGPT subscription" or "your own OpenAI key"."""
        return "your ChatGPT subscription" if self.chatgpt_active else "your own OpenAI key"

    @property
    def direct_model(self) -> str:
        """The model a direct route answers with, or "" when none is chosen yet."""
        if self.chatgpt_active:
            return str(self.chatgpt.model or "")
        return self.own_key_model

    def size_note(self, text: str) -> str:
        """What sending *text* on a direct route means, for the pad's summary.

        Empty on the free service, where the size limit speaks for itself. An
        own key is priced per request; a plan is not, so its note says usage
        rather than dollars (:func:`quill.core.ai.chatgpt_ai_help.size_note`).
        """
        if not self.direct:
            return ""
        free_tokens = self.free_limits.max_input_tokens
        if self.chatgpt_active:
            from quill.core.ai.chatgpt_ai_help import size_note

            return size_note(text, self.direct_model, free_limit_tokens=free_tokens)
        from quill.core.ai.own_key import size_warning

        return size_warning(text, self.own_key_model, free_limit_tokens=free_tokens)

    def conversation_note(self) -> str:
        """What a conversation costs on this route, said once at the top of the window."""
        if self.chatgpt_active:
            return (
                "This conversation uses your ChatGPT subscription: no QUILL limit, and "
                "each message counts toward your plan's own usage. The whole "
                "conversation goes with each message."
            )
        if self.own_key_active:
            return (
                "This conversation uses your own OpenAI key: no limits, billed to "
                "your OpenAI account. The whole conversation goes with each message, "
                "so a long one costs more per reply."
            )
        return (
            "Each message uses one of your free requests. The conversation so far "
            "goes with it as far as the free size limit allows, so a long "
            "conversation gradually forgets its beginning; this window says when "
            "that starts."
        )

    # -- what the service allows ----------------------------------------- #

    @property
    def limits(self) -> GatewayLimits:
        """The cached limits, or the shipped defaults until they are fetched.

        Never fetches on access: a property that opens a socket is a property
        that stalls a menu. :meth:`refresh_limits` is the explicit one, and the
        defaults are honest in the meantime -- they are the values the service
        actually ships with.
        """
        if self.chatgpt_active:
            from quill.core.ai.chatgpt_ai_help import CHATGPT_LIMITS

            return CHATGPT_LIMITS
        if self.own_key_active:
            from quill.core.ai.own_key import OWN_KEY_LIMITS

            return OWN_KEY_LIMITS
        return self._limits or GatewayLimits()

    @property
    def free_limits(self) -> GatewayLimits:
        """The free service's limits, whichever way requests are going.

        With an own key :attr:`limits` is deliberately unlimited; this is what
        the pad compares against to say "more than the free AI would accept".
        """
        return self._limits or GatewayLimits()

    def refresh_limits(self, on_done: Callable[[GatewayLimits], None] | None = None) -> None:
        """Fetch the limits in the background. Failure is silent by design.

        If the service cannot be reached the defaults stand, the pad still opens
        and the first real request reports the problem properly. Putting an
        error in front of somebody because a *background* refresh failed would
        be reporting our housekeeping as their problem.
        """

        if self.direct:
            return  # nothing to ask QUILL's service: the limits are OpenAI's

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
        if self.direct:
            return ""
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
        language: str = "",
    ) -> None:
        """Run one AI request. Returns at once; answers on the UI thread.

        *on_error* receives a finished sentence, never an exception. Every
        failure in the client is already a coded error whose text was written
        for a person to hear, so rendering one at a user is the whole job.
        *language* is Translate's target language.
        """
        if self.chatgpt_active:
            from quill.core.ai.chatgpt_ai_help import ask_with_chatgpt

            account = self.chatgpt

            def work(**_kwargs: Any) -> tuple[str, GatewayQuota | None]:
                answer = ask_with_chatgpt(
                    account, feature, prompt, chunks, language=language or "English"
                )
                return answer, None

        elif self.own_key_active:
            from quill.core.ai.own_key import ask_with_own_key

            prov = self.own_key_provider
            model = self.own_key_model

            def work(**_kwargs: Any) -> tuple[str, GatewayQuota | None]:
                answer = ask_with_own_key(
                    feature,
                    prompt,
                    chunks,
                    provider=prov,
                    model=model,
                    language=language or "English",
                )
                return answer, None

        else:
            client = self.client()

            def work(**_kwargs: Any) -> tuple[str, GatewayQuota | None]:
                return client.ask(feature, prompt, chunks, language=language)

        def done(_name: str, result: Any) -> None:
            text, quota = result
            _call_after(on_done, text, quota)

        def failed(_name: str, error: BaseException) -> None:
            _call_after(on_error, _sentence(error))

        _submit("quill-ai-ask", work, on_success=done, on_failure=failed)

    def converse(
        self,
        prompt: str,
        chunks: list[str] | None,
        history: list[dict[str, str]],
        *,
        on_done: Callable[[str, GatewayQuota | None, int], None],
        on_error: Callable[[str], None],
    ) -> None:
        """One conversation turn (:mod:`quill.core.ai.hosted_chat`). Returns at
        once; answers on the UI thread with ``(reply, quota, turns_dropped)``.

        With an own key the history goes to OpenAI as it is -- the window has
        already trimmed it only as far as the model can read -- and nothing is
        counted; on QUILL's service the service may trim further and says by
        how many turns.
        """
        if self.chatgpt_active:
            from quill.core.ai.chatgpt_ai_help import converse_with_chatgpt

            account = self.chatgpt

            def work(**_kwargs: Any) -> tuple[str, GatewayQuota | None, int]:
                return converse_with_chatgpt(account, prompt, chunks, history), None, 0

        elif self.own_key_active:
            from quill.core.ai.own_key import ask_with_own_key

            prov = self.own_key_provider
            model = self.own_key_model

            def work(**_kwargs: Any) -> tuple[str, GatewayQuota | None, int]:
                reply = ask_with_own_key(
                    "chat",
                    prompt,
                    chunks,
                    provider=prov,
                    model=model,
                    history=history,
                )
                return reply, None, 0

        else:
            client = self.client()

            def work(**_kwargs: Any) -> tuple[str, GatewayQuota | None, int]:
                return client.converse(prompt, chunks, history)

        def done(_name: str, result: Any) -> None:
            text, quota, dropped = result
            _call_after(on_done, text, quota, dropped)

        def failed(_name: str, error: BaseException) -> None:
            _call_after(on_error, _sentence(error))

        _submit("quill-ai-converse", work, on_success=done, on_failure=failed)

    def describe_image(
        self,
        path: Any,
        question: str,
        *,
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Ask About an Image. Returns at once; answers on the UI thread."""
        if self.chatgpt_active:
            from quill.core.ai.chatgpt_ai_help import describe_image_with_chatgpt

            account = self.chatgpt

            def work(**_kwargs: Any) -> str:
                return describe_image_with_chatgpt(account, path, question)

        elif self.own_key_active and self.own_key_provider == "gemini":
            from pathlib import Path
            from quill.core.ai.vision import describe_image as vision_describe
            from quill.core.assistant_ai import (
                AssistantConnectionSettings,
                default_host_for_provider,
                load_provider_api_key,
            )

            key = load_provider_api_key("gemini")
            model = self.own_key_model
            conn = AssistantConnectionSettings(
                provider="gemini",
                host=default_host_for_provider("gemini"),
                model=model,
            )

            def work(**_kwargs: Any) -> str:
                text, err = vision_describe(
                    conn,
                    key,
                    Path(path),
                    prompt=question or "Describe this image in detail.",
                )
                if err or not text:
                    raise ValueError(err or "Google Gemini returned an empty description.")
                return text

        else:
            from quill.core.ai.chatgpt_ai_help import describe_image_with_chatgpt

            account = self.chatgpt

            def work(**_kwargs: Any) -> str:
                return describe_image_with_chatgpt(account, path, question)

        def done(_name: str, text: Any) -> None:
            _call_after(on_done, str(text))

        def failed(_name: str, error: BaseException) -> None:
            if isinstance(error, ValueError):
                _call_after(on_error, str(error))
                return
            _call_after(on_error, _sentence(error))

        _submit("quill-ai-image", work, on_success=done, on_failure=failed)

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
                    "QUILL Lite. Nothing was saved.",
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
    from quill.core.error_codes import CodedError

    if isinstance(error, (GatewayError, CodedError)):
        # The sentence first and the code last. str(error) leads with
        # "[QUILL-AI-GATEWAY-QUOTA]", which a screen reader spells out before
        # the person hears what happened; support still gets the code.
        message = str(error.args[0]) if error.args else ""
        hint = getattr(error, "user_hint", "")
        code = getattr(error, "code", "")
        parts = [message, hint, f"Error code {code}." if code else ""]
        return " ".join(part.strip() for part in parts if part and part.strip())
    return "The AI service is not answering right now. Try again in a moment. Nothing was used."


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
    """One background job. QUILL Lite has no task manager, so this is the
    family's ``thread_submit`` -- the same one the update check uses."""
    from quill.ui.update_download import thread_submit

    thread_submit(name, func, on_success=on_success, on_failure=on_failure)


def _ignore(_name: str, _error: BaseException) -> None:
    """A background failure nobody needs to hear about."""


def _ignore2(_name: str, _result: Any) -> None:
    """A background success nobody needs to hear about."""
