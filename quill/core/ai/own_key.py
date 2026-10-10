"""AI help with the user's own API key: no allowance, no QUILL server.

The AI help features normally go through QUILL's free service, which keeps
an allowance per person and a size limit per request. Somebody with their own
OpenAI or Google Gemini account can switch that off: the same features then go
**straight from this computer to the provider they chose**, billed to their
account, with no QUILL server in between and none of the free tier's limits.

**The provider is chosen, never guessed** (qc.md X-07). The person picks OpenAI
or Google Gemini in Use My Own API Key, and that choice -- ``ai_own_key_provider``
-- is the only thing that decides where a request goes. Nothing is inferred
from a model's name, and nothing falls back from one provider to the other: a
request on Gemini with no Gemini key saved is refused with a sentence, even when
an OpenAI key is sitting in the store, because sending somebody's writing to a
company they did not pick is not a fallback but a leak. An empty choice means
OpenAI, the only provider there was when the first keys were saved, so nobody
who consented then is moved anywhere now. PR #1615 proposed inferring Gemini
from a model name with a fallback to any stored key; that half was not taken.

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
* **The same key store as QUILL.** Each provider's key lives where QUILL's AI
  Hub keeps that provider's key (Windows Credential Manager, or an encrypted
  file in a portable copy), one entry per provider, so a key entered in either
  program works in both and saving one never overwrites the other.
* **The same client.** OpenAI requests go through
  :func:`quill.core.assistant_ai.generate_assistant_response` -- QUILL's own
  provider code, plain HTTPS, certificate-checked, with retries. Gemini requests
  stream from ``streamGenerateContent`` (:mod:`quill.core.ai.own_key_gemini`),
  built from the same pure request builders, so a person can stop one part way.

wx-free.
"""

from __future__ import annotations

from typing import Any

from quill.core.ai import word_tools
from quill.core.ai.gateway_client import GatewayLimits
from quill.core.error_codes import CodedError

__all__ = [
    "CONTEXT_WARNING_TOKENS",
    "INSTRUCTIONS",
    "OWN_KEY_LIMITS",
    "UNLIMITED",
    "GEMINI",
    "OWN_KEY_PROVIDER",
    "OWN_KEY_PROVIDERS",
    "PROVIDER_NAMES",
    "OwnKeyCancelled",
    "OwnKeyError",
    "OwnKeyRejected",
    "ask_with_own_key",
    "chosen_model",
    "chosen_provider",
    "conversation_note",
    "default_model",
    "describe_image_with_own_key",
    "has_own_key",
    "key_url",
    "load_settings_fields",
    "normalize_provider",
    "own_key_active",
    "provider_for",
    "provider_name",
    "request_for",
    "scrub",
    "size_warning",
    "usage_url",
]

#: The first own-key provider, and what an empty ``ai_own_key_provider`` means.
OWN_KEY_PROVIDER = "openai"
GEMINI = "gemini"

#: Every provider an own key can be for, in the order the window offers them.
OWN_KEY_PROVIDERS: tuple[str, ...] = (OWN_KEY_PROVIDER, GEMINI)

#: Each provider as a person hears it.
PROVIDER_NAMES: dict[str, str] = {OWN_KEY_PROVIDER: "OpenAI", GEMINI: "Google Gemini"}

#: Whose account each provider bills, for the cost sentences.
_ACCOUNT_NAMES: dict[str, str] = {OWN_KEY_PROVIDER: "OpenAI", GEMINI: "Google Gemini"}
_KEY_URLS = {
    OWN_KEY_PROVIDER: "platform.openai.com, under API keys",
    GEMINI: "aistudio.google.com/apikey (Google AI Studio)",
}
_USAGE_URLS = {
    OWN_KEY_PROVIDER: "https://platform.openai.com/usage",
    GEMINI: "https://aistudio.google.com/usage",
}

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
    # Direct-only: word tools never spend a free hosted request.
    word_tools.FEATURE: word_tools.INSTRUCTIONS,
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
        "Check the provider, the key and the model in Use My Own API Key, and that "
        "the account has credit. Or switch back to QUILL's free AI there."
    )


class OwnKeyRejected(OwnKeyError):
    """The provider refused the saved key itself (wrong, revoked or restricted)."""

    code = "QUILL-AI-OWN-KEY-REJECTED"
    user_hint = (
        "Paste the key again in Use My Own API Key and press Test the Key, or create "
        "a new key on the provider's website."
    )


class OwnKeyCancelled(OwnKeyError):
    """The person stopped the request; nothing more is read or shown."""

    code = "QUILL-AI-OWN-KEY-CANCELLED"
    user_hint = ""


def provider_name(provider: str) -> str:
    """*provider* as a person hears it: "OpenAI", "Google Gemini"."""
    return PROVIDER_NAMES.get(provider, provider)


def normalize_provider(value: object) -> str:
    """A supported provider, defaulting old or invalid preference data to OpenAI."""
    text = str(value or "").strip().lower()
    return text if text in OWN_KEY_PROVIDERS else OWN_KEY_PROVIDER


def provider_for(settings: Any = None) -> str:
    """Compatibility accessor for persisted preferences predating strict routing."""
    return normalize_provider(getattr(settings, "ai_own_key_provider", ""))


def key_url(provider: str) -> str:
    """Where a key for *provider* is created, as readable text."""
    return _KEY_URLS[normalize_provider(provider)]


def usage_url(provider: str) -> str:
    """Where the provider reports usage and charges."""
    return _USAGE_URLS[normalize_provider(provider)]


def chosen_provider(settings: Any = None) -> str:
    """The provider the person chose, or "" when the saved choice is not one.

    Empty means OpenAI (see the module docstring). A value that is neither --
    a hand-edited file, a newer copy's provider -- is *no* provider rather
    than a guess, so nothing is sent anywhere on its account.
    """
    raw = str(getattr(settings, "ai_own_key_provider", "") or "").strip().lower()
    if not raw:
        return OWN_KEY_PROVIDER
    return raw if raw in OWN_KEY_PROVIDERS else ""


def default_model(provider: str = OWN_KEY_PROVIDER) -> str:
    from quill.core.assistant_ai import default_model_for_provider

    return default_model_for_provider(provider)


def chosen_model(settings: Any = None) -> str:
    """The model own-key requests use: the saved one, else the provider's default."""
    saved = str(getattr(settings, "ai_own_key_model", "") or "").strip()
    return saved or default_model(chosen_provider(settings) or OWN_KEY_PROVIDER)


def has_own_key(provider: str = OWN_KEY_PROVIDER) -> bool:
    """Whether *provider*'s key is stored (or set in the environment)."""
    from quill.core.assistant_ai import load_provider_api_key

    try:
        return bool(load_provider_api_key(provider))
    except Exception:  # noqa: BLE001 - an unreadable store is "no key"
        return False


def own_key_active(settings: Any = None) -> bool:
    """Whether AI help uses the user's key: whenever the chosen provider has one.

    There is deliberately no separate switch. A saved key lifts every limit;
    removing it (Use My Own API Key, Remove the Saved Key) is how a person goes
    back to the free service. Only the *chosen* provider's key counts: an
    OpenAI key does not make the route active while Gemini is chosen.
    """
    provider = chosen_provider(settings)
    return bool(provider) and has_own_key(provider)


def load_settings_fields(data: Any) -> dict[str, Any]:
    """The own-key settings from saved JSON, for QUILL's settings loader."""
    return {
        "ai_own_key_model": str(data.get("ai_own_key_model", "") or ""),
        "ai_own_key_provider": normalize_provider(data.get("ai_own_key_provider", "")),
    }


def scrub(text: str, key: str) -> str:
    """*text* with *key* taken out, for any sentence that might quote a reply."""
    secret = (key or "").strip()
    return text.replace(secret, "[your key]") if len(secret) >= 4 else text


def conversation_note(provider: str) -> str:
    """What a conversation costs on an own key, said once at the top of its window."""
    account = _ACCOUNT_NAMES.get(provider, provider_name(provider))
    return (
        f"This conversation uses your own {provider_name(provider)} key: no limits, "
        f"billed to your {account} account. The whole conversation goes with each "
        "message, so a long one costs more per reply."
    )


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


def _stop_if_cancelled(cancel: Any) -> None:
    if cancel is not None and cancel.is_set():
        raise OwnKeyCancelled("Stopped. Nothing more will arrive from this request.")


def ask_with_own_key(
    feature: str,
    prompt: str,
    chunks: list[str] | None = None,
    *,
    model: str = "",
    history: list[dict[str, str]] | None = None,
    language: str = "English",
    provider: str = OWN_KEY_PROVIDER,
    cancel: Any = None,
) -> str:
    """Send one AI help request to *provider* with the user's key. Blocking.

    *provider* is the person's choice (:func:`chosen_provider`) and is never
    second-guessed: only that provider's key is read, and only that provider
    is asked. *cancel* is a ``threading.Event``; once set, the request is
    abandoned -- before sending, between the pieces of a Gemini answer, and
    after an OpenAI answer arrives -- and :class:`OwnKeyCancelled` is raised.

    Raises :class:`OwnKeyError` (or a subclass) with a sentence written for a
    person, which never contains the key.
    """
    from quill.core.assistant_ai import (
        AssistantConnectionSettings,
        default_host_for_provider,
        generate_assistant_response,
        load_provider_api_key,
    )

    provider = (provider or "").strip().lower()
    if provider not in OWN_KEY_PROVIDERS:
        raise OwnKeyError(
            "No provider is chosen for your own key. Choose OpenAI or Google Gemini "
            "in Use My Own API Key."
        )
    name = provider_name(provider)
    _stop_if_cancelled(cancel)
    key = load_provider_api_key(provider)
    if not key:
        raise OwnKeyError(
            f"No {name} key is saved on this computer. Add one in Use My Own API Key, "
            "or choose another provider there."
        )
    system, user = request_for(feature, prompt, chunks, history, language)
    chosen = model.strip() or default_model(provider)
    if provider == GEMINI:
        from quill.core.ai.own_key_gemini import stream_answer

        return stream_answer(key, chosen, system, user, cancel=cancel)
    connection = AssistantConnectionSettings(
        provider=provider, host=default_host_for_provider(provider), model=chosen
    )
    # No answer ceiling: the model's own maximum is the only one.
    text, error = generate_assistant_response(
        connection,
        key,
        user,
        max_tokens=None,
        system_prompt=system,
    )
    _stop_if_cancelled(cancel)  # it arrived after Stop: not shown
    if error or not text:
        reason = scrub(error or "the answer was empty", key)
        raise OwnKeyError(f"{name} did not answer: {reason}.")
    return text.strip()


def describe_image_with_own_key(
    path: Any, question: str = "", *, provider: str = GEMINI, model: str = ""
) -> str:
    """Ask About an Image on the listener's own key. Blocking."""
    from pathlib import Path

    from quill.core.ai.vision import describe_image
    from quill.core.assistant_ai import (
        AssistantConnectionSettings,
        default_host_for_provider,
        load_provider_api_key,
    )

    chosen = (provider or "").strip().lower()
    if chosen not in OWN_KEY_PROVIDERS:
        raise OwnKeyError("No provider is chosen for your own key. Nothing was sent.")
    name = provider_name(chosen)
    key = load_provider_api_key(chosen)
    if not key:
        raise OwnKeyError(f"No {name} key is saved on this computer. Nothing was sent.")
    connection = AssistantConnectionSettings(
        provider=chosen,
        host=default_host_for_provider(chosen),
        model=model.strip() or default_model(chosen),
    )
    try:
        text, error = describe_image(
            connection,
            key,
            Path(str(path)),
            prompt=question or "Describe this image in detail.",
        )
    except Exception as exc:  # noqa: BLE001 - one actionable sentence for the UI
        raise OwnKeyError(f"{name} could not describe the image: {scrub(str(exc), key)}") from exc
    if error or not text:
        reason = scrub(error or "the answer was empty", key)
        raise OwnKeyError(f"{name} did not describe the image: {reason}.")
    return str(text).strip()


def size_warning(
    text: str, model: str, *, free_limit_tokens: int, provider: str = OWN_KEY_PROVIDER
) -> str:
    """What sending *text* with the user's own key means, before it is sent.

    Never a refusal. Always the rough cost of sending it, because that is the
    thing an allowance used to answer for them; more than that only when it is
    true: that this is more than the free service would take, and that it may
    be more than *model* can read at once. The answer is not limited either,
    and costs extra -- said once, here, rather than discovered on the bill.
    """
    from quill.core.ai.gateway_context import estimate_tokens, words_in
    from quill.core.ai.own_key_models import estimate_for

    tokens = estimate_tokens(text)
    words = words_in(text)
    cost = tokens * estimate_for(model, provider).input_per_million / 1_000_000
    spent = "less than 1 cent" if cost < 0.01 else f"about ${cost:,.2f}"
    account = _ACCOUNT_NAMES.get(provider, provider_name(provider))
    parts = [
        f"Your own key has no limits. Sending these {words:,} words costs {spent} "
        f"on your {account} account with {model}, plus the answer, which is not "
        "limited in length."
    ]
    if tokens > free_limit_tokens:
        parts.append("This is more than QUILL's free AI would accept.")
    if tokens > CONTEXT_WARNING_TOKENS:
        parts.append(
            f"It may be more than the model can read at once; if so, {account} "
            "refuses it and nothing is charged."
        )
    return " ".join(parts)
