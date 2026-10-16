"""Filling a library prompt's placeholders: what is actually sent.

The Prompt Library (:mod:`quill.core.prompt_library`) is run two ways since
2026-10-15: on QUILL's own AI provider (Tools, AI, Prompt Library) and on the
free hosted AI, in both editors (the shared hosted-AI commands). Both fill a
prompt through :func:`fill_prompt`, so the two can never send the same prompt
differently. Kept beside the library rather than in it because that module is
at its size budget (GATE-11).

wx-free and strict-typed.
"""

from __future__ import annotations

__all__ = ["PROMPTS_FILE", "fill_prompt"]

#: The file the library is kept in, under whichever app's data folder.
PROMPTS_FILE = "prompts.json"


def fill_prompt(text: str, *, selection: str, document: str = "", title: str = "") -> str:
    """*text* with ``{selection}``, ``{document}`` and ``{title}`` filled in.

    ``{selection}`` is the input text; ``{document}`` is the whole document, or
    the input text when there is no document; ``{title}`` is the document's
    title, or nothing.
    """
    return (
        text
        .replace("{selection}", selection)
        .replace("{document}", document or selection)
        .replace("{title}", title)
    )
