"""Everything AI help can do, in the order the pad offers it.

Seventeen choices, shared by QUILL and QUILL Lite through the one pad
(:mod:`quill.ui.hosted_ai_pad`). Each is a feature id the gateway knows
(``quill-ai-gateway/app/prompts.py``), a label a person hears on arriving at its
row, and one sentence of help -- the row's inline ``SetHelpText``, which is what
F1 reads, what the help audit checks and what ``docs/f1-help-reference.md``
renders. One sentence, written once, reaching three places.

**The writing tools** (QUILL Lite 1.1, 2026-09) are the ten after Explain:
Shorten, Simplify, Make more formal, Make friendlier, Turn into a list, Find
action items, Suggest headings, Continue writing, Write an email reply and
Translate. Every one is the shape of Summarize -- a passage in, a result out, at
the same size as any other request -- so none of them costs more than the six
that came before, on the free service or with an own key.

**Translate's language** is the one value a request fills into an instruction,
so the list is fixed on both ends: :data:`LANGUAGES` here must equal the
gateway's, and ``tests/unit/core/ai/test_writing_tools.py`` fails if they drift.

wx-free and strict-typed.
"""

from __future__ import annotations

__all__ = [
    "ACTIONS",
    "ACTION_TITLES",
    "CONVERSATION",
    "DEFAULT_LANGUAGE",
    "LANGUAGES",
    "QUESTION_ACTIONS",
    "label_for",
]

#: The feature id of a conversation, which the pad opens a window for rather
#: than sending.
CONVERSATION = "chat"

#: ``(feature id, label, help sentence)``, in the order the pad lists them.
ACTIONS: tuple[tuple[str, str, str], ...] = (
    ("summarize", "Summarize", "A few plain sentences saying what this passage says."),
    ("rewrite", "Rewrite", "The same meaning, clearer and shorter."),
    ("proofread", "Proofread", "Spelling, grammar and punctuation corrected, wording left alone."),
    ("explain", "Explain", "What this passage means, in plain language."),
    ("shorten", "Shorten", "The same passage at about half the length, every important fact kept."),
    (
        "simplify",
        "Simplify",
        "Plain language that is easy to read: short sentences, everyday words, "
        "and any technical term explained.",
    ),
    (
        "formal",
        "Make more formal",
        "The same meaning in a professional tone, for work or official letters.",
    ),
    (
        "friendly",
        "Make friendlier",
        "The same meaning in a warmer tone, as if to someone you know.",
    ),
    (
        "make_list",
        "Turn into a list",
        "A bulleted list, or numbered steps when the passage describes a process.",
    ),
    (
        "action_items",
        "Find action items",
        "Every task, who does it, and every date or deadline the passage mentions, one per line.",
    ),
    (
        "headings",
        "Suggest headings",
        "Headings that would divide the passage into sections a screen reader can "
        "jump between, and where each one goes.",
    ),
    (
        "continue",
        "Continue writing",
        "A next paragraph in the same voice, to keep, change or throw away.",
    ),
    (
        "email_reply",
        "Write an email reply",
        "Paste or select an email you received; you get a polite reply to edit, with "
        "anything you must decide left in square brackets.",
    ),
    (
        "translate",
        "Translate",
        "The passage in the language you choose below, meaning and formatting kept.",
    ),
    (
        "document_qna",
        "Ask a question about the document",
        "Type a question; QUILL Lite finds the parts of the document that answer "
        "it and sends only those.",
    ),
    (
        "ask",
        "Ask a general question",
        "Type any question. Only your question is sent -- nothing from your document.",
    ),
    (
        CONVERSATION,
        "Have a conversation",
        "Talk back and forth in a window of its own; each reply remembers what was "
        "said before. Type a first message below if you like, and press Send.",
    ),
)

#: The actions that take typing rather than a passage.
QUESTION_ACTIONS: frozenset[str] = frozenset({"document_qna", "ask", CONVERSATION})

#: What the result window is titled, per action.
ACTION_TITLES: dict[str, str] = {
    "summarize": "Summary",
    "rewrite": "Rewrite",
    "proofread": "Proofread",
    "explain": "Explanation",
    "shorten": "Shorter",
    "simplify": "Plain Language",
    "formal": "More Formal",
    "friendly": "Friendlier",
    "make_list": "List",
    "action_items": "Action Items",
    "headings": "Suggested Headings",
    "continue": "Next Paragraph",
    "email_reply": "Email Reply",
    "translate": "Translation",
    "document_qna": "Answer",
    "ask": "Answer",
}

#: The languages Translate offers -- the gateway's list, word for word.
LANGUAGES: tuple[str, ...] = (
    "English",
    "Spanish",
    "French",
    "German",
    "Italian",
    "Portuguese",
    "Dutch",
    "Swedish",
    "Polish",
    "Russian",
    "Ukrainian",
    "Turkish",
    "Arabic",
    "Hebrew",
    "Hindi",
    "Chinese (Simplified)",
    "Japanese",
    "Korean",
    "Vietnamese",
    "Tagalog",
)

#: What Translate chooses until somebody picks another.
DEFAULT_LANGUAGE = "Spanish"


def label_for(feature: str) -> str:
    """The label a person knows *feature* by."""
    return next((label for fid, label, _help in ACTIONS if fid == feature), feature)
