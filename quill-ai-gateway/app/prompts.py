"""The fixed, server-side-only system prompt per feature, and how hard the
model is allowed to think about it.

PRD §8 is explicit about why these live in code, not in ``gateway_config``: the
client never supplies its own system prompt (only a user prompt or question), so
a modified client cannot smuggle an unapproved use through an approved
``feature`` id. Changing a template here is a reviewed code change and a deploy,
exactly like changing any other product behavior — never a runtime admin dial.

:data:`REASONING_EFFORT` is in this module for exactly the same reason, and it
is the more expensive of the two to get wrong. Reasoning tokens are billed at
the output rate and never appear in the answer, so a model left at its
provider's default effort roughly **doubles the entire service bill** with
nothing to show for it. Worse, reasoning is drawn from the same output budget as
the answer: if it consumes ``max_output_tokens``, the user is charged for an
empty reply. Both halves of that are handled — the effort floor here, and the
no-charge-for-nothing rule in ``app/routes/chat.py``.

Five features are shipped. Two more have templates and ids but are switched off,
and :data:`DEFERRED_FEATURES` says why in the words an operator will read in the
console.
"""

from __future__ import annotations

__all__ = [
    "DEFERRED_FEATURES",
    "FEATURES",
    "FEATURE_LABELS",
    "REASONING_EFFORT",
    "SHIPPED_FEATURES",
    "TEMPLATES",
    "build_prompt",
    "reasoning_effort_for",
]

TEMPLATES: dict[str, str] = {
    "summarize": (
        "Summarize the following text in a few clear sentences, in plain "
        "language suitable for a screen reader to read aloud. Preserve the "
        "key facts; do not add information that isn't in the text. Return "
        "only the summary, with no preamble.\n\n{prompt}"
    ),
    "rewrite": (
        "Rewrite the following text to be clearer and more concise, "
        "preserving its meaning and tone. Return only the rewritten text, "
        "with no preamble or explanation.\n\n{prompt}"
    ),
    "proofread": (
        "Correct the spelling, grammar and punctuation of the following "
        "text. Do not change the wording, the tone, or the meaning beyond "
        "what the corrections require, and do not rewrite for style. Return "
        "only the corrected text, with no preamble, no explanation and no "
        "list of what changed.\n\n{prompt}"
    ),
    "explain": (
        "Explain what the following passage means, in plain language "
        "suitable for a screen reader to read aloud. Be brief. Explain only "
        "what the passage says; do not judge it, and do not add information "
        "from outside it. Return only the explanation, with no "
        "preamble.\n\n{prompt}"
    ),
    "document_qna": (
        "You are answering a question about excerpts from the user's own "
        "document. Answer only from the excerpts provided; if they do not "
        "contain the answer, say so plainly rather than guessing. Keep the "
        "answer concise and in plain language suitable for a screen reader "
        "to read aloud.\n\nExcerpts:\n{context}\n\nQuestion: {prompt}"
    ),
    # --- Not shipped. See DEFERRED_FEATURES. --------------------------------
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

#: The five features the free tier actually offers today.
SHIPPED_FEATURES: tuple[str, ...] = (
    "summarize",
    "rewrite",
    "proofread",
    "explain",
    "document_qna",
)

#: Features with an id and a template that are deliberately switched off, and
#: the sentence the console (and anyone who somehow reaches them) is shown.
#: These are seeded with ``enabled = False``, so the ordinary feature-flag path
#: refuses them — there is no second mechanism to keep in step.
DEFERRED_FEATURES: dict[str, str] = {
    "alt_text": (
        "Describing pictures is not a shipped feature yet. It costs several "
        "times more per request than text does and needs its own limits, so "
        "it is deliberately last. Nothing in QUILL or QuillLite can reach it."
    ),
    "chat": (
        "Open-ended chat is not part of the free tier. Every free feature "
        "works on a passage you selected or a question about a document you "
        "have open, which is what keeps requests small and predictable. Chat "
        "is available with your own API key."
    ),
}

#: Every id the ``/v1/chat`` route will recognise. A deferred feature is
#: recognised and then refused by its flag, which produces a clear sentence;
#: an unrecognised one is a 400, which does not.
FEATURES = frozenset(TEMPLATES)

#: What each feature is called in a sentence a person reads.
FEATURE_LABELS: dict[str, str] = {
    "summarize": "Summarize",
    "rewrite": "Rewrite",
    "proofread": "Proofread",
    "explain": "Explain",
    "document_qna": "Questions about documents",
    "alt_text": "Pictures (alt text)",
    "chat": "Open-ended chat",
}

#: How hard the model may think, per feature. Code, not config — see the module
#: docstring. ``none`` is the floor and the default; ``document_qna`` is the one
#: feature with genuine synthesis to do, and even it should be measured against
#: ``none`` before the setting is kept.
REASONING_EFFORT: dict[str, str] = {
    "summarize": "none",
    "rewrite": "none",
    "proofread": "none",
    "explain": "none",
    "document_qna": "low",
    "alt_text": "none",
    "chat": "none",
}

#: The only values :data:`REASONING_EFFORT` may take, cheapest first. Anything
#: above ``low`` is not reachable from this table on purpose: the tiers above it
#: cost multiples more and none of the five shipped features needs one.
ALLOWED_EFFORTS: tuple[str, ...] = ("none", "low")


def reasoning_effort_for(feature: str) -> str:
    """The effort setting for *feature*, floored at ``none`` for anything
    unlisted. An unknown feature must never inherit the provider's default,
    which is where the doubled bill comes from."""
    effort = REASONING_EFFORT.get(feature, "none")
    return effort if effort in ALLOWED_EFFORTS else "none"


def build_prompt(feature: str, prompt: str, chunks: list[str] | None = None) -> str:
    """The exact text sent to the model for *feature*, wrapping the
    client-supplied *prompt* (and, for document Q&A, its *chunks*) in the
    feature's fixed template. Raises :class:`KeyError` for an unknown feature —
    the caller (``app/routes/chat.py``) validates ``feature`` against
    :data:`FEATURES` before ever reaching here."""
    template = TEMPLATES[feature]
    if feature == "document_qna":
        context = "\n\n---\n\n".join(chunks or [])
        return template.format(context=context, prompt=prompt)
    return template.format(prompt=prompt)
