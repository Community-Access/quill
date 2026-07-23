"""High-level writing assistant built on an AIBackend.

Provides the common writing operations (rewrite, summarize, continue, fix
grammar, change tone) plus access to the Quill command tools. Defaults to the
Apple Foundation Models backend on macOS; pass a different backend elsewhere.
Calls are blocking — the UI should run them off the main thread.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from quill.core.ai.backend import AIBackend, ContextWindowExceeded
from quill.core.ai.tools import AITool, build_tools_from_registry, run_tool

if TYPE_CHECKING:
    from quill.core.ai.agent import AgentDecision

logger = logging.getLogger(__name__)

# Max characters of input we send in one call; larger inputs are chunked.
_CHUNK_CHARS = 4000
# Hard cap on a single chat MESSAGE/instruction sent to the model. Without this,
# pasting a huge document into the chat blows past the context window and the
# on-device model hangs (UI appears to lock up). The document context is trimmed
# separately via _CONTEXT_BUDGETS.
_MAX_MESSAGE_CHARS = 4000
# Document-context budgets to try (chars), shrinking until it fits the window.
_CONTEXT_BUDGETS = (6000, 3000, 1200, 0)

# Terms that signal the user actually wants to change the document. The
# on-device model sometimes routes a greeting or a question to insert/replace
# (offering to paste a chat reply into the document). Without one of these terms
# we refuse to insert/replace and answer in chat instead. See _has_document_intent.
# Action verbs only — NOT document nouns. A question like "how do I center a
# heading?" mentions a noun ("heading") but is conversational; keying on verbs
# keeps it in chat while still catching real requests ("write…", "add…").
_DOC_INTENT_TERMS = (
    "write",
    "add ",
    "insert",
    "draft",
    "compose",
    "continue",
    "append",
    "generate",
    "create",
    "outline",
    "expand",
    "elaborate",
    "rewrite",
    "rephrase",
    "reword",
    "revise",
    "edit ",
    "fix ",
    "correct",
    "shorten",
    "lengthen",
    "simplify",
    "improve",
    "polish",
    "translate",
    "summarize",
    "make it",
    "make this",
    "make the",
    "turn this",
    "turn it",
    "replace",
    "reformat",
    "proofread",
    "tighten",
)


def _has_document_intent(message: str) -> bool:
    """True if the message explicitly asks to write to or edit the document."""
    low = (message or "").lower()
    return any(term in low for term in _DOC_INTENT_TERMS)


_OPERATION_PROMPTS: dict[str, str] = {
    "rewrite": "Rewrite the following text to be clear and well written. "
    "Return only the rewritten text, with no preamble:\n\n{text}",
    "summarize": "Summarize the following text concisely. Return only the summary:\n\n{text}",
    "continue": "Continue writing naturally from the following text. "
    "Return only the new continuation:\n\n{text}",
    "fix_grammar": "Correct the spelling and grammar of the following text. "
    "Return only the corrected text:\n\n{text}",
    "shorten": "Make the following text more concise while keeping its meaning. "
    "Return only the shortened text:\n\n{text}",
    "structure": "The following is raw text recognized from an image or PDF by OCR. "
    "Reflow it into clean, well-structured Markdown: join lines that were broken "
    "mid-sentence by the scan, group paragraphs, and infer headings, lists, and "
    "tables from the layout where they are obvious. Preserve all of the original "
    "wording and meaning exactly — do not summarize, add, or invent content. "
    "Return only the Markdown, with no preamble:\n\n{text}",
    "reading_order": "The following is text extracted from a document whose reading "
    "order is jumbled — for example a multi-column PDF, a page with sidebars or text "
    "boxes, or lines pulled out of sequence. Reconstruct the correct reading order: "
    "put the text back into the order a person would naturally read it, merge columns "
    "into a single flow, join lines broken mid-sentence, and group paragraphs. Infer "
    "headings, lists, and tables from the layout where they are obvious, and return "
    "clean Markdown. Preserve all of the original wording and meaning exactly — do not "
    "summarize, add, remove, or invent content. Return only the Markdown, with no "
    "preamble:\n\n{text}",
}


def make_default_backend() -> AIBackend:
    """Pick the best available backend for this platform.

    When the user has configured an AI connection (AI-13), the selected provider
    actually responds: a saved connection that is not "off" and reports itself
    available routes generation to ``ProviderChatBackend``. Otherwise generation
    falls back to the bundled on-device model: macOS with Apple Intelligence ->
    Foundation Models; everywhere else -> llama.cpp CPU.
    """
    import sys

    # Honor an explicitly configured provider first (AI-13). The presence of the
    # connection file marks a deliberate user choice; an unconfigured install has
    # no file and falls through to the bundled local backend.
    try:
        from quill.core.assistant_ai import (
            assistant_connection_path,
            load_assistant_connection_settings,
        )

        if assistant_connection_path().exists():
            settings = load_assistant_connection_settings()
            if settings.provider.strip().lower() != "off":
                from quill.core.ai.provider_backend import ProviderChatBackend

                backend = ProviderChatBackend(settings)
                if backend.is_available()[0]:
                    return backend
    except Exception as exc:  # noqa: BLE001 - any failure falls back to the local model
        logger.warning("Configured AI provider probe failed; falling back to local model: %s", exc)

    # Check the simple chat settings (ai_chat_default_provider / ai_chat_default_model).
    # This path is set by the inline setup strip in AskQuillChatDialog.
    try:
        from quill.core.settings import load_settings

        _s = load_settings()
        _provider = getattr(_s, "ai_chat_default_provider", "") or ""
        _model = (
            getattr(_s, "ai_prompt_default_model", "")
            or getattr(_s, "ai_chat_default_model", "")
            or ""
        )
        if _provider and _model:
            from quill.core.ai.provider_backend import SimpleChatBackend

            _backend = SimpleChatBackend(_provider, _model)
            if _backend.is_available()[0]:
                return _backend
    except Exception as exc:  # noqa: BLE001
        logger.warning("Simple chat settings backend probe failed: %s", exc)

    if sys.platform == "darwin":
        try:
            from quill.core.ai.foundation_models import FoundationModelsBackend

            fm = FoundationModelsBackend()
            if fm.is_available()[0]:
                return fm
        except Exception as error:  # noqa: BLE001
            logger.warning("Foundation Models backend probe failed: %s", error)
    from quill.core.ai.llama_cpp_backend import LlamaCppBackend

    return LlamaCppBackend()


class Assistant:
    def __init__(self, backend: AIBackend | None = None) -> None:
        if backend is None:
            backend = make_default_backend()
        self.backend = backend
        self._style_preamble = ""
        self._instructions_preamble = ""

    def set_style_preamble(self, preamble: str) -> None:
        """Condition generation on the user's writing style (empty to disable)."""
        self._style_preamble = preamble or ""

    def set_instructions_preamble(self, preamble: str) -> None:
        """Pin the user's durable writing instructions (AI-21; empty to disable)."""
        self._instructions_preamble = preamble or ""

    def _wrap(self, prompt: str) -> str:
        # Instructions (explicit user rules) lead, then the trained style
        # (voice), then the task. Both are visible, user-owned conditioning.
        segments = [
            segment for segment in (self._instructions_preamble, self._style_preamble) if segment
        ]
        if not segments:
            return prompt
        return "\n\n".join([*segments, prompt])

    def is_available(self) -> tuple[bool, str | None]:
        return self.backend.is_available()

    def available_operations(self) -> list[str]:
        return list(_OPERATION_PROMPTS)

    def transform(self, operation: str, text: str) -> str:
        if operation not in _OPERATION_PROMPTS:
            raise ValueError(f"Unknown operation: {operation}")
        template = _OPERATION_PROMPTS[operation]
        if len(text) <= _CHUNK_CHARS:
            return self.backend.respond(self._wrap(template.format(text=text)))
        # Input is larger than the window: process in chunks.
        chunks = _split_into_chunks(text, _CHUNK_CHARS)
        pieces = [self.backend.respond(self._wrap(template.format(text=c))) for c in chunks]
        if operation == "summarize":
            # Map-reduce: summarize the combined chunk summaries.
            combined = "\n\n".join(pieces)
            if len(combined) > _CHUNK_CHARS:
                combined = combined[:_CHUNK_CHARS]
            return self.backend.respond(self._wrap(template.format(text=combined)))
        return "\n".join(pieces)

    def change_tone(self, text: str, tone: str) -> str:
        prompt = (
            f"Rewrite the following text in a {tone} tone. "
            f"Return only the rewritten text:\n\n{text}"
        )
        return self.backend.respond(self._wrap(prompt))

    def ask(self, prompt: str) -> str:
        return self.backend.respond(self._wrap(prompt))

    def _respond_fitting(self, build_prompt: Callable[[int], str]) -> str:
        """Try the prompt with shrinking document context until it fits the window."""
        last_error: Exception | None = None
        for budget in _CONTEXT_BUDGETS:
            try:
                return self.backend.respond(self._wrap(build_prompt(budget)))
            except ContextWindowExceeded as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        return self.backend.respond(self._wrap(build_prompt(0)))

    def _clamp_message(self, message: str) -> str:
        """Bound a single user message so a huge paste can't exceed the model's
        context window and hang inference."""
        message = (message or "").strip()
        if len(message) <= _MAX_MESSAGE_CHARS:
            return message
        return (
            message[:_MAX_MESSAGE_CHARS]
            + "\n\n[Message truncated to fit the on-device model's limit.]"
        )

    def _document_context(self, document_text: str, budget: int) -> str:
        document_text = (document_text or "").strip()
        if not document_text or budget <= 0:
            return ""
        return f"\n\nThe current document:\n{document_text[:budget]}"

    def answer(self, user_message: str, document_text: str = "") -> str:
        """A full chat answer (uses the document as context, trimmed to fit)."""
        user_message = self._clamp_message(user_message)
        return self._respond_fitting(
            lambda budget: f"{user_message}{self._document_context(document_text, budget)}"
        )

    def answer_stream(
        self,
        user_message: str,
        document_text: str = "",
        on_delta: Callable[[str], None] | None = None,
    ) -> str:
        """Stream a chat answer, calling ``on_delta`` per fragment (AI-1, AI-14).

        Returns the complete answer. Streaming backends deliver real incremental
        tokens; backends that cannot stream emit the whole answer once via the
        :meth:`AIBackend.respond_stream` fallback, so callers always get a clean
        degraded experience. Document context shrinks until it fits the window,
        exactly like :meth:`answer`.
        """
        emit = on_delta or (lambda _fragment: None)
        user_message = self._clamp_message(user_message)

        def build(budget: int) -> str:
            return f"{user_message}{self._document_context(document_text, budget)}"

        last_error: Exception | None = None
        for budget in _CONTEXT_BUDGETS:
            try:
                return self.backend.respond_stream(self._wrap(build(budget)), emit)
            except ContextWindowExceeded as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        return self.backend.respond_stream(self._wrap(build(0)), emit)

    def write_for_document(self, user_message: str, document_text: str = "") -> str:
        """Generate substantial content to insert; returns only the text."""
        user_message = self._clamp_message(user_message)
        return self._respond_fitting(
            lambda budget: (
                "Write a complete, well-structured piece for the user's document — use "
                "multiple paragraphs and headings where appropriate, not just a title or "
                "a single line. Return ONLY the text to insert, with no preamble, labels, "
                f"or quotation marks.\n\nRequest: {user_message}"
                f"{self._document_context(document_text, budget)}"
            )
        )

    def rewrite_selection(self, user_message: str, selection_text: str) -> str:
        """Apply an instruction to the selected text; returns only the result.

        Large selections are processed in chunks so they never exceed the window.
        """
        instruction = (
            "Apply this instruction to the text and return ONLY the resulting text, "
            f"with no preamble.\n\nInstruction: {self._clamp_message(user_message)}\n\nText:\n"
        )
        if len(selection_text) <= _CHUNK_CHARS:
            return self.backend.respond(self._wrap(instruction + selection_text))
        chunks = _split_into_chunks(selection_text, _CHUNK_CHARS)
        return "\n".join(self.backend.respond(self._wrap(instruction + c)) for c in chunks)

    def tools(self, registry: object, feature_manager: object | None = None) -> list[AITool]:
        return build_tools_from_registry(registry, feature_manager)

    def run_tool(self, registry: object, name: str) -> None:
        run_tool(registry, name)

    def decide(
        self, user_message: str, document_text: str, tool_ids: Iterable[str]
    ) -> AgentDecision:
        """Agentic decision: answer / insert / replace / run a tool.

        Falls back to a plain text answer if the backend can't make structured
        decisions.
        """
        from quill.core.ai.agent import AgentDecision

        user_message = self._clamp_message(user_message)
        decide = getattr(self.backend, "decide", None)
        if decide is None:
            # No structured decider: treat as a plain chat answer. Leave the
            # text empty so the caller generates it (streaming-friendly) instead
            # of paying for a second, discarded blocking generation here.
            return AgentDecision(action="answer", text="")
        decision: AgentDecision = decide(
            user_message, document_text, tuple(tool_ids), self._style_preamble
        )
        # Guard against the model turning a plain chat message (a greeting, a
        # question) into a document edit. If the user didn't actually ask to
        # write or edit anything, answer in chat instead of offering an insert.
        if decision.action in ("insert", "replace") and not _has_document_intent(user_message):
            return AgentDecision(action="answer", text=decision.text)
        return decision


def _split_into_chunks(text: str, max_chars: int) -> list[str]:
    """Split text into chunks no larger than max_chars, preferring paragraph
    then line then hard boundaries."""
    if max_chars <= 0:
        raise ValueError("max_chars must be a positive integer")
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        block = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(block) <= max_chars:
            current = block
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(paragraph) <= max_chars:
            current = paragraph
        else:
            # Paragraph itself too big: hard-split.
            for i in range(0, len(paragraph), max_chars):
                piece = paragraph[i : i + max_chars]
                if len(piece) == max_chars:
                    chunks.append(piece)
                else:
                    current = piece
    if current:
        chunks.append(current)
    return chunks
