"""Document Q&A via the configured AI provider.

Accepts document text (or a PDF path) and a question, sends both to the AI
with a system prompt that restricts answers to document content, and returns
a structured answer with source context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.ai.custom_instructions import split_instruction
from quill.core.assistant_ai import AssistantConnectionSettings, generate_assistant_response
from quill.core.error_codes import CodedError

_QA_PROMPT_TEMPLATE = (
    "You are a precise document assistant. Answer questions using ONLY the information "
    "in the document provided. If the answer is not in the document, say so explicitly — "
    "do not invent or guess. Quote the relevant passage when possible.\n\n"
    "DOCUMENT:\n{document}\n\n"
    "QUESTION: {question}\n\n"
    "ANSWER:"
)

_MAX_DOC_CHARS = 80_000
_CONTEXT_WINDOW_CHARS = 200


class DocumentQAError(CodedError):
    code = "QUILL-AI-DOCQA-FAILED"


class DocumentQAAuthError(DocumentQAError):
    pass


class DocumentQAEmptyError(DocumentQAError):
    pass


@dataclass(frozen=True)
class QAAnswer:
    question: str
    answer: str
    source_excerpt: str = ""
    truncated: bool = False


def ask_document(
    question: str,
    document_text: str,
    connection: AssistantConnectionSettings,
    api_key: str = "",
) -> QAAnswer:
    """Ask *question* about *document_text* and return a structured answer.

    Raises DocumentQAEmptyError if question or document is blank.
    Raises DocumentQAAuthError on API authentication failure.
    Raises DocumentQAError on any other failure.
    """
    question = question.strip()
    document_text = document_text.strip()

    if not question:
        raise DocumentQAEmptyError("Question is empty.")
    if not document_text:
        raise DocumentQAEmptyError("Document is empty — nothing to ask about.")

    truncated = len(document_text) > _MAX_DOC_CHARS
    doc_for_prompt = document_text[:_MAX_DOC_CHARS] if truncated else document_text

    system_prompt, user_prompt = split_instruction(
        "document_qa",
        _QA_PROMPT_TEMPLATE.format(document=doc_for_prompt, question=question),
    )

    response, error = generate_assistant_response(
        connection,
        api_key,
        user_prompt,
        max_tokens=2048,
        system_prompt=system_prompt,
        timeout_seconds=120.0,
    )

    if error:
        msg = error.lower()
        if "auth" in msg or "401" in msg or "api key" in msg:
            raise DocumentQAAuthError(error)
        raise DocumentQAError(error)
    if not response:
        raise DocumentQAError("AI returned no response.")

    answer_text = response.strip()
    excerpt = _find_source_excerpt(answer_text, document_text)

    return QAAnswer(
        question=question,
        answer=answer_text,
        source_excerpt=excerpt,
        truncated=truncated,
    )


def ask_pdf(
    question: str,
    pdf_path: Path,
    connection: AssistantConnectionSettings,
    api_key: str = "",
) -> QAAnswer:
    """Extract text from *pdf_path* and call :func:`ask_document`."""
    from quill.io.pdf import format_pdf_document

    path = Path(pdf_path)
    if not path.exists():
        raise DocumentQAError(f"File not found: {path}")
    text = format_pdf_document(path)
    if not text.strip():
        raise DocumentQAEmptyError(f"No text could be extracted from {path.name}.")
    return ask_document(question, text, connection, api_key)


def _find_source_excerpt(answer: str, document: str) -> str:
    """Find a short passage from *document* that likely supports *answer*.

    Looks for a long word from the answer that also appears in the document
    and returns a surrounding window. Returns empty string if nothing matches.
    """
    answer_words = [w for w in answer.split() if len(w) > 6 and w.isalpha()]
    for word in answer_words:
        idx = document.lower().find(word.lower())
        if idx >= 0:
            start = max(0, idx - 80)
            end = min(len(document), idx + _CONTEXT_WINDOW_CHARS)
            snippet = document[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(document):
                snippet = snippet + "..."
            return snippet
    return ""


@dataclass
class ConversationContext:
    """Multi-turn Q&A session state for a single document."""

    document_text: str
    turns: list[tuple[str, str]] = field(default_factory=list)

    def ask(
        self,
        question: str,
        connection: AssistantConnectionSettings,
        api_key: str = "",
    ) -> QAAnswer:
        """Ask a follow-up question with prior turns included for context."""
        history = ""
        if self.turns:
            history_parts = []
            for q, a in self.turns[-3:]:  # last 3 turns for context
                history_parts.append(f"Q: {q}\nA: {a}")
            history = "\nPrevious questions:\n" + "\n\n".join(history_parts) + "\n\n"

        prompt_doc = self.document_text[:_MAX_DOC_CHARS]
        truncated = len(self.document_text) > _MAX_DOC_CHARS
        prompt = (
            "You are a precise document assistant. Answer using ONLY the document below. "
            "If the answer is not in the document, say so.\n\n"
            f"DOCUMENT:\n{prompt_doc}\n\n"
            f"{history}"
            f"QUESTION: {question}\n\nANSWER:"
        )

        response, error = generate_assistant_response(
            connection, api_key, prompt, max_tokens=2048, timeout_seconds=120.0
        )
        if error:
            raise DocumentQAError(error)
        if not response:
            raise DocumentQAError("AI returned no response.")

        answer_text = response.strip()
        self.turns.append((question, answer_text))
        return QAAnswer(
            question=question,
            answer=answer_text,
            source_excerpt=_find_source_excerpt(answer_text, self.document_text),
            truncated=truncated,
        )

    def clear_history(self) -> None:
        self.turns.clear()
