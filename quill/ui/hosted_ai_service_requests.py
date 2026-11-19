"""Requests routed through the selected hosted-AI connection."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from quill.core.ai.connection_caps import CHATGPT, COPILOT, OWN_KEY
from quill.core.ai.gateway_client import GatewayQuota
from quill.core.ai.text_only import as_text
from quill.ui.hosted_ai_service_support import _call_after, _submit

__all__ = ["AiRequestMixin"]


class AiRequestMixin:
    """Build and submit requests for the route selected by the listener."""

    # -- the one that costs something ------------------------------------- #

    def _auto_retry(
        self,
        *,
        error: BaseException,
        failed_connection: str,
        requires: tuple[str, ...],
        build_work: Callable[[str], Callable[..., Any]],
        operation: str,
        on_success: Callable[..., None],
        on_error: Callable[[str], None],
        stop: threading.Event | None = None,
    ) -> bool:
        """Ask before a one-time retry of a failed Auto request on another provider."""
        if stop is not None and stop.is_set():
            return True
        connection = self.confirm_auto_retry(error, failed_connection, requires)
        if not connection:
            return False
        self._announce_auto_route(connection, retry=True)

        def failed(_name: str, retry_error: BaseException) -> None:
            _call_after(on_error, self._failure_sentence(retry_error, connection))

        _submit(
            f"quill-ai-{operation}-retry",
            build_work(connection),
            on_success=on_success,
            on_failure=failed,
        )
        return True

    def ask(
        self,
        feature: str,
        prompt: str,
        chunks: list[str] | None,
        *,
        on_done: Callable[[str, GatewayQuota | None], None],
        on_error: Callable[[str], None],
        language: str = "",
        requires: tuple[str, ...] = ("text",),
    ) -> threading.Event:
        """Run one AI request. Returns at once; answers on the UI thread.

        *on_error* receives a finished sentence, never an exception. Every
        failure in the client is already a coded error whose text was written
        for a person to hear, so rendering one at a user is the whole job.
        *language* is Translate's target language; *requires* is what the
        request needs of the connection in use (GATE-CAPS).
        """
        stop = threading.Event()
        connection = self.request_connection(requires, lambda said: _call_after(on_error, said))
        if not connection:
            return stop  # not ready, cannot do it, or the route changed and they said No

        def build_work(route: str) -> Callable[..., tuple[str, GatewayQuota | None]]:
            if route == COPILOT:
                return self._copilot_ask_work(feature, prompt, chunks, language, stop)
            if route == CHATGPT:
                from quill.core.ai.chatgpt_ai_help import ask_with_chatgpt

                account = self.chatgpt

                def plan_work(**_kwargs: Any) -> tuple[str, GatewayQuota | None]:
                    answer = ask_with_chatgpt(
                        account, feature, prompt, chunks, language=language or "English"
                    )
                    return answer, None

                return plan_work
            if route == OWN_KEY:
                from quill.core.ai.own_key import ask_with_own_key

                model, provider = self.connection_model(OWN_KEY), self.own_key_provider

                def key_work(**_kwargs: Any) -> tuple[str, GatewayQuota | None]:
                    answer = ask_with_own_key(
                        feature,
                        prompt,
                        chunks,
                        model=model,
                        language=language or "English",
                        provider=provider,
                        cancel=stop,
                    )
                    return answer, None

                return key_work
            client = self.client()

            def free_work(**_kwargs: Any) -> tuple[str, GatewayQuota | None]:
                return client.ask(feature, prompt, chunks, language=language)

            return free_work

        work = build_work(connection)

        def done(_name: str, result: Any) -> None:
            def deliver() -> None:
                if stop.is_set():
                    return
                text, quota = result
                on_done(as_text(text), quota)  # chart-like content stays text (decision 13)

            _call_after(deliver)

        def failed(_name: str, error: BaseException) -> None:
            said = self._failure_sentence(error, connection)

            def deliver() -> None:
                if stop.is_set():
                    return
                if self._auto_retry(
                    error=error,
                    failed_connection=connection,
                    requires=requires,
                    build_work=build_work,
                    operation="ask",
                    on_success=done,
                    on_error=on_error,
                    stop=stop,
                ):
                    return
                on_error(said)

            _call_after(deliver)

        _submit("quill-ai-ask", work, on_success=done, on_failure=failed)
        return stop

    def cancel(self, request: threading.Event | None) -> bool:
        """Cancel only *request*, leaving requests from other windows untouched."""
        if request is None or request.is_set():
            return False
        request.set()
        return True

    def converse(
        self,
        prompt: str,
        chunks: list[str] | None,
        history: list[dict[str, str]],
        *,
        on_done: Callable[[str, GatewayQuota | None, int], None],
        on_error: Callable[[str], None],
        requires: tuple[str, ...] = ("text",),
    ) -> threading.Event:
        """One conversation turn (:mod:`quill.core.ai.hosted_chat`). Returns at
        once; answers on the UI thread with ``(reply, quota, turns_dropped)``.

        With an own key the history goes to OpenAI as it is -- the window has
        already trimmed it only as far as the model can read -- and nothing is
        counted; on QUILL's service the service may trim further and says by
        how many turns.
        """
        stop = threading.Event()
        connection = self.request_connection(requires, lambda said: _call_after(on_error, said))
        if not connection:
            return stop

        def build_work(route: str) -> Callable[..., tuple[str, GatewayQuota | None, int]]:
            if route == COPILOT:
                return self._copilot_converse_work(prompt, chunks, history, stop)
            if route == CHATGPT:
                from quill.core.ai.chatgpt_ai_help import converse_with_chatgpt

                account = self.chatgpt

                def plan_work(**_kwargs: Any) -> tuple[str, GatewayQuota | None, int]:
                    return converse_with_chatgpt(account, prompt, chunks, history), None, 0

                return plan_work
            if route == OWN_KEY:
                from quill.core.ai.own_key import ask_with_own_key

                model, provider = self.connection_model(OWN_KEY), self.own_key_provider

                def key_work(**_kwargs: Any) -> tuple[str, GatewayQuota | None, int]:
                    reply = ask_with_own_key(
                        "chat",
                        prompt,
                        chunks,
                        model=model,
                        history=history,
                        provider=provider,
                        cancel=stop,
                    )
                    return reply, None, 0

                return key_work
            client = self.client()

            def free_work(**_kwargs: Any) -> tuple[str, GatewayQuota | None, int]:
                return client.converse(prompt, chunks, history)

            return free_work

        work = build_work(connection)

        def done(_name: str, result: Any) -> None:
            def deliver() -> None:
                if stop.is_set():
                    return
                text, quota, dropped = result
                on_done(as_text(text), quota, dropped)

            _call_after(deliver)

        def failed(_name: str, error: BaseException) -> None:
            said = self._failure_sentence(error, connection)

            def deliver() -> None:
                if stop.is_set():
                    return
                if self._auto_retry(
                    error=error,
                    failed_connection=connection,
                    requires=requires,
                    build_work=build_work,
                    operation="converse",
                    on_success=done,
                    on_error=on_error,
                    stop=stop,
                ):
                    return
                on_error(said)

            _call_after(deliver)

        _submit("quill-ai-converse", work, on_success=done, on_failure=failed)
        return stop

    def describe_image(
        self,
        path: Any,
        question: str,
        *,
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
        requires: tuple[str, ...] = ("text", "pictures"),
    ) -> None:
        """Ask About an Image on the plan, Copilot or a seeing own key; answers on the
        UI thread. GATE-CAPS refuses elsewhere. A bad file is the client's sentence."""
        connection = self.request_connection(requires, lambda said: _call_after(on_error, said))
        if not connection:
            return

        def build_work(route: str) -> Callable[..., str]:
            if route == COPILOT:
                return self._copilot_image_work(path, question)
            if route == CHATGPT:
                from quill.core.ai.chatgpt_ai_help import describe_image_with_chatgpt

                account = self.chatgpt

                def plan_work(**_kwargs: Any) -> str:
                    return describe_image_with_chatgpt(account, path, question)

                return plan_work
            from quill.core.ai.own_key import describe_image_with_own_key

            provider, model = self.own_key_provider, self.connection_model(OWN_KEY)

            def key_work(**_kwargs: Any) -> str:
                return describe_image_with_own_key(path, question, provider=provider, model=model)

            return key_work

        work = build_work(connection)

        def done(_name: str, text: Any) -> None:
            _call_after(on_done, as_text(str(text)))

        def failed(_name: str, error: BaseException) -> None:
            if isinstance(error, ValueError):
                _call_after(on_error, str(error))
                return
            said = self._failure_sentence(error, connection)

            def deliver() -> None:
                if self._auto_retry(
                    error=error,
                    failed_connection=connection,
                    requires=requires,
                    build_work=build_work,
                    operation="image",
                    on_success=done,
                    on_error=on_error,
                ):
                    return
                on_error(said)

            _call_after(deliver)

        _submit("quill-ai-image", work, on_success=done, on_failure=failed)
