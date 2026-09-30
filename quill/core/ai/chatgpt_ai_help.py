"""AI help on a ChatGPT subscription: the same features, the same words.

The third way a request can travel. QUILL's free service and the user's own
OpenAI key already share one set of instructions
(:data:`quill.core.ai.own_key.INSTRUCTIONS`, the gateway's own templates); this
route sends those very instructions to the Responses API on the person's plan,
so a summary is the same summary whichever way it goes. What differs is only
what the plan makes possible: **images**, which neither of the other two routes
carries, and OpenAI's own **web search**, offered to the model only when the
person has switched it on.

Two things are decided here and nowhere else:

* **What "the plan's limits" means for the pad.** Nothing QUILL can see. The
  plan has its own usage limits, enforced by OpenAI and reported back as a
  coded error when they are reached; so the pad is told the same unlimited
  figures an own key gets and warns about size instead of refusing.
* **How a request is shaped for the Responses API.** One ``user`` item whose
  content is the text and any images, with the instructions in the request's
  own ``instructions`` field rather than a system message.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from quill.core.ai.chatgpt_account import ChatGptAccount
from quill.core.ai.chatgpt_client import ChatGptAnswer, image_part, respond
from quill.core.ai.chatgpt_errors import ChatGptError
from quill.core.ai.gateway_client import GatewayLimits

__all__ = [
    "CHATGPT_LIMITS",
    "IMAGE_FEATURE",
    "IMAGE_INSTRUCTIONS",
    "ask_with_chatgpt",
    "converse_with_chatgpt",
    "describe_image_with_chatgpt",
    "size_note",
]

#: The feature id Ask About an Image reports itself as, for result windows.
IMAGE_FEATURE = "image"

#: What Ask About an Image sends with the picture when no question is typed.
#: Written for a blind reader, in the same voice as every other instruction.
IMAGE_INSTRUCTIONS = (
    "Describe the attached image in clear, plain language for a blind reader, "
    "suitable for a screen reader to read aloud. Lead with what the image is "
    "and what matters most in it. If it contains text, transcribe the text "
    "exactly. If the user asks a question about the image, answer that "
    "question first, then add only the description that helps. Do not use "
    "tables, and keep any formatting simple."
)


def _limits() -> GatewayLimits:
    from quill.core.ai.own_key import OWN_KEY_LIMITS

    flags = dict(OWN_KEY_LIMITS.feature_flags)
    flags[IMAGE_FEATURE] = True
    return GatewayLimits(
        max_input_tokens=OWN_KEY_LIMITS.max_input_tokens,
        max_output_tokens=OWN_KEY_LIMITS.max_output_tokens,
        max_chunks_per_request=OWN_KEY_LIMITS.max_chunks_per_request,
        hosted_ai_enabled=True,
        feature_flags=flags,
    )


#: What the pad is told the limits are on a ChatGPT plan: every feature on,
#: images too, and no QUILL ceiling of any kind. OpenAI's own limits apply and
#: are reported as they are met.
CHATGPT_LIMITS: GatewayLimits = _limits()


def _tools(account: ChatGptAccount) -> list[dict[str, Any]]:
    return [{"type": "web_search"}] if account.web_search else []


def _user_item(text: str, images: Sequence[dict[str, Any]] = ()) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "input_text", "text": text}]
    content.extend(images)
    return {"role": "user", "content": content}


def ask_with_chatgpt(
    account: ChatGptAccount,
    feature: str,
    prompt: str,
    chunks: list[str] | None = None,
    *,
    history: list[dict[str, str]] | None = None,
    language: str = "English",
    on_delta: Callable[[str], None] | None = None,
    stop: Callable[[], bool] | None = None,
) -> str:
    """One AI help request on the plan. Blocking; raises a coded error."""
    from quill.core.ai.own_key import OwnKeyError, request_for

    try:
        instructions, user = request_for(feature, prompt, chunks, history, language)
    except OwnKeyError as error:
        said = str(error.args[0]) if error.args else "That is not available."
        raise ChatGptError(said) from error
    answer = respond(
        account.access_token(),
        model=account.model,
        items=[_user_item(user)],
        instructions=instructions,
        tools=_tools(account),
        on_delta=on_delta,
        stop=stop,
    )
    return answer.text


def converse_with_chatgpt(
    account: ChatGptAccount,
    prompt: str,
    chunks: list[str] | None,
    history: list[dict[str, str]],
    *,
    instructions: str = "",
    on_delta: Callable[[str], None] | None = None,
    stop: Callable[[], bool] | None = None,
) -> str:
    """One conversation turn on the plan, with the history as real turns.

    The Responses API takes the conversation as items rather than as one
    formatted block, so each earlier turn goes as its own ``user`` or
    ``assistant`` item and the model reads it the way it was said. Document
    excerpts, when there are any, go ahead of the first turn. *instructions*
    replaces the editors' conversation instructions when an app has its own --
    Quill Radio's assistant is a different assistant from the editor's.
    """
    from quill.core.ai.own_key import INSTRUCTIONS

    items: list[dict[str, Any]] = []
    if chunks:
        items.append(
            _user_item("Excerpts from the user's document:\n" + "\n\n---\n\n".join(chunks))
        )
    for turn in history:
        role = "assistant" if turn.get("role") == "assistant" else "user"
        text = str(turn.get("content", "") or "")
        if role == "assistant":
            items.append({"role": "assistant", "content": [{"type": "output_text", "text": text}]})
        else:
            items.append(_user_item(text))
    items.append(_user_item(prompt))
    answer: ChatGptAnswer = respond(
        account.access_token(),
        model=account.model,
        items=items,
        instructions=instructions or INSTRUCTIONS["chat"],
        tools=_tools(account),
        on_delta=on_delta,
        stop=stop,
    )
    return answer.text


def describe_image_with_chatgpt(
    account: ChatGptAccount,
    path: Path,
    question: str = "",
    *,
    on_delta: Callable[[str], None] | None = None,
    stop: Callable[[], bool] | None = None,
) -> str:
    """Ask About an Image: the picture, and the question if there is one.

    The file is read and checked here, on the worker, so a bad file is a
    sentence rather than a failed request. Raises ``ValueError`` for the file
    and a coded error for everything after it.
    """
    part = image_part(path)
    text = question.strip() or "Describe this image."
    answer = respond(
        account.access_token(),
        model=account.model,
        items=[_user_item(text, [part])],
        instructions=IMAGE_INSTRUCTIONS,
        tools=_tools(account),
        on_delta=on_delta,
        stop=stop,
    )
    return answer.text


def size_note(text: str, model: str, *, free_limit_tokens: int) -> str:
    """What sending *text* on the plan means, said before it is sent.

    Never a refusal, and never a price: a plan is paid for already, and what
    it costs is a share of the plan's usage that OpenAI counts and QUILL
    cannot see. What is worth saying is when this is more than the free
    service would take, and when it may be more than the model can read.
    """
    from quill.core.ai.gateway_context import estimate_tokens, words_in
    from quill.core.ai.own_key import CONTEXT_WARNING_TOKENS

    tokens = estimate_tokens(text)
    words = words_in(text)
    which = model or "your chosen model"
    parts = [
        f"Your ChatGPT subscription has no QUILL limit. These {words:,} words go to "
        f"{which} on your plan, and count toward your plan's own usage."
    ]
    if tokens > free_limit_tokens:
        parts.append("This is more than QUILL's free AI would accept.")
    if tokens > CONTEXT_WARNING_TOKENS:
        parts.append("It may be more than the model can read at once; if so, OpenAI refuses it.")
    return " ".join(parts)
