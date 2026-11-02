"""The plain parts of the Copilot hosted-AI route: data, errors and pure helpers.

Split from :mod:`quill.core.ai.copilot_chat` (which re-exports every name) so
each module stays under the size budget: here is everything that needs no
SDK, no client and no event loop -- the answer and model records, the 10A.5
errors and :func:`classify_failure`, blob attachments, the resent
conversation, and the ``models.list`` reading with Copilot Free's Auto row.

wx-free and strict-typed.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError

__all__ = [
    "AUTO_MODEL",
    "AUTO_MODEL_NAME",
    "FAILED",
    "IMAGE_TYPES",
    "LIMIT",
    "NOT_FOR_ACCOUNT",
    "REVOKED",
    "VISION_SOURCE",
    "ChatTurn",
    "CopilotAnswer",
    "CopilotChatError",
    "CopilotImage",
    "CopilotLimitReached",
    "CopilotModel",
    "CopilotModelList",
    "CopilotNotForAccount",
    "CopilotRefused",
    "CopilotSignInEnded",
    "attachments_for",
    "classify_failure",
    "conversation_prompt",
    "enum_text",
    "event_type",
    "models_from_info",
]

#: The model id that lets Copilot choose; what Copilot Free is limited to.
AUTO_MODEL = "auto"
#: The model row's words when the plan allows only Auto (10A.4).
AUTO_MODEL_NAME = "Auto (Copilot Free chooses)"

#: Picture types Copilot accepts as attachments (codex.md 2B.6).
IMAGE_TYPES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})

#: Where a per-model "sees pictures" claim comes from (GATE-CAPS needs a source).
VISION_SOURCE = "Copilot SDK models.list: ModelInfo.capabilities.supports.vision"

# -- outcomes (10A.5) ------------------------------------------------------------ #

REVOKED = "revoked"
LIMIT = "limit"
NOT_FOR_ACCOUNT = "not_for_account"
FAILED = "failed"


class CopilotChatError(CodedError):
    """A Copilot request failed; :attr:`sentence` is what the app says."""

    code = "QUILL-AI-COPILOT-CHAT-FAILED"
    user_hint = "Try again, or press Ctrl+4 to choose another AI."
    outcome = FAILED

    def __init__(self, sentence: str, *, detail: str = "") -> None:
        super().__init__(sentence)
        self.sentence = sentence
        self.detail = detail


class CopilotSignInEnded(CopilotChatError):
    """GitHub refused the token (a 401, revoked or expired). Nothing was sent."""

    code = "QUILL-AI-COPILOT-SIGNIN-ENDED"
    user_hint = "Press Ctrl+4 to sign in again or choose another."
    outcome = REVOKED


class CopilotLimitReached(CopilotChatError):
    """The account's Copilot quota is spent. Never retried, never switched."""

    code = "QUILL-AI-COPILOT-LIMIT"
    user_hint = "Manage usage is in the Usage window."
    outcome = LIMIT


class CopilotNotForAccount(CopilotChatError):
    """An organisation or plan has Copilot switched off for this account (R15)."""

    code = "QUILL-AI-COPILOT-POLICY-OFF"
    user_hint = "Press Ctrl+4 to choose another AI."
    outcome = NOT_FOR_ACCOUNT


class CopilotRefused(CopilotChatError):
    """Refused before anything started: Safe Mode, or a call on the UI thread."""

    code = "QUILL-AI-COPILOT-REFUSED"
    user_hint = "Restart without Safe Mode to use AI."


# -- plain data -------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class CopilotImage:
    """One picture to attach: its bytes and MIME type."""

    data: bytes
    mime_type: str
    name: str = ""


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """One turn of the local conversation: ``user`` or ``assistant``."""

    role: str
    text: str


@dataclass(frozen=True, slots=True)
class CopilotAnswer:
    """What came back: the text, and what the service said about the call."""

    text: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stopped: bool = False


@dataclass(frozen=True, slots=True)
class CopilotModel:
    """One model as the list reads it, in the service's own order."""

    id: str
    name: str
    vision: bool = False


@dataclass(frozen=True, slots=True)
class CopilotModelList:
    """The models this account may choose; ``auto_only`` for Copilot Free."""

    models: tuple[CopilotModel, ...] = field(default_factory=tuple)
    auto_only: bool = False


# -- pure helpers -------------------------------------------------------------------- #


def attachments_for(images: Sequence[CopilotImage]) -> list[dict[str, str]]:
    """Each picture as an SDK ``blob`` attachment; refuses a type Copilot cannot take."""
    attachments: list[dict[str, str]] = []
    for image in images:
        mime = image.mime_type.strip().lower()
        if mime not in IMAGE_TYPES:
            raise ValueError(f"GitHub Copilot cannot take a picture of type {mime or 'unknown'}.")
        item = {"type": "blob", "data": base64.b64encode(image.data).decode("ascii")}
        item["mimeType"] = mime
        if image.name.strip():
            item["displayName"] = image.name.strip()
        attachments.append(item)
    return attachments


def _turn_parts(turn: ChatTurn | tuple[str, str]) -> tuple[str, str]:
    if isinstance(turn, ChatTurn):
        return turn.role, turn.text
    return str(turn[0]), str(turn[1])


def conversation_prompt(history: Sequence[ChatTurn | tuple[str, str]], prompt: str) -> str:
    """*prompt* with the local history written before it, oldest first.

    Copilot keeps no conversation for QUILL: each turn is a fresh session, so
    what was said travels with the next message.
    """
    lines: list[str] = []
    for turn in history:
        role, text = _turn_parts(turn)
        if not text.strip():
            continue
        who = "Assistant" if role.strip().lower() == "assistant" else "User"
        lines.append(f"{who}: {text.strip()}")
    if not lines:
        return prompt
    return (
        "Here is our conversation so far, oldest first.\n\n"
        + "\n\n".join(lines)
        + f"\n\nMy next message:\n{prompt}"
    )


def _words(*values: object) -> str:
    return " ".join(str(v) for v in values if v).lower()


def classify_failure(
    *,
    status_code: int | None = None,
    error_type: str = "",
    error_code: str = "",
    message: str = "",
    remediation: str = "",
) -> str:
    """Which 10A.5 outcome a failure is: revoked, limit, not for account, or failed."""
    words = _words(error_type, error_code, message)
    action = remediation.strip().lower()
    if (
        status_code == 401
        or action == "sign_in"
        or any(k in words for k in ("unauthorized", "bad credentials", "authentication"))
        or any(k in words for k in ("token expired", "token revoked", "invalid token"))
    ):
        return REVOKED
    if status_code in (402, 429) or any(
        k in words for k in ("quota", "rate_limit", "rate limit", "limit_exceeded", "usage limit")
    ):
        return LIMIT
    if (
        status_code == 403
        or action == "switch_account"
        or any(k in words for k in ("policy", "not enabled", "disabled by", "no access"))
        or "not have access" in words
    ):
        return NOT_FOR_ACCOUNT
    return FAILED


def enum_text(value: object) -> str:
    return str(getattr(value, "value", value) or "")


def event_type(event: object) -> str:
    return enum_text(getattr(event, "type", ""))


def _usable(info: Any) -> bool:
    policy = getattr(info, "policy", None)
    state = str(getattr(policy, "state", "enabled") or "enabled").lower() if policy else "enabled"
    return state == "enabled"


def models_from_info(infos: Sequence[Any]) -> CopilotModelList:
    """The SDK's ``ModelInfo`` list as :class:`CopilotModelList`, order kept.

    Only models whose policy is enabled (or that carry none) are listed. When
    nothing but Auto is usable -- Copilot Free -- the list is the one Auto row.
    """
    models: list[CopilotModel] = []
    for info in infos:
        model_id = str(getattr(info, "id", "") or "").strip()
        if not model_id or not _usable(info):
            continue
        supports = getattr(getattr(info, "capabilities", None), "supports", None)
        models.append(
            CopilotModel(
                id=model_id,
                name=str(getattr(info, "name", "") or model_id),
                vision=bool(getattr(supports, "vision", False)),
            )
        )
    if all(m.id == AUTO_MODEL for m in models):
        vision = any(m.vision for m in models)
        return CopilotModelList((CopilotModel(AUTO_MODEL, AUTO_MODEL_NAME, vision),), True)
    return CopilotModelList(tuple(models), False)
