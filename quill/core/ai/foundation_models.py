"""Apple Foundation Models backend (macOS 26+, Apple Silicon, Apple Intelligence).

Uses the official ``apple-fm-sdk`` Python bindings. On-device, free, no model
download, no GPU server. Degrades gracefully when unavailable. Supports both
plain text responses and an agentic ``decide`` step (guided generation) that
chooses to answer, insert, replace, or run a Quill command.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, cast

from quill.core.ai.agent import ACTIONS, AgentDecision
from quill.core.ai.backend import AIBackend, ContextWindowExceeded

_DECIDE_INSTRUCTIONS = (
    "You are Quill's editor assistant. Decide how to handle the user's request about "
    "the single document they are editing. action=answer replies in chat; "
    "action=insert provides new text to put at the cursor; action=replace rewrites the "
    "selected text; action=run runs ONE listed tool by its exact id. Only set tool when "
    "action is run.\n"
    "Default to action=answer. Greetings, questions, and conversation ('hello', "
    "'what does this say?', 'can you help?') are answered in chat — they do NOT modify "
    "the document. Choose insert or replace ONLY when the user clearly asks you to add "
    "or change text in the document (e.g. 'write an intro', 'add a conclusion', 'rewrite "
    "this'). When unsure, answer in chat."
)


class FoundationModelsBackend(AIBackend):
    name = "Apple Foundation Models"
    is_local = True

    def __init__(self) -> None:
        self._fm = None
        self._decision_types: dict[tuple[str, ...], object] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._loop_lock = threading.Lock()

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        with self._loop_lock:
            if self._loop is not None and self._loop.is_running():
                return self._loop
            loop = asyncio.new_event_loop()

            def _run() -> None:
                loop.run_forever()

            thread = threading.Thread(target=_run, daemon=True, name="fm-event-loop")
            thread.start()
            self._loop = loop
            self._loop_thread = thread
            return loop

    def _sdk(self) -> Any:
        if self._fm is None:
            import apple_fm_sdk as fm  # type: ignore[import-not-found]

            self._fm = fm
        return self._fm

    def is_available(self) -> tuple[bool, str | None]:
        try:
            fm = self._sdk()
        except ImportError:
            return False, "apple-fm-sdk is not installed"
        try:
            ok, reason = fm.SystemLanguageModel().is_available()
            if ok:
                return True, None
            return False, str(reason) if reason else "Apple Intelligence is not available"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    def _is_context_error(self, exc: Exception) -> bool:
        name = type(exc).__name__.lower()
        return "contextwindow" in name or "context window" in str(exc).lower()

    def respond(self, prompt: str) -> str:
        fm = self._sdk()

        async def _go() -> str:
            session = fm.LanguageModelSession()
            return cast("str", await session.respond(prompt))

        try:
            future = asyncio.run_coroutine_threadsafe(_go(), self._get_loop())
            return future.result()
        except Exception as exc:  # noqa: BLE001
            if self._is_context_error(exc):
                raise ContextWindowExceeded(str(exc)) from exc
            raise

    # --- agentic decision (guided generation) ---------------------------------

    def _decision_type(self, tool_ids: tuple[str, ...]) -> Any:
        cached = self._decision_types.get(tool_ids)
        if cached is not None:
            return cached
        fm = self._sdk()
        namespace = {
            "__annotations__": {"action": str, "text": str, "tool": str},
            "action": fm.guide("What to do", anyOf=list(ACTIONS)),
            "text": fm.guide("Text for answer/insert/replace; empty when running a tool"),
            "tool": fm.guide(
                "Exact command id when action is run; otherwise empty",
                anyOf=["", *tool_ids],
            ),
        }
        decision_cls = type("QuillAgentDecision", (), namespace)
        decision_cls = fm.generable("How Quill should handle the user's request")(decision_cls)
        self._decision_types[tool_ids] = decision_cls
        return decision_cls

    def decide(
        self,
        user_message: str,
        document_text: str,
        tool_ids: tuple[str, ...],
        style_preamble: str = "",
    ) -> AgentDecision:
        decision_type = self._decision_type(tuple(tool_ids))
        fm = self._sdk()
        instructions = _DECIDE_INSTRUCTIONS
        if style_preamble:
            instructions = f"{_DECIDE_INSTRUCTIONS}\n\n{style_preamble}"

        def run(budget: int) -> Any:
            context = document_text[:budget]

            async def _go() -> Any:
                session = fm.LanguageModelSession(instructions=instructions)
                return await session.respond(
                    f"Request: {user_message}\n\nDocument:\n{context}",
                    generating=decision_type,
                )

            return asyncio.run_coroutine_threadsafe(_go(), self._get_loop()).result()

        raw = None
        for budget in (6000, 3000, 1200, 0):
            try:
                raw = run(budget)
                break
            except Exception as exc:  # noqa: BLE001
                if self._is_context_error(exc) and budget > 0:
                    continue
                if self._is_context_error(exc):
                    # Even with no document context it won't fit — answer plainly.
                    return AgentDecision(action="answer", text="")
                raise
        if raw is None:
            return AgentDecision(action="answer", text="")
        action = raw.action if raw.action in ACTIONS else "answer"
        tool = raw.tool if action == "run" and raw.tool in tool_ids else ""
        if action == "run" and not tool:
            action = "answer"
        return AgentDecision(action=action, text=raw.text or "", tool=tool)
