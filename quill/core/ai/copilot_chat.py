"""My GitHub Copilot as a hosted-AI route: ask, converse, stream, models, quota.

The single-request side of Copilot (codex.md 10A.12), the counterpart of
``chatgpt_ai_help.respond_on_plan`` for the ChatGPT plan. It is a small facade
over the Copilot pack (:mod:`quill.ai_packs.copilot`), and makes its clients
exactly the way the pack does -- the pinned bundled CLI over explicit stdio,
the scrubbed child environment, this app's own token passed as
``github_token`` -- so everything said about that path holds here too.

What a request looks like:

* **No vendor tools, ever.** The session's ``available_tools`` names only a
  QUILL tool that matches no built-in, and every permission request is
  refused (``PermissionDecisionReject``); Copilot can only answer in text.
* **The family line is added here** (:func:`text_only.with_family_instruction`,
  decision 13), after the caller's system text, appended to the CLI's own
  system message (``mode: append``). The answer is returned as received; the
  caller runs :func:`text_only.as_text`, as it does for every connection.
* **Pictures go as attachments**: ``{"type": "blob", "data": <base64>,
  "mimeType": ...}``, PNG, JPEG, WebP or GIF only. Whether the chosen model
  sees is the capability registry's question (``connection_caps.require``),
  answered per model from :meth:`CopilotChat.list_models`.
* **No server-side conversation.** :meth:`CopilotChat.converse` resends the
  local history with every turn in a fresh session, so nothing about the
  conversation is kept anywhere but the app's own window.
* **The asyncio loop runs on the calling worker thread** (``asyncio.run``),
  and a call from the main thread -- the UI thread in every QuillVille app --
  is refused rather than freezing the window.
* **Safe Mode refuses** before anything starts.

**Failures, as 10A.5 words them.** A 401 or a rejected credential means GitHub
ended the sign-in: the token is forgotten, the row reads "signed out by
GitHub" and :class:`CopilotSignInEnded` carries "Your GitHub Copilot sign-in
has ended. Nothing was sent. ...". A spent quota is :class:`CopilotLimitReached`
with the limit sentence; Copilot switched off by an organisation or plan
(R15) is :class:`CopilotNotForAccount`. None is retried and none falls back to
another connection (decision 15). How GitHub labels each failure is read
from the ``session.error`` event (``status_code``, ``error_type``,
``error_code``, ``remediation``) or the JSON-RPC error; the exact labels are
to verify against a live account (G1).

wx-free and strict-typed.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
import threading
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Any, TypeVar

from quill.core.ai import copilot_auth, copilot_state
from quill.core.ai.connection_caps import COPILOT, PICTURES, set_model_capabilities
from quill.core.ai.connection_choice import (
    limit_sentence,
    not_for_account_sentence,
    revoked_sentence,
)
from quill.core.ai.copilot_chat_parts import (
    AUTO_MODEL,
    AUTO_MODEL_NAME,
    FAILED,
    IMAGE_TYPES,
    LIMIT,
    NOT_FOR_ACCOUNT,
    REVOKED,
    VISION_SOURCE,
    ChatTurn,
    CopilotAnswer,
    CopilotChatError,
    CopilotImage,
    CopilotLimitReached,
    CopilotModel,
    CopilotModelList,
    CopilotNotForAccount,
    CopilotRefused,
    CopilotSignInEnded,
    attachments_for,
    classify_failure,
    conversation_prompt,
    enum_text,
    event_type,
    models_from_info,
)
from quill.core.ai.copilot_quota import CopilotQuota, quota_from_result
from quill.core.ai.text_only import with_family_instruction
from quill.core.error_codes import CodedError

__all__ = [
    "AUTO_MODEL",
    "AUTO_MODEL_NAME",
    "FAILED",
    "IMAGE_TYPES",
    "LIMIT",
    "NOT_FOR_ACCOUNT",
    "REVOKED",
    "VISION_SOURCE",
    "ChatTurn",
    "CopilotAnswer",
    "CopilotChat",
    "CopilotChatError",
    "CopilotImage",
    "CopilotLimitReached",
    "CopilotModel",
    "CopilotModelList",
    "CopilotNotForAccount",
    "CopilotRefused",
    "CopilotSignInEnded",
    "attachments_for",
    "classify_failure",
    "conversation_prompt",
    "models_from_info",
]

_SAFE_MODE = "Safe Mode is on, so AI is off. Nothing was sent."
_UI_THREAD = "GitHub Copilot was asked on the window's own thread. Nothing was sent."
T = TypeVar("T")


def _safe_mode() -> bool:
    from quill.stability.safe_mode import should_enable_safe_mode

    return should_enable_safe_mode(sys.argv, os.environ)


# -- the event listener -------------------------------------------------------------- #


class _Listener:
    """Collects what one turn's events say: deltas, the last error, token counts."""

    def __init__(self, on_delta: Callable[[str], None] | None) -> None:
        self.on_delta = on_delta
        self.parts: list[str] = []
        self.error: Any = None
        self.model = ""
        self.input_tokens = 0
        self.output_tokens = 0
        self.stopped = False

    def __call__(self, event: object) -> None:
        kind = event_type(event)
        data = getattr(event, "data", None)
        if kind == "assistant.message_delta":
            delta = str(getattr(data, "delta_content", "") or "")
            if delta:
                self.parts.append(delta)
                if self.on_delta is not None:
                    self.on_delta(delta)
        elif kind == "session.error":
            self.error = data
        elif kind == "assistant.usage":
            self.model = str(getattr(data, "model", "") or self.model)
            self.input_tokens += int(getattr(data, "input_tokens", 0) or 0)
            self.output_tokens += int(getattr(data, "output_tokens", 0) or 0)

    @property
    def text(self) -> str:
        return "".join(self.parts)


async def _watch_stop(
    stop: Callable[[], bool], session: Any, listener: _Listener, interval: float
) -> None:
    while not stop():
        await asyncio.sleep(interval)
    listener.stopped = True
    await session.abort()


# -- the facade ------------------------------------------------------------------- #


class CopilotChat:
    """Single requests and conversations on this app's GitHub Copilot sign-in.

    Every method blocks: call it from a worker thread
    (``QuillTaskManager``), never the UI thread, and hand the result back with
    ``wx.CallAfter``.
    """

    #: How often a stream checks its stop callable, in seconds.
    stop_poll_seconds = 0.1

    def __init__(
        self,
        agent_name: str = copilot_auth.DEFAULT_AGENT_NAME,
        *,
        app_name: str = "",
        model: str = "",
        timeout: float | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.agent_name = agent_name or copilot_auth.DEFAULT_AGENT_NAME
        self.app_name = app_name or self.agent_name
        self.model = model.strip()
        self.timeout = timeout
        self.data_dir = data_dir

    # -- the public calls ---------------------------------------------------- #

    def ask(
        self,
        prompt: str,
        *,
        system: str = "",
        images: Sequence[CopilotImage] = (),
        model: str = "",
    ) -> CopilotAnswer:
        """One request, one answer (``send_and_wait``); pictures as attachments."""
        return self._turn(prompt, system=system, images=images, model=model)

    def stream(
        self,
        prompt: str,
        *,
        on_delta: Callable[[str], None],
        system: str = "",
        images: Sequence[CopilotImage] = (),
        model: str = "",
        stop: Callable[[], bool] | None = None,
    ) -> CopilotAnswer:
        """One request whose text arrives in pieces: *on_delta* gets each one.

        *on_delta* runs on this worker thread. *stop* is polled; once it
        answers True the turn is aborted and the text so far comes back with
        ``stopped=True``.
        """
        return self._turn(
            prompt,
            system=system,
            images=images,
            model=model,
            on_delta=on_delta,
            stop=stop,
        )

    def converse(
        self,
        history: Sequence[ChatTurn | tuple[str, str]],
        prompt: str,
        *,
        system: str = "",
        images: Sequence[CopilotImage] = (),
        model: str = "",
        on_delta: Callable[[str], None] | None = None,
        stop: Callable[[], bool] | None = None,
    ) -> CopilotAnswer:
        """The next turn of a conversation kept on this computer.

        *history* (oldest first) is resent with *prompt* in a fresh session;
        pictures belong to this turn only. Streams when *on_delta* is given.
        """
        return self._turn(
            conversation_prompt(history, prompt),
            system=system,
            images=images,
            model=model,
            on_delta=on_delta,
            stop=stop,
        )

    def list_models(self) -> CopilotModelList:
        """The models this account may use (``models.list``), service order kept.

        Each model's vision flag is recorded in the capability registry with
        the SDK as its source, so "pictures, per model" is decided by what
        GitHub reported. A plan allowed only Auto lists the one Auto row.
        """

        async def work(client: Any) -> Any:
            return await client.list_models()

        infos = self._with_client(work)
        result = models_from_info(list(infos or ()))
        for model in result.models:
            set_model_capabilities(
                COPILOT, model.id, {PICTURES: model.vision}, source=VISION_SOURCE
            )
        return result

    def quota(self) -> CopilotQuota:
        """GitHub's own count for this account (``account.getQuota``)."""

        async def work(client: Any) -> Any:
            rpc = importlib.import_module("copilot.rpc")
            return await client.rpc.account.get_quota(rpc.AccountGetQuotaRequest())

        return quota_from_result(self._with_client(work))

    # -- the machinery ----------------------------------------------------- #

    def _refuse_if_blocked(self) -> None:
        if _safe_mode():
            raise CopilotRefused(_SAFE_MODE)
        if threading.current_thread() is threading.main_thread():
            raise CopilotRefused(_UI_THREAD)

    def _client(self, copilot: Any) -> Any:
        """A ``CopilotClient`` made exactly as the pack makes one (not started)."""
        from quill.ai_packs.copilot import client_kwargs

        return copilot.CopilotClient(**client_kwargs(copilot, self.agent_name))

    def _send_timeout(self) -> float:
        if self.timeout is not None:
            return self.timeout
        from quill.ai_packs.copilot import SEND_TIMEOUT_SECONDS

        return SEND_TIMEOUT_SECONDS

    def _session_kwargs(self, system: str, model: str, streaming: bool) -> dict[str, Any]:
        from quill.ai_packs.copilot import available_tools_for, reject_class, system_message_for

        reject = reject_class()
        refusal = "QUILL answers in text only; no tools are offered."

        def deny(request: object, invocation: object) -> object:
            return reject(feedback=refusal)

        kwargs: dict[str, Any] = {
            "available_tools": available_tools_for(),
            "on_permission_request": deny,
            "system_message": system_message_for(with_family_instruction(system)),
        }
        chosen = (model or self.model).strip()
        if chosen and chosen != AUTO_MODEL:
            kwargs["model"] = chosen
        if streaming:
            kwargs["streaming"] = True
        return kwargs

    def _turn(
        self,
        prompt: str,
        *,
        system: str,
        images: Sequence[CopilotImage],
        model: str,
        on_delta: Callable[[str], None] | None = None,
        stop: Callable[[], bool] | None = None,
    ) -> CopilotAnswer:
        self._refuse_if_blocked()
        attachments = attachments_for(images)  # refused before anything starts
        listener = _Listener(on_delta)
        session_kwargs = self._session_kwargs(system, model, streaming=on_delta is not None)
        timeout = self._send_timeout()

        async def work(client: Any) -> CopilotAnswer:
            async with await client.create_session(**session_kwargs) as session:
                unsubscribe = session.on(listener)
                stopper = (
                    asyncio.ensure_future(
                        _watch_stop(stop, session, listener, self.stop_poll_seconds)
                    )
                    if stop is not None
                    else None
                )
                try:
                    result = await session.send_and_wait(
                        prompt, attachments=attachments or None, timeout=timeout
                    )
                except TimeoutError:
                    await session.abort()  # the SDK's timeout only stops waiting
                    raise
                except Exception:
                    if listener.stopped:
                        return self._answer(None, listener, stopped=True)
                    raise
                finally:
                    if stopper is not None:
                        stopper.cancel()
                    if callable(unsubscribe):
                        unsubscribe()
                return self._answer(result, listener, stopped=listener.stopped)

        answer: CopilotAnswer = self._with_client(work, listener)
        return answer

    def _answer(self, result: object, listener: _Listener, *, stopped: bool) -> CopilotAnswer:
        from quill.ai_packs.copilot import answer_text

        return CopilotAnswer(
            text=answer_text(result) or listener.text,
            model=listener.model,
            input_tokens=listener.input_tokens,
            output_tokens=listener.output_tokens,
            stopped=stopped,
        )

    def _with_client(
        self, work: Callable[[Any], Awaitable[T]], listener: _Listener | None = None
    ) -> T:
        """Run *work* against a started client on this thread's own event loop."""
        self._refuse_if_blocked()
        copilot = importlib.import_module("copilot")

        async def run() -> T:
            async with self._client(copilot) as client:
                return await work(client)

        try:
            value = asyncio.run(run())
        except CopilotChatError:
            raise
        except CodedError:
            raise  # an unverified bundled CLI keeps its own code and sentence
        except Exception as exc:  # noqa: BLE001 - every SDK failure is worded once
            raise self._failure(exc, listener.error if listener else None) from exc
        copilot_state.clear_marks(self.agent_name, data_dir=self.data_dir)
        return value

    def _failure(self, exc: BaseException, session_error: Any) -> CopilotChatError:
        """The worded error for *exc*, recording what GitHub said about the account."""
        holder = session_error if session_error is not None else exc
        status = getattr(holder, "status_code", None)
        if status is None and getattr(exc, "code", None) in (401, 402, 403, 429):
            status = getattr(exc, "code", None)
        message = str(getattr(holder, "message", "") or exc)
        outcome = classify_failure(
            status_code=status if isinstance(status, int) else None,
            error_type=enum_text(getattr(holder, "error_type", "")),
            error_code=enum_text(getattr(holder, "error_code", "")),
            message=message,
            remediation=enum_text(getattr(holder, "remediation", "")),
        )
        detail = message.strip()
        if outcome == REVOKED:
            copilot_state.mark_ended_by_github(self.agent_name, data_dir=self.data_dir)
            return CopilotSignInEnded(revoked_sentence(COPILOT), detail=detail)
        if outcome == LIMIT:
            return CopilotLimitReached(limit_sentence(COPILOT, self.app_name), detail=detail)
        if outcome == NOT_FOR_ACCOUNT:
            copilot_state.mark_policy_off(self.agent_name, data_dir=self.data_dir)
            return CopilotNotForAccount(not_for_account_sentence(), detail=detail)
        if isinstance(exc, TimeoutError):
            return CopilotChatError(
                "GitHub Copilot took too long to answer and was stopped.", detail=detail
            )
        reason = detail.rstrip(".") or type(exc).__name__
        return CopilotChatError(f"GitHub Copilot did not answer: {reason}.", detail=detail)
