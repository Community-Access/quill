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

Seventeen features are shipped. One more has a template and an id but is
switched off, and :data:`DEFERRED_FEATURES` says why in the words an operator
will read in the console.

The sixth, ``ask``, is the one that works on nothing from a document: a single
question, answered on its own, with no history. Its answer gets a ceiling of its
own (``max_ask_output_tokens``): a general answer needs more room than a
rewritten paragraph does.

The seventh, ``chat``, is a conversation -- and was deferred until 2026-09 for
the reason a conversation is usually expensive: it resends its whole history on
every turn, so each reply costs more than the last. It is shipped on the one
condition that removes that: **the history is trimmed to the same input ceiling
every other request has** (``app/routes/chat.py``, oldest turns first), so a
turn can never cost more than any other request, and every turn is a counted
request with a monthly share of its own (``feature_cap.chat``). What a long
conversation loses is memory of its opening, never money. The prompt is built by
:func:`build_prompt` from the history the client sends; the client still never
supplies the instructions.

The ten after that are the **writing tools** (2026-09, QUILL Lite 1.1):
Shorten, Simplify, Make more formal, Make friendlier, Turn into a list, Find
action items, Suggest headings, Continue writing, Write an email reply and
Translate. Each is the shape of Summarize -- one passage in, one result out,
under the same input ceiling -- so none of them moves a worst case. Translate's
target language is the one value a client fills into a template, and it must
be one of :data:`LANGUAGES`.
"""

from __future__ import annotations

__all__ = [
    "DEFERRED_FEATURES",
    "FEATURES",
    "FEATURE_LABELS",
    "LANGUAGES",
    "LONG_ANSWER_FEATURES",
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
    "ask": (
        "Answer the user's question directly and accurately, in plain "
        "language suitable for a screen reader to read aloud. Be concise: "
        "give the answer first, then only the detail that helps. If you are "
        "not sure of something, say so rather than guessing. Do not use "
        "tables, and keep any formatting simple.\n\n{prompt}"
    ),
    "document_qna": (
        "You are answering a question about excerpts from the user's own "
        "document. Answer only from the excerpts provided; if they do not "
        "contain the answer, say so plainly rather than guessing. Keep the "
        "answer concise and in plain language suitable for a screen reader "
        "to read aloud.\n\nExcerpts:\n{context}\n\nQuestion: {prompt}"
    ),
    # --- The writing tools (2026-09, QUILL Lite 1.1). Each is one passage in,
    # one result out, at the same size as every other request. -------------
    "shorten": (
        "Shorten the following text to about half its length. Keep every "
        "important fact, the meaning and the tone; cut repetition and "
        "padding. Return only the shortened text, with no preamble.\n\n{prompt}"
    ),
    "simplify": (
        "Rewrite the following text in plain language that is easy to read: "
        "short sentences, everyday words, and any necessary technical term "
        "explained the first time it appears. Keep every fact and do not add "
        "any. Return only the rewritten text, with no preamble.\n\n{prompt}"
    ),
    "formal": (
        "Rewrite the following text in a more formal, professional tone, "
        "suitable for work or official correspondence. Keep the meaning and "
        "every fact. Return only the rewritten text, with no preamble.\n\n{prompt}"
    ),
    "friendly": (
        "Rewrite the following text in a warmer, friendlier tone, as if to "
        "someone the writer knows. Keep the meaning and every fact. Return "
        "only the rewritten text, with no preamble.\n\n{prompt}"
    ),
    "make_list": (
        "Turn the following text into a clear list: numbered steps if it "
        "describes a process, otherwise bullet points. Start each item on its "
        "own line with a hyphen and a space, or with its number and a full "
        "stop. Keep every fact and add none. Return only the list, with no "
        "preamble.\n\n{prompt}"
    ),
    "action_items": (
        "List the action items in the following text: every task someone has "
        "to do, with who and by when wherever the text says, and every date "
        "or deadline it mentions. One item per line, starting with a hyphen "
        "and a space. If there are none, say so in one sentence. Do not add "
        "anything the text does not say.\n\n{prompt}"
    ),
    "headings": (
        "Suggest headings that would divide the following text into clear "
        "sections a reader can jump between. For each, give the heading on "
        "its own line, then on the next line the first few words of the "
        "paragraph it belongs above, in quotation marks. Keep headings short "
        "and plain. Return only the headings and their places, with no "
        "preamble.\n\n{prompt}"
    ),
    "continue": (
        "Write the next paragraph of the following text, continuing it "
        "naturally in the same voice, tone and tense. Do not repeat or "
        "summarize what is already there, and do not add a conclusion unless "
        "the text is clearly ending. Return only the new paragraph.\n\n{prompt}"
    ),
    "email_reply": (
        "The following is an email the user received. Write a clear, polite "
        "reply that the user can edit before sending: answer each question "
        "it asks, and where the user must decide something, leave a short "
        "placeholder in square brackets. Return only the body of the reply, "
        "with no subject line and no preamble.\n\n{prompt}"
    ),
    "translate": (
        "Translate the following text into {language}. Keep the meaning, the "
        "tone and any formatting such as line breaks and lists. Return only "
        "the translation, with no preamble or notes.\n\n{prompt}"
    ),
    "chat": (
        "You are a helpful assistant inside QUILL, an accessibility-first "
        "text editor, in a conversation with the user. Reply to their latest "
        "message directly and concisely, in plain language suitable for a "
        "screen reader to read aloud, using the conversation so far for "
        "context. If excerpts from the user's document are included, answer "
        "questions about the document only from them, and say so plainly "
        "when they do not contain the answer. If you are not sure of "
        "something, say so rather than guessing. Do not use tables, and keep "
        "any formatting simple.\n\n{prompt}"
    ),
    # --- Not shipped. See DEFERRED_FEATURES. --------------------------------
    "alt_text": (
        "Describe this image in one concise sentence suitable as alt text "
        "for a screen reader. Focus on what the image conveys, not "
        "incidental visual detail.\n\n{prompt}"
    ),
}

#: The seven features the free tier actually offers today.
SHIPPED_FEATURES: tuple[str, ...] = (
    "summarize",
    "rewrite",
    "proofread",
    "explain",
    "document_qna",
    "ask",
    "chat",
    "shorten",
    "simplify",
    "formal",
    "friendly",
    "make_list",
    "action_items",
    "headings",
    "continue",
    "email_reply",
    "translate",
)

#: Features whose answer gets the longer ceiling (``max_ask_output_tokens``)
#: rather than the ordinary one: a general answer, a conversation reply, and the
#: writing tools whose result can be longer than a summary -- a translation or a
#: new paragraph is as long as it needs to be. The Limits page prices every
#: request at the longer ceiling already, so this moves no worst case.
LONG_ANSWER_FEATURES: frozenset[str] = frozenset({
    "ask",
    "chat",
    "translate",
    "continue",
    "email_reply",
    "headings",
    "make_list",
    "simplify",
})

#: The languages Translate offers. The client shows the same list
#: (``quill/core/ai/writing_tools.py``); anything else is refused, because the
#: language is the one piece of a template a client fills in, and a free-text
#: field there would be a place to smuggle instructions.
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

#: Features with an id and a template that are deliberately switched off, and
#: the sentence the console (and anyone who somehow reaches them) is shown.
#: These are seeded with ``enabled = False``, so the ordinary feature-flag path
#: refuses them — there is no second mechanism to keep in step.
DEFERRED_FEATURES: dict[str, str] = {
    "alt_text": (
        "Describing pictures is not a shipped feature yet. It costs several "
        "times more per request than text does and needs its own limits, so "
        "it is deliberately last. Nothing in QUILL or QUILL Lite can reach it."
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
    "ask": "General questions",
    "alt_text": "Pictures (alt text)",
    "chat": "Conversations",
    "shorten": "Shorten",
    "simplify": "Simplify",
    "formal": "Make more formal",
    "friendly": "Make friendlier",
    "make_list": "Turn into a list",
    "action_items": "Find action items",
    "headings": "Suggest headings",
    "continue": "Continue writing",
    "email_reply": "Write an email reply",
    "translate": "Translate",
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
    "ask": "none",
    "alt_text": "none",
    "chat": "none",
    "shorten": "none",
    "simplify": "none",
    "formal": "none",
    "friendly": "none",
    "make_list": "none",
    "action_items": "none",
    "headings": "none",
    "continue": "none",
    "email_reply": "none",
    "translate": "none",
}

#: The only values :data:`REASONING_EFFORT` may take, cheapest first. Anything
#: above ``low`` is not reachable from this table on purpose: the tiers above it
#: cost multiples more and none of the six shipped features needs one.
ALLOWED_EFFORTS: tuple[str, ...] = ("none", "low")


def reasoning_effort_for(feature: str) -> str:
    """The effort setting for *feature*, floored at ``none`` for anything
    unlisted. An unknown feature must never inherit the provider's default,
    which is where the doubled bill comes from."""
    effort = REASONING_EFFORT.get(feature, "none")
    return effort if effort in ALLOWED_EFFORTS else "none"


#: Who said a turn, as the model reads it. The only two roles a history may hold.
HISTORY_SPEAKERS: dict[str, str] = {"user": "User", "assistant": "Assistant"}


def chat_message(prompt: str, chunks: list[str] | None, history: list[dict] | None) -> str:
    """The user half of a ``chat`` request: document excerpts, the conversation
    so far, then the latest message.

    Mirrored word for word by ``quill/core/ai/own_key.py`` (an own-key chat is
    built on the user's computer), and ``tests/unit/core/ai/test_own_key.py``
    fails if the two drift -- a conversation must read the same to the model
    whichever way it travels.
    """
    parts: list[str] = []
    if chunks:
        parts.append("Excerpts from the user's document:\n" + "\n\n---\n\n".join(chunks))
    if history:
        lines = [f"{HISTORY_SPEAKERS[turn['role']]}: {turn['content']}" for turn in history]
        parts.append("The conversation so far:\n" + "\n\n".join(lines))
    parts.append(f"The user's latest message:\n{prompt}")
    return "\n\n".join(parts)


def build_prompt(
    feature: str,
    prompt: str,
    chunks: list[str] | None = None,
    history: list[dict] | None = None,
    language: str = "English",
) -> str:
    """The exact text sent to the model for *feature*, wrapping the
    client-supplied *prompt* (and, for document Q&A, its *chunks*; for a
    conversation, its *history* too) in the feature's fixed template. Raises
    :class:`KeyError` for an unknown feature — the caller
    (``app/routes/chat.py``) validates ``feature`` against :data:`FEATURES`
    before ever reaching here, and validates *history* as well."""
    template = TEMPLATES[feature]
    if feature == "document_qna":
        context = "\n\n---\n\n".join(chunks or [])
        return template.format(context=context, prompt=prompt)
    if feature == "chat":
        return template.format(prompt=chat_message(prompt, chunks, history))
    if feature == "translate":
        # The caller has checked *language* against LANGUAGES; a value that is
        # not in it never reaches a template.
        return template.format(prompt=prompt, language=language)
    return template.format(prompt=prompt)
