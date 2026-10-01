"""AI help with the user's own OpenAI key: no allowance, no QUILL server.

The AI help features normally go through QUILL's free service, which keeps
an allowance per person and a size limit per request. Somebody with their own
OpenAI account can switch that off: the same features then go **straight
from this computer to OpenAI**, billed to their account, with no QUILL server in
between and none of the free tier's limits.

**No limits, and warnings instead.** With a key there is no allowance, no size
ceiling on what is sent, no ceiling on the answer, and no excerpt picking: a
question about a document sends the whole document. What replaces each limit is
a sentence before sending (:func:`size_warning`) -- how big this is, roughly
what it costs, and when it is big enough that OpenAI may refuse it -- because a
person paying per token should know before a whole book goes, and should still
be allowed to send it.

Three things make it the same feature rather than a second one:

* **The same instructions.** :data:`INSTRUCTIONS` are the gateway's own
  templates (``quill-ai-gateway/app/prompts.py``), sent as the system message so
  a summary is the same summary whichever way it travels.
  ``tests/unit/core/ai/test_own_key.py`` fails if the two drift.
* **The same key store as QUILL.** The key lives where QUILL's AI Hub keeps its
  OpenAI key (Windows Credential Manager, or an encrypted file in a portable
  copy), so a key entered in either program works in both.
* **The same client.** :func:`quill.core.assistant_ai.generate_assistant_response`
  -- QUILL's own provider code, plain HTTPS, certificate-checked, with retries.

wx-free.
"""

from __future__ import annotations

from typing import Any

from quill.core.ai.gateway_client import GatewayLimits
from quill.core.error_codes import CodedError

__all__ = [
    "CONTEXT_WARNING_TOKENS",
    "INSTRUCTIONS",
    "OWN_KEY_LIMITS",
    "UNLIMITED",
    "OWN_KEY_PROVIDER",
    "OWN_KEY_PROVIDERS",
    "OwnKeyError",
    "active_own_key_provider",
    "ask_with_own_key",
    "default_model",
    "describe_image_with_own_key",
    "has_own_key",
    "load_settings_fields",
    "own_key_active",
    "request_for",
    "size_warning",
]

OWN_KEY_PROVIDER = "openai"
OWN_KEY_PROVIDERS: tuple[str, ...] = ("openai", "gemini")

#: The instruction half of each gateway template, sent as the system message.
#: Must match ``quill-ai-gateway/app/prompts.py`` word for word.
INSTRUCTIONS: dict[str, str] = {
    "summarize": (
        "Summarize the following text in a few clear sentences, in plain "
        "language suitable for a screen reader to read aloud. Preserve the "
        "key facts; do not add information that isn't in the text. Return "
        "only the summary, with no preamble."
    ),
    "rewrite": (
        "Rewrite the following text to be clearer and more concise, "
        "preserving its meaning and tone. Return only the rewritten text, "
        "with no preamble or explanation."
    ),
    "proofread": (
        "Correct the spelling, grammar and punctuation of the following "
        "text. Do not change the wording, the tone, or the meaning beyond "
        "what the corrections require, and do not rewrite for style. Return "
        "only the corrected text, with no preamble, no explanation and no "
        "list of what changed."
    ),
    "explain": (
        "Explain what the following passage means, in plain language "
        "suitable for a screen reader to read aloud. Be brief. Explain only "
        "what the passage says; do not judge it, and do not add information "
        "from outside it. Return only the explanation, with no "
        "preamble."
    ),
    "ask": (
        "Answer the user's question directly and accurately, in plain "
        "language suitable for a screen reader to read aloud. Be concise: "
        "give the answer first, then only the detail that helps. If you are "
        "not sure of something, say so rather than guessing. Do not use "
        "tables, and keep any formatting simple."
    ),
    "document_qna": (
        "You are answering a question about excerpts from the user's own "
        "document. Answer only from the excerpts provided; if they do not "
        "contain the answer, say so plainly rather than guessing. Keep the "
        "answer concise and in plain language suitable for a screen reader "
        "to read aloud."
    ),
    "chat": (
        "You are a helpful assistant inside QUILL, an accessibility-first "
        "text editor, in a conversation with the user. Reply to their latest "
        "message directly and concisely, in plain language suitable for a "
        "screen reader to read aloud, using the conversation so far for "
        "context. If excerpts from the user's document are included, answer "
        "questions about the document only from them, and say so plainly when"
        " they do not contain the answer. If you are not sure of something, "
        "say so rather than guessing. Do not use tables, and keep any "
        "formatting simple."
    ),
    "shorten": (
        "Shorten the following text to about half its length. Keep every "
        "important fact, the meaning and the tone; cut repetition and "
        "padding. Return only the shortened text, with no preamble."
    ),
    "simplify": (
        "Rewrite the following text in plain language that is easy to read: "
        "short sentences, everyday words, and any necessary technical term "
        "explained the first time it appears. Keep every fact and do not add "
        "any. Return only the rewritten text, with no preamble."
    ),
    "formal": (
        "Rewrite the following text in a more formal, professional tone, "
        "suitable for work or official correspondence. Keep the meaning and "
        "every fact. Return only the rewritten text, with no preamble."
    ),
    "friendly": (
        "Rewrite the following text in a warmer, friendlier tone, as if to "
        "someone the writer knows. Keep the meaning and every fact. Return "
        "only the rewritten text, with no preamble."
    ),
    "make_list": (
        "Turn the following text into a clear list: numbered steps if it "
        "describes a process, otherwise bullet points. Start each item on its"
        " own line with a hyphen and a space, or with its number and a full "
        "stop. Keep every fact and add none. Return only the list, with no "
        "preamble."
    ),
    "action_items": (
        "List the action items in the following text: every task someone has "
        "to do, with who and by when wherever the text says, and every date "
        "or deadline it mentions. One item per line, starting with a hyphen "
        "and a space. If there are none, say so in one sentence. Do not add "
        "anything the text does not say."
    ),
    "headings": (
        "Suggest headings that would divide the following text into clear "
        "sections a reader can jump between. For each, give the heading on "
        "its own line, then on the next line the first few words of the "
        "paragraph it belongs above, in quotation marks. Keep headings short "
        "and plain. Return only the headings and their places, with no "
        "preamble."
    ),
    "continue": (
        "Write the next paragraph of the following text, continuing it "
        "naturally in the same voice, tone and tense. Do not repeat or "
        "summarize what is already there, and do not add a conclusion unless "
        "the text is clearly ending. Return only the new paragraph."
    ),
    "email_reply": (
        "The following is an email the user received. Write a clear, polite "
        "reply that the user can edit before sending: answer each question it"
        " asks, and where the user must decide something, leave a short "
        "placeholder in square brackets. Return only the body of the reply, "
        "with no subject line and no preamble."
    ),
    "translate": (
        "Translate the following text into {language}. Keep the meaning, the "
        "tone and any formatting such as line breaks and lists. Return only "
        "the translation, with no preamble or notes."
    ),
    # Not a gateway feature: dictated text is only tidied on a direct route (a
    # ChatGPT plan or an own key), where there is no allowance to spend it
    # from, so the gateway has no template to match and the word-for-word test
    # does not cover it (2026-09-29).
    "tidy_dictation": (
        "The following text was dictated by voice and written down by speech "
        "recognition. Correct what the recogniser got wrong: words that sound "
        "alike but are not the word meant, names and technical terms it "
        "misheard, words run together or split apart, and missing or misplaced "
        "punctuation and capitalisation. Remove filler words and false starts. "
        "Keep the speaker's meaning, wording, tone and order otherwise, and add "
        "nothing. Return only the corrected text, with no preamble, no "
        "explanation and no list of what changed."
    ),
}

#: Effectively no limit. The pad never refuses on size with a key; it warns
#: (:func:`size_warning`), and OpenAI's own context window is the only ceiling.
UNLIMITED = 1_000_000_000

#: What the pad is told the limits are with an own key: every feature on, and
#: no size, answer or excerpt ceiling at all.
OWN_KEY_LIMITS = GatewayLimits(
    max_input_tokens=UNLIMITED,
    max_output_tokens=UNLIMITED,
    max_chunks_per_request=UNLIMITED,
    hosted_ai_enabled=True,
    feature_flags={feature: True for feature in INSTRUCTIONS},
)

#: Past this many tokens a request is big enough that the chosen model may not
#: be able to read it at once. OpenAI refuses such a request before doing any
#: work, so the warning says so -- it is a warning, never a refusal here.
CONTEXT_WARNING_TOKENS = 100_000


class OwnKeyError(CodedError):
    """A request with the user's own key did not produce an answer."""

    code = "QUILL-AI-OWN-KEY-FAILED"
    user_hint = (
        "Check your API key and model in Use My Own API Key, and verify your "
        "account has credit. Or switch back to QUILL's free AI there."
    )


def infer_provider_from_model(model: str) -> str:
    """Infer provider from model name if unmistakable, else empty string."""
    m = model.strip().lower()
    if "gemini" in m:
        return "gemini"
    if any(
        m.startswith(p)
        for p in ("gpt", "o1", "o3", "o4", "chat", "luna", "text-", "davinci", "babbage")
    ):
        return "openai"
    return ""


def active_own_key_provider(settings: Any = None) -> str:
    """Return the provider id to use for own-key AI: the saved choice, or detected key."""
    from quill.core.assistant_ai import load_provider_api_key

    if settings is not None:
        saved_provider = str(getattr(settings, "ai_own_key_provider", "") or "").strip().lower()
        if saved_provider in OWN_KEY_PROVIDERS and load_provider_api_key(saved_provider):
            return saved_provider

    # Auto-detection: prefer configured/environment key in provider order
    for prov in OWN_KEY_PROVIDERS:
        if load_provider_api_key(prov):
            return prov
    return OWN_KEY_PROVIDER


def default_model(provider: str = "") -> str:
    from quill.core.assistant_ai import default_model_for_provider

    target = provider.strip().lower() or active_own_key_provider()
    return default_model_for_provider(target)


def has_own_key(provider: str = "") -> bool:
    """Whether an API key is stored (or set in the environment) for own-key use."""
    from quill.core.assistant_ai import load_provider_api_key

    try:
        if provider:
            return bool(load_provider_api_key(provider.strip().lower()))
        return bool(load_provider_api_key("openai") or load_provider_api_key("gemini"))
    except Exception:  # noqa: BLE001 - an unreadable store is "no key"
        return False


def own_key_active(settings: Any = None) -> bool:
    """Whether AI help uses the user's key: whenever one is saved or present in the environment."""
    if settings is not None:
        saved_provider = str(getattr(settings, "ai_own_key_provider", "") or "").strip().lower()
        if saved_provider:
            return has_own_key(saved_provider)
    return has_own_key()


def load_settings_fields(data: Any) -> dict[str, Any]:
    """The own-key settings from saved JSON, for QUILL's settings loader."""
    return {
        "ai_own_key_model": str(data.get("ai_own_key_model", "") or ""),
        "ai_own_key_provider": str(data.get("ai_own_key_provider", "") or ""),
    }


def request_for(
    feature: str,
    prompt: str,
    chunks: list[str] | None = None,
    history: list[dict[str, str]] | None = None,
    language: str = "English",
) -> tuple[str, str]:
    """``(system, user)`` messages for *feature* -- the gateway's, split in two.

    A conversation's user half is :func:`quill.core.ai.hosted_chat.chat_message`
    (the gateway's own formatting); Translate names *language*, which must be
    one of :data:`quill.core.ai.writing_tools.LANGUAGES`.
    """
    instructions = INSTRUCTIONS.get(feature)
    if instructions is None:
        raise OwnKeyError(f"{feature.replace('_', ' ').capitalize()} is not available.")
    if feature == "document_qna":
        context = "\n\n---\n\n".join(chunks or [])
        return instructions, f"Excerpts:\n{context}\n\nQuestion: {prompt}"
    if feature == "chat":
        from quill.core.ai.hosted_chat import chat_message

        return instructions, chat_message(prompt, chunks, history)
    if feature == "translate":
        from quill.core.ai.writing_tools import LANGUAGES

        if language not in LANGUAGES:
            raise OwnKeyError(f"{language} is not a language Translate offers.")
        return instructions.format(language=language), prompt
    return instructions, prompt


def ask_with_own_key(
    feature: str,
    prompt: str,
    chunks: list[str] | None = None,
    *,
    provider: str = "",
    model: str = "",
    history: list[dict[str, str]] | None = None,
    language: str = "English",
) -> str:
    """Send one AI help request to the provider with the user's key. Blocking.

    Raises :class:`OwnKeyError` with a sentence written for a person.
    """
    from quill.core.assistant_ai import (
        AssistantConnectionSettings,
        default_host_for_provider,
        generate_assistant_response,
        load_provider_api_key,
    )

    inferred = infer_provider_from_model(model)
    active_prov = provider.strip().lower() or (
        inferred if inferred and load_provider_api_key(inferred) else active_own_key_provider()
    )
    key = load_provider_api_key(active_prov)
    if not key:
        for fallback_prov in OWN_KEY_PROVIDERS:
            fallback_key = load_provider_api_key(fallback_prov)
            if fallback_key:
                active_prov = fallback_prov
                key = fallback_key
                break
    if not key:
        prov_name = "Google Gemini" if active_prov == "gemini" else "OpenAI"
        raise OwnKeyError(
            f"No {prov_name} key is stored on this computer or set in the environment."
        )
    system, user = request_for(feature, prompt, chunks, history, language)
    connection = AssistantConnectionSettings(
        provider=active_prov,
        host=default_host_for_provider(active_prov),
        model=model.strip() or default_model(active_prov),
    )
    # No answer ceiling: the model's own maximum is the only one.
    text, error = generate_assistant_response(
        connection,
        key,
        user,
        max_tokens=None,
        system_prompt=system,
    )
    if error or not text:
        prov_display = "Google Gemini" if active_prov == "gemini" else "OpenAI"
        raise OwnKeyError(f"{prov_display} did not answer: {error or 'the answer was empty'}.")
    return text.strip()


def size_warning(text: str, model: str, *, free_limit_tokens: int, provider: str = "") -> str:
    """What sending *text* with the user's own key means, before it is sent.

    Never a refusal. Always the rough cost of sending it, because that is the
    thing an allowance used to answer for them; more than that only when it is
    true: that this is more than the free service would take, and that it may
    be more than *model* can read at once. The answer is not limited either,
    and costs extra -- said once, here, rather than discovered on the bill.
    """
    from quill.core.ai.gateway_context import estimate_tokens, words_in
    from quill.core.ai.own_key_models import estimate_for

    target_prov = (
        provider.strip().lower() or infer_provider_from_model(model) or active_own_key_provider()
    )
    provider_name = "Google Gemini" if target_prov == "gemini" else "OpenAI"
    tokens = estimate_tokens(text)
    words = words_in(text)
    cost = tokens * estimate_for(model, provider=target_prov).input_per_million / 1_000_000
    spent = "less than 1 cent" if cost < 0.01 else f"about ${cost:,.2f}"
    parts = [
        f"Your own key has no limits. Sending these {words:,} words costs {spent} "
        f"on your {provider_name} account with {model}, plus the answer, which is not "
        "limited in length."
    ]
    if tokens > free_limit_tokens:
        parts.append("This is more than QUILL's free AI would accept.")
    if tokens > CONTEXT_WARNING_TOKENS:
        parts.append(
            f"It may be more than the model can read at once; if so, {provider_name} "
            "refuses it and nothing is charged."
        )
    return " ".join(parts)


def describe_image_with_own_key(
    path: Any,
    question: str = "",
    *,
    provider: str = "gemini",
    model: str = "",
) -> str:
    """Describe an image using the user's own API key (e.g. Gemini vision)."""
    from pathlib import Path

    from quill.core.ai.vision import describe_image as vision_describe
    from quill.core.assistant_ai import (
        AssistantConnectionSettings,
        default_host_for_provider,
        load_provider_api_key,
    )

    prov = provider.strip().lower() or "gemini"
    key = load_provider_api_key(prov)
    conn = AssistantConnectionSettings(
        provider=prov,
        host=default_host_for_provider(prov),
        model=model.strip() or default_model(prov),
    )
    prompt = question or "Describe this image in detail."
    text, err = vision_describe(conn, key, Path(path), prompt=prompt)
    if err or not text:
        raise ValueError(err or "Google Gemini returned an empty description.")
    return text
