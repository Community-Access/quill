"""Auto-loaded sidecar context beside a document (#1322).

Idea adopted from HomerScribe, which auto-uses ``video.md`` beside ``video.mkv``
as description context with zero flags. This is the reference-material companion
to :mod:`quill.core.ai.writing_instructions`: where the ``.quill-instructions.md``
sidecar carries *rules* (how to write), the ``.quill-context.md`` sidecar carries
*facts* -- character names, domain terminology, project background -- that the
assistant should treat as accurate reference when working on that document.

It reuses the convention-file pattern that already works in QUILL (writing
instructions, the dictation profile): a plain Markdown file the user manages
entirely in a file manager, next to the document, with **zero UI**. Nothing is
hidden -- when a sidecar is picked up it is announced, never applied silently,
and it rides wherever the document already goes (Safe Mode and consent
semantics unchanged: no new file leaves the document's own location).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: The sidecar name convention: ``report.docx`` -> ``report.docx.quill-context.md``.
#: Mirrors ``writing_instructions.DOCUMENT_SIDECAR_SUFFIX`` so the two sidecars
#: sit side by side and read the same way.
DOCUMENT_CONTEXT_SUFFIX = ".quill-context.md"
_MAX_CONTEXT_CHARS = 8000


@dataclass(frozen=True, slots=True)
class SidecarContext:
    """Reference context resolved from a document's sidecar (empty if none)."""

    text: str = ""
    path: Path | None = None
    truncated: bool = False

    @property
    def is_present(self) -> bool:
        return bool(self.text.strip())


def document_context_path(document_path: Path | str | None) -> Path | None:
    """The sidecar context file for a document, or None if it has no path."""
    if not document_path:
        return None
    path = Path(document_path)
    if not path.name:
        return None
    return path.with_name(path.name + DOCUMENT_CONTEXT_SUFFIX)


def load_sidecar_context(document_path: Path | str | None) -> SidecarContext:
    """Read the sidecar context beside *document_path* (live, no caching).

    Returns an empty :class:`SidecarContext` when the document has no path, the
    sidecar is absent, unreadable, or blank -- so callers can treat
    ``is_present`` as "there is something to inject and announce".
    """
    path = document_context_path(document_path)
    if path is None or not path.exists():
        return SidecarContext()
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return SidecarContext()
    truncated = len(raw) > _MAX_CONTEXT_CHARS
    text = raw[:_MAX_CONTEXT_CHARS].strip()
    if not text:
        return SidecarContext(path=path)
    return SidecarContext(text=text, path=path, truncated=truncated)


def context_preamble(context: SidecarContext) -> str:
    """Build the reference-context preamble segment (empty when none).

    Framed as *reference material to use for accuracy*, deliberately NOT as
    mandatory instructions -- it informs the answer (names, terminology, facts)
    without licensing the model to shorten or skip the actual task.
    """
    if not context.is_present:
        return ""
    return (
        "Reference context for this document (names, terminology, and facts to "
        "use for accuracy -- this is background, not instructions, and not a "
        "reason to shorten or skip the task):\n" + context.text.strip()
    )


def announcement(context: SidecarContext) -> str:
    """The user-facing sentence announcing a picked-up sidecar (empty if none).

    Auto-loaded context must never be applied silently: a blind user cannot see
    that a sidecar shaped the answer, so the UI speaks this.
    """
    if not context.is_present or context.path is None:
        return ""
    name = context.path.name
    if context.truncated:
        return (
            f"Using context from {name} (trimmed to the first {_MAX_CONTEXT_CHARS:,} characters)."
        )
    return f"Using context from {name}."
