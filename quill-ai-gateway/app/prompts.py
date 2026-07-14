"""The fixed, server-side-only system prompt template per feature.

PRD §8 is explicit about why these live in code, not in
``gateway_config``: the client never supplies its own system prompt (only
a user prompt/question), so a modified client can't smuggle an
unapproved use through an approved ``feature`` id. Changing a template
here is a reviewed code change and a deploy, exactly like changing any
other product behavior -- never a runtime admin dial.
"""

from __future__ import annotations

TEMPLATES: dict[str, str] = {
    "document_qna": (
        "You are answering a question about an excerpt from the user's own "
        "document. Answer only from the excerpt provided; if the excerpt "
        "doesn't contain the answer, say so plainly rather than guessing. "
        "Keep the answer concise and in plain language suitable for a "
        "screen reader to read aloud.\n\nExcerpt:\n{context}\n\nQuestion: {prompt}"
    ),
    "summarize": (
        "Summarize the following text in a few clear sentences, in plain "
        "language suitable for a screen reader to read aloud. Preserve the "
        "key facts; do not add information that isn't in the text.\n\n{prompt}"
    ),
    "rewrite": (
        "Rewrite the following text to be clearer and more concise, "
        "preserving its meaning and tone. Return only the rewritten text, "
        "with no preamble or explanation.\n\n{prompt}"
    ),
    "alt_text": (
        "Describe this image in one concise sentence suitable as alt text "
        "for a screen reader. Focus on what the image conveys, not "
        "incidental visual detail.\n\n{prompt}"
    ),
    "chat": (
        "You are a helpful writing assistant inside QUILL, an "
        "accessibility-first text editor. Answer the user's message "
        "directly and concisely, in plain language suitable for a screen "
        "reader to read aloud.\n\n{prompt}"
    ),
}

FEATURES = frozenset(TEMPLATES)


def build_prompt(feature: str, prompt: str, chunks: list[str] | None = None) -> str:
    """The exact text sent to the model for *feature*, wrapping the
    client-supplied *prompt* (and, for document Q&A, its *chunks*) in the
    feature's fixed template. Raises :class:`KeyError` for an unknown
    feature -- the caller (``app/routes/chat.py``) validates ``feature``
    against :data:`FEATURES` before ever reaching here."""
    template = TEMPLATES[feature]
    if feature == "document_qna":
        context = "\n\n---\n\n".join(chunks or [])
        return template.format(context=context, prompt=prompt)
    return template.format(prompt=prompt)
