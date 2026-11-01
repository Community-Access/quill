"""AI help on My GitHub Copilot: the same features, the same words (codex.md 10A.12).

The counterpart of :mod:`quill.core.ai.chatgpt_ai_help` for the Copilot route.
QUILL's free service, an own key and the ChatGPT plan already share one set of
instructions (:data:`quill.core.ai.own_key.INSTRUCTIONS`); this sends those very
instructions to Copilot through :class:`~quill.core.ai.copilot_chat.CopilotChat`,
so a summary is the same summary whichever way it goes.

* **Single requests** use ``CopilotChat.ask`` (``send_and_wait``).
* **A conversation** resends the local history with every turn
  (``CopilotChat.converse``); nothing is kept anywhere but the app's window.
* **Ask About an Image** reads and checks the picture with the plan's own
  :func:`quill.core.ai.chatgpt_client.image_part`, so a bad file is the same
  sentence on every route, then attaches it as a blob. Whether the chosen model
  sees is the capability registry's question, asked before this is called.

Every call blocks: run it on a worker thread and hand the answer back with
``wx.CallAfter``. Failures are :class:`~quill.core.ai.copilot_chat.CopilotChatError`
subclasses whose ``sentence`` is said once; nothing here retries or switches
(10A.5). wx-free and strict-typed.
"""

from __future__ import annotations

import base64
from collections.abc import Callable, Sequence
from pathlib import Path

from quill.core.ai.copilot_chat import ChatTurn, CopilotChat, CopilotChatError, CopilotImage

__all__ = [
    "ask_with_copilot",
    "converse_with_copilot",
    "copilot_image",
    "describe_image_with_copilot",
]


def ask_with_copilot(
    chat: CopilotChat,
    feature: str,
    prompt: str,
    chunks: list[str] | None = None,
    *,
    language: str = "English",
    on_delta: Callable[[str], None] | None = None,
    stop: Callable[[], bool] | None = None,
) -> str:
    """One AI help request on Copilot. Blocking; raises a coded error."""
    from quill.core.ai.own_key import OwnKeyError, request_for

    try:
        instructions, user = request_for(feature, prompt, chunks, None, language)
    except OwnKeyError as error:
        said = str(error.args[0]) if error.args else "That is not available."
        raise CopilotChatError(said) from error
    if on_delta is not None:
        return chat.stream(user, on_delta=on_delta, system=instructions, stop=stop).text
    return chat.ask(user, system=instructions).text


def converse_with_copilot(
    chat: CopilotChat,
    prompt: str,
    chunks: list[str] | None,
    history: Sequence[dict[str, str]],
    *,
    instructions: str = "",
    on_delta: Callable[[str], None] | None = None,
    stop: Callable[[], bool] | None = None,
) -> str:
    """One conversation turn, the local history written ahead of the new message.

    Document excerpts, when there are any, go before the new message as the
    plan's route sends them; *instructions* replaces the editors' conversation
    instructions when an app has its own.
    """
    from quill.core.ai.own_key import INSTRUCTIONS

    turns = [
        ChatTurn(
            "assistant" if turn.get("role") == "assistant" else "user",
            str(turn.get("content", "") or ""),
        )
        for turn in history
    ]
    message = prompt
    if chunks:
        excerpts = "\n\n---\n\n".join(chunks)
        message = f"Excerpts from the user's document:\n{excerpts}\n\n{prompt}"
    answer = chat.converse(
        turns,
        message,
        system=instructions or INSTRUCTIONS["chat"],
        on_delta=on_delta,
        stop=stop,
    )
    return answer.text


def copilot_image(path: Path) -> CopilotImage:
    """*path* as a picture Copilot can take, checked the way the plan checks it.

    Raises ``ValueError`` with a sentence for a person when the file is
    missing, empty, not an image, or not a JPEG, PNG, WebP or GIF.
    """
    from quill.core.ai.chatgpt_client import image_part

    part = image_part(path)
    url = str(part.get("image_url", ""))
    head, _comma, data = url.partition(",")
    mime = head.removeprefix("data:").removesuffix(";base64")
    return CopilotImage(base64.b64decode(data), mime, Path(path).name)


def describe_image_with_copilot(chat: CopilotChat, path: Path, question: str = "") -> str:
    """Ask About an Image on Copilot: the picture as an attachment, and the question.

    The file is read and checked here, on the worker, so a bad file is a
    sentence (``ValueError``) rather than a failed request.
    """
    from quill.core.ai.chatgpt_ai_help import IMAGE_INSTRUCTIONS

    image = copilot_image(path)
    text = question.strip() or "Describe this image."
    return chat.ask(text, system=IMAGE_INSTRUCTIONS, images=(image,)).text
