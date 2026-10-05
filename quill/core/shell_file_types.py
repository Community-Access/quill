"""Which kinds of file get QUILL's right-click verbs (``shell_file_types``).

The Integration page has always offered "File types offered to QUILL" -- images
only; images and PDF; or images, PDF and text documents -- and until 2026-10
nothing read it, so every enabled verb was registered on every extension it
could handle. This narrows each verb's extensions to the chosen kinds before
the registry plan is built.

Only the three kinds the choice names are narrowed. Media files belong to the
"Convert with QUILL" verb, which has its own switch and is not an image, PDF or
text document, so the choice leaves them alone.

wx-free, platform-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from quill.core.shell_verbs import (
    IMAGE_EXTENSIONS,
    OPENABLE_EXTENSIONS,
    PDF_EXTENSIONS,
    ShellVerb,
)

#: The choice values, in the order Settings offers them.
FILE_TYPE_CHOICES: tuple[str, ...] = ("images", "images_pdf", "images_pdf_docs")

#: What a missing or unknown value means: every kind, which is what QUILL
#: registered before the setting was read.
DEFAULT_FILE_TYPES = "images_pdf_docs"

_GOVERNED: frozenset[str] = frozenset(IMAGE_EXTENSIONS + PDF_EXTENSIONS + OPENABLE_EXTENSIONS)


def allowed_extensions(choice: str) -> frozenset[str]:
    """The governed extensions the *choice* keeps."""
    value = (choice or "").strip().lower()
    if value not in FILE_TYPE_CHOICES:
        value = DEFAULT_FILE_TYPES
    allowed = set(IMAGE_EXTENSIONS)
    if value in {"images_pdf", "images_pdf_docs"}:
        allowed.update(PDF_EXTENSIONS)
    if value == "images_pdf_docs":
        allowed.update(OPENABLE_EXTENSIONS)
    return frozenset(allowed)


def narrow_verbs(verbs: Iterable[ShellVerb], choice: str) -> list[ShellVerb]:
    """Each verb restricted to the chosen kinds; a verb left with none is dropped."""
    allowed = allowed_extensions(choice)
    result: list[ShellVerb] = []
    for verb in verbs:
        kept = tuple(ext for ext in verb.extensions if ext not in _GOVERNED or ext in allowed)
        if kept:
            result.append(verb if kept == verb.extensions else replace(verb, extensions=kept))
    return result


__all__ = [
    "DEFAULT_FILE_TYPES",
    "FILE_TYPE_CHOICES",
    "allowed_extensions",
    "narrow_verbs",
]
