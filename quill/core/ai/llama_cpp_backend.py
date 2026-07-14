"""llama.cpp backend (CPU, in-process) for Windows and other non-macOS systems.

Uses ``llama-cpp-python`` to run a local GGUF model entirely on the CPU — no
GPU, no server, no cloud (per issue #40). Optional dependency: if it or a model
isn't present, it reports unavailable and the UI degrades gracefully.

Model resolution order:
  1. ``QUILL_LLAMA_MODEL`` environment variable (path to a .gguf), then
  2. the first ``*.gguf`` found in ``<app data>/models``.
Recommended default model: Phi-4-mini (Q4); Llama 3.2 1B for low-end machines.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from quill.core import lifecycle_service
from quill.core.ai.agent import ACTIONS, AgentDecision
from quill.core.ai.backend import AIBackend, ContextWindowExceeded
from quill.core.ai.model_manager import choose_model_spec, ensure_model, existing_model

_N_CTX = 4096
_MAX_TOKENS = 1024
_ProgressCallback = Callable[[int, int], None]

# STATUS_ILLEGAL_INSTRUCTION — the prebuilt llama.cpp used a CPU instruction
# (e.g. AVX2) the CPU/emulator doesn't support.
_ILLEGAL_INSTRUCTION = -1073741795


def _cpu_error_message(exc: OSError) -> str:
    if getattr(exc, "winerror", None) == _ILLEGAL_INSTRUCTION:
        return (
            "The local AI model couldn't run on this CPU. The prebuilt llama.cpp "
            "needs AVX2, which isn't available here (for example, x64 emulation on "
            "Windows-on-ARM / Parallels on Apple Silicon). Run on a machine with AVX2 "
            "support, or install a no-AVX / native build of llama-cpp-python."
        )
    return f"Failed to run the local AI model: {exc}"


def _format_native_load_error(exc: OSError) -> str:
    error_code = getattr(exc, "winerror", None)
    if not isinstance(error_code, int):
        error_code = getattr(exc, "errno", None)
    if isinstance(error_code, int) and error_code == _ILLEGAL_INSTRUCTION:
        return (
            "The local AI model could not run on this CPU. The llama.cpp build uses "
            "an unsupported instruction set (for example AVX2, Windows error 0xc000001d). "
            "Use a CPU-compatible "
            "build or disable AI on this machine."
        )
    if isinstance(error_code, int):
        code = error_code & 0xFFFFFFFF
        return (
            "llama-cpp-python failed to load native code on this machine "
            f"(Windows error 0x{code:08x}). Install a CPU-compatible build or disable AI."
        )
    return (
        "llama-cpp-python failed to load native code on this machine. "
        "Install a CPU-compatible build or disable AI."
    )


def _extract_message_content(response: object) -> str:
    """Safely pull the assistant text out of a chat-completion response.

    A malformed or version-mismatched llama.cpp payload must not crash with a
    raw ``KeyError``/``IndexError``/``TypeError``; surface a friendly error.
    """
    try:
        choices = response["choices"]  # type: ignore[index]
        first = choices[0]
        content = first["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "The local AI model returned an unexpected response shape. "
            "This can happen after a llama-cpp-python upgrade; reinstall a "
            "compatible version or disable AI on this machine."
        ) from exc
    if content is None:
        return ""
    return str(content).strip()


class LlamaCppBackend(AIBackend):
    name = "llama.cpp (local CPU)"

    def __init__(
        self,
        model_path: str | None = None,
        n_ctx: int = _N_CTX,
        progress: _ProgressCallback | None = None,
    ) -> None:
        self._model_path = model_path
        self._n_ctx = n_ctx
        self._progress = progress
        self._llm: Any = None

    def _load(self) -> Any:
        if self._llm is None:
            try:
                from llama_cpp import Llama  # type: ignore[import-not-found]
            except OSError as exc:
                raise RuntimeError(_format_native_load_error(exc)) from exc

            # Resolve (and download the RAM-appropriate model the first time).
            path = self._model_path or ensure_model(self._progress)
            self._model_path = path
            # Low-resource mode may evict another loaded engine to make room first.
            lifecycle_service.reserve("llm")
            try:
                self._llm = Llama(model_path=path, n_ctx=self._n_ctx, verbose=False)
            except OSError as exc:
                raise RuntimeError(_format_native_load_error(exc)) from exc
            lifecycle_service.note_loaded("llm", self.unload)
        lifecycle_service.touch("llm")
        return self._llm

    def unload(self) -> None:
        """Free the loaded model (idle-unload / low-resource eviction).

        The next completion reloads it (the warm cost). Safe to call when nothing is
        loaded. Registered with the lifecycle service so an idle sweep can call it.
        """
        self._llm = None
        lifecycle_service.note_unloaded("llm")

    def is_available(self) -> tuple[bool, str | None]:
        try:
            import llama_cpp  # noqa: F401
        except ImportError:
            return False, "llama-cpp-python is not installed (pip install llama-cpp-python)"
        except OSError as exc:
            return False, _format_native_load_error(exc)
        # A model is auto-downloaded (RAM-tiered) on first use if none is present.
        return True, None

    def model_status(self) -> str:
        """Human-readable note about which model is/will be used."""
        found = self._model_path or existing_model()
        if found:
            return f"Using model: {found}"
        spec = choose_model_spec()
        return f"Will download {spec.name} on first use."

    def _complete(self, messages: list[dict], response_format: dict | None = None) -> str:
        llm = self._load()
        kwargs: dict = {"messages": messages, "max_tokens": _MAX_TOKENS}
        if response_format is not None:
            kwargs["response_format"] = response_format
        try:
            out = llm.create_chat_completion(**kwargs)
        except ValueError as exc:
            if "context" in str(exc).lower() or "token" in str(exc).lower():
                raise ContextWindowExceeded(str(exc)) from exc
            raise
        except OSError as exc:
            raise RuntimeError(_cpu_error_message(exc)) from exc
        return _extract_message_content(out)

    def respond(self, prompt: str) -> str:
        return self._complete([{"role": "user", "content": prompt}])

    def decide(
        self,
        user_message: str,
        document_text: str,
        tool_ids: tuple[str, ...],
        style_preamble: str = "",
    ) -> AgentDecision:
        # JSON-constrained decision (llama.cpp supports JSON response_format).
        system = (
            "You are Quill's editor assistant. Decide how to handle the user's request "
            "about the single document they are editing. Reply with a JSON object: "
            '{"action": one of ' + json.dumps(list(ACTIONS)) + ', "text": string, "tool": '
            "string}. action=answer replies in chat; insert=new text for the cursor; "
            "replace=rewrites the selection; run=run ONE tool id. tool must be one of: "
            + json.dumps(list(tool_ids))
            + " (empty unless action is run). "
            "Default to action=answer: greetings, questions, and conversation are "
            "answered in chat and do NOT change the document. Use insert or replace ONLY "
            "when the user clearly asks to add or change document text. When unsure, answer."
        )
        if style_preamble:
            system = f"{system}\n\n{style_preamble}"
        for budget in (6000, 3000, 1200, 0):
            context = document_text[:budget]
            try:
                raw = self._complete(
                    [
                        {"role": "system", "content": system},
                        {
                            "role": "user",
                            "content": f"Request: {user_message}\n\nDocument:\n{context}",
                        },
                    ],
                    response_format={"type": "json_object"},
                )
                break
            except ContextWindowExceeded:
                if budget == 0:
                    return AgentDecision(action="answer", text="")
                continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return AgentDecision(action="answer", text=raw)
        action = data.get("action") if data.get("action") in ACTIONS else "answer"
        tool = data.get("tool", "") if action == "run" and data.get("tool") in tool_ids else ""
        if action == "run" and not tool:
            action = "answer"
        return AgentDecision(action=action, text=str(data.get("text") or ""), tool=tool)
