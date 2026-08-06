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
from quill.core.ai.quality_filter import (
    find_quality_issues,
    negative_examples_block,
    retry_instruction,
)
from quill.core.ai.tools import AITool, build_tools_from_registry, run_tool
from quill.core.ai.two_pass import DEFAULT_WORD_BUDGET, observe_prompt, rewrite_prompt

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


#: Generative operations whose output the small-local-model quality shaping
#: (#1319) applies to: the model *writes* here, so negative-example prompting
#: and the hedging/filler post-filter help. The faithful transforms
#: (``fix_grammar``, ``structure``, ``reading_order``) are deliberately excluded
#: -- they must preserve the source exactly, so a "banned word" that is in the
#: source must never trigger a rewrite.
_GENERATIVE_OPS: frozenset[str] = frozenset({"rewrite", "summarize", "continue", "shorten"})


#: Set by :func:`make_default_backend` when resolution fell back past a
#: provider the user explicitly configured; read via :func:`last_backend_note`.
#: The rule (error specificity, PRD 5.1c-ES): never silently give the user a
#: different engine than the one they chose — the UI announces this note.
_LAST_BACKEND_NOTE = ""


def last_backend_note() -> str:
    """The user-facing sentence for the last silent backend fallback, or ""."""
    return _LAST_BACKEND_NOTE


def _note_backend_fallback(provider: str) -> None:
    global _LAST_BACKEND_NOTE
    name = provider.strip() or "your configured AI provider"
    _LAST_BACKEND_NOTE = (
        f"{name} was not available, so Quill is using the on-device model "
        "instead. Check your provider and key in the AI settings to restore it."
    )


def make_default_backend() -> AIBackend:
    """Pick the best available backend for this platform.

    When the user has configured an AI connection (AI-13), the selected provider
    actually responds: a saved connection that is not "off" and reports itself
    available routes generation to ``ProviderChatBackend``. Otherwise generation
    falls back to the bundled on-device model: macOS with Apple Intelligence ->
    Foundation Models; everywhere else -> llama.cpp CPU. A fallback past a
    provider the user explicitly configured is recorded via
    :func:`last_backend_note` so the UI can say so instead of quietly answering
    with a different engine.
    """
    import sys

    global _LAST_BACKEND_NOTE
    _LAST_BACKEND_NOTE = ""

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
                _note_backend_fallback(settings.provider)
    except Exception as exc:  # noqa: BLE001 - any failure falls back to the local model
        logger.warning("Configured AI provider probe failed; falling back to local model: %s", exc)
        _note_backend_fallback("")

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
                _LAST_BACKEND_NOTE = ""
                return _backend
            _note_backend_fallback(_provider)
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
        #: When default resolution fell back past a configured provider, the
        #: sentence the UI must speak (never silently swap engines).
        self.backend_note = ""
        if backend is None:
            backend = make_default_backend()
            self.backend_note = last_backend_note()
        self.backend = backend
        self._style_preamble = ""
        self._instructions_preamble = ""
        #: Two-pass observe-then-rewrite for summarize on a local model (#1320):
        #: pass 1 extracts observations, pass 2 rewrites them under a word budget
        #: without the source, cutting hallucination. Defaults on but only ever
        #: fires on a local backend; the UI's single-pass escape hatch flips this
        #: off to preserve speed on slow CPUs.
        self.two_pass_summarize = True
        self.summary_word_budget = DEFAULT_WORD_BUDGET
        #: After answer()/answer_stream()/write_for_document(): a user-facing
        #: sentence describing any silent trimming that shaped the request
        #: ("The answer used the first N of the document's M characters."),
        #: or "". The UI announces it so the user is never quietly given an
        #: answer over less context than they believe was sent (error
        #: specificity: never silently deliver less than was asked).
        self.last_context_note = ""
        self._last_fit_budget = 0

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

    def _respond_quality(self, prompt: str, *, shape: bool) -> str:
        """Respond, applying small-local-model quality shaping when ``shape``.

        On a local backend (#1319): prepend negative worked examples to teach
        concision, then run the deterministic hedging/filler post-filter on the
        output and, on a hit, do exactly one cheap retry naming the offending
        phrases. Cloud backends and faithful transforms skip all of this and
        get the plain response, byte-for-byte as before.
        """
        local = shape and bool(getattr(self.backend, "is_local", False))
        if local:
            prompt = f"{negative_examples_block()}\n\n{prompt}"
        result = self.backend.respond(prompt)
        if local:
            issues = find_quality_issues(result)
            if issues:
                revised = self.backend.respond(
                    f"{retry_instruction(issues)}\n\nYour previous answer:\n{result}"
                )
                if revised.strip():
                    return revised
        return result

    def is_available(self) -> tuple[bool, str | None]:
        return self.backend.is_available()

    def available_operations(self) -> list[str]:
        return list(_OPERATION_PROMPTS)

    def transform(self, operation: str, text: str) -> str:
        if operation not in _OPERATION_PROMPTS:
            raise ValueError(f"Unknown operation: {operation}")
        template = _OPERATION_PROMPTS[operation]
        shape = operation in _GENERATIVE_OPS
        if len(text) <= _CHUNK_CHARS:
            if operation == "summarize":
                return self._summarize(text)
            return self._respond_quality(self._wrap(template.format(text=text)), shape=shape)
        # Input is larger than the window: process in chunks.
        chunks = _split_into_chunks(text, _CHUNK_CHARS)
        pieces = [
            self._respond_quality(self._wrap(template.format(text=c)), shape=shape) for c in chunks
        ]
        if operation == "summarize":
            # Map-reduce: summarize the combined chunk summaries.
            combined = "\n\n".join(pieces)
            if len(combined) > _CHUNK_CHARS:
                combined = combined[:_CHUNK_CHARS]
            return self._summarize(combined)
        return "\n".join(pieces)

    def _use_two_pass_summarize(self) -> bool:
        # Only ever on a local backend; cloud models don't need it and would just
        # pay for a second call. ``getattr`` tolerates a backend without the
        # ``is_local`` marker (treated as cloud).
        return self.two_pass_summarize and bool(getattr(self.backend, "is_local", False))

    def _summarize(self, text: str) -> str:
        """Summarize *text*, two-pass observe-then-rewrite on a local backend.

        Pass 1 extracts plain observations (source visible, unwrapped -- it is
        faithful extraction, not user-voiced writing); pass 2 rewrites them under
        the word budget with the source unseen, wrapped so the user's
        instructions/style still shape the final summary. Falls back to the
        single-pass summary on a cloud backend or when disabled.
        """
        if self._use_two_pass_summarize():
            observations = self.backend.respond(observe_prompt(text, kind="text"))
            return self._respond_quality(
                self._wrap(rewrite_prompt(observations, word_budget=self.summary_word_budget)),
                shape=True,
            )
        # Single-pass summary still gets the #1319 hedging/filler shaping.
        return self._respond_quality(
            self._wrap(_OPERATION_PROMPTS["summarize"].format(text=text)), shape=True
        )

    def change_tone(self, text: str, tone: str) -> str:
        prompt = (
            f"Rewrite the following text in a {tone} tone. "
            f"Return only the rewritten text:\n\n{text}"
        )
        return self._respond_quality(self._wrap(prompt), shape=True)

    def ask(self, prompt: str) -> str:
        return self.backend.respond(self._wrap(prompt))

    def _respond_fitting(self, build_prompt: Callable[[int], str]) -> str:
        """Try the prompt with shrinking document context until it fits the window."""
        last_error: Exception | None = None
        for budget in _CONTEXT_BUDGETS:
            try:
                result = self.backend.respond(self._wrap(build_prompt(budget)))
                self._last_fit_budget = budget
                return result
            except ContextWindowExceeded as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        self._last_fit_budget = 0
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

    def _record_context_note(self, original_message: str, document_text: str) -> None:
        """Describe any trimming the last request applied, for the UI to speak.

        A sighted user might notice a shortened prompt; a blind user cannot,
        so silently answering over a fraction of the document reads exactly
        like answering over all of it. The note states the working size.
        """
        notes: list[str] = []
        message = (original_message or "").strip()
        if len(message) > _MAX_MESSAGE_CHARS:
            notes.append(
                f"Your message was shortened to the first {_MAX_MESSAGE_CHARS:,} "
                f"of its {len(message):,} characters to fit the model."
            )
        document = (document_text or "").strip()
        budget = self._last_fit_budget
        if document and len(document) > budget:
            if budget <= 0:
                notes.append(
                    f"The document ({len(document):,} characters) did not fit the "
                    "model, so the answer does not use it."
                )
            else:
                notes.append(
                    f"The answer used the first {budget:,} of the document's "
                    f"{len(document):,} characters."
                )
        self.last_context_note = " ".join(notes)

    def answer(self, user_message: str, document_text: str = "") -> str:
        """A full chat answer (uses the document as context, trimmed to fit)."""
        original_message = user_message
        user_message = self._clamp_message(user_message)
        result = self._respond_fitting(
            lambda budget: f"{user_message}{self._document_context(document_text, budget)}"
        )
        self._record_context_note(original_message, document_text)
        return result

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
        original_message = user_message
        user_message = self._clamp_message(user_message)

        def build(budget: int) -> str:
            return f"{user_message}{self._document_context(document_text, budget)}"

        last_error: Exception | None = None
        for budget in _CONTEXT_BUDGETS:
            try:
                result = self.backend.respond_stream(self._wrap(build(budget)), emit)
                self._last_fit_budget = budget
                self._record_context_note(original_message, document_text)
                return result
            except ContextWindowExceeded as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        self._last_fit_budget = 0
        result = self.backend.respond_stream(self._wrap(build(0)), emit)
        self._record_context_note(original_message, document_text)
        return result

    def write_for_document(self, user_message: str, document_text: str = "") -> str:
        """Generate substantial content to insert; returns only the text."""
        original_message = user_message
        user_message = self._clamp_message(user_message)
        result = self._respond_fitting(
            lambda budget: (
                "Write a complete, well-structured piece for the user's document — use "
                "multiple paragraphs and headings where appropriate, not just a title or "
                "a single line. Return ONLY the text to insert, with no preamble, labels, "
                f"or quotation marks.\n\nRequest: {user_message}"
                f"{self._document_context(document_text, budget)}"
            )
        )
        self._record_context_note(original_message, document_text)
        return result

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
