"""Screenshot prompts, grounded questions and opt-in automatic analysis.

Uses the shared vision prompt library and provider transport. No UI imports,
no independent model engine and no automatic capture or upload on import.
"""

from __future__ import annotations

import hashlib
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.ai.vision_prompts import enabled_style_choices, resolve_prompt_text
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic
from quill.core.studio_capture import INSPECTION_PROMPT, CaptureEvidence

if TYPE_CHECKING:
    from quill.core.assistant_ai import AssistantConnectionSettings


SCREENSHOT_PROMPTS: dict[str, tuple[str, str]] = {
    "screen-overview": (
        "Screenshot: orientation and overview",
        "Give a brief overview, then describe layout from top to bottom. Identify the likely "
        "application and purpose only when supported by visible evidence. Read important headings, "
        "selected items, dialogs, errors and current state. End with uncertainties and useful "
        "follow-up questions for a blind user.",
    ),
    "screen-controls": (
        "Screenshot: controls and navigation",
        "Describe visible controls in reading order, with their text, apparent type, selected or "
        "disabled state, and location in familiar terms such as top, bottom, left or right. "
        "Include coordinates only as optional supporting detail. "
        "Explain what each appears to do. "
        "Do not invent shortcuts, accessibility names, focus, or keyboard operability from pixels. "
        "Flag anything obscured or ambiguous.",
    ),
    "screen-text": (
        "Screenshot: text, errors and tables",
        "Transcribe visible text in reading order. Preserve error codes, punctuation and numbers. "
        "Label unreadable or uncertain characters instead of completing them. Reconstruct visible "
        "tables with their headers and row associations. Distinguish exact transcription from "
        "your explanation. State where content is cut off.",
    ),
    "screen-quality": (
        "Screenshot: framing and capture problems",
        "Inspect for clipping, offscreen content, blank or protected areas, tooltips, dialogs, "
        "notifications, overlapping windows, cursor obstruction and text too small to read. "
        "Give plain-language directions and specific corrective suggestions, such as choosing "
        "the whole named window to retain context; coordinates are optional detail. Distinguish "
        "visible problems from concerns that require a fresh capture or human judgment.",
    ),
    "screen-privacy": (
        "Screenshot: possible sensitive information",
        "Flag possible names, addresses, emails, tokens, credentials, financial or health details, "
        "private messages and unrelated windows. Refer to locations and categories without "
        "unnecessarily repeating sensitive text. Suggest redactions. Explicitly say this is an "
        "uncertain review of an image already sent to the provider, not proof of safe sharing.",
    ),
    "screen-alt": (
        "Screenshot: alt text and extended description",
        "Draft concise alt text focused on the screenshot's purpose, then a separate extended "
        "description covering layout, significant text and relevant states. Avoid filenames, "
        "'image of', unsupported conclusions and redundant decoration. Mark uncertain readings. "
        "Ask what the author wants to communicate if the purpose is ambiguous.",
    ),
    "screen-chart": (
        "Screenshot: chart or diagram explanation",
        "Identify the chart or diagram type, title, axes, units, legend and relationships. "
        "Describe trends and read visible values, marking estimates explicitly. Explain colors "
        "and patterns in words. Do not invent missing data or infer causality. Provide an "
        "accessible textual reconstruction when the available evidence supports one.",
    ),
}


def prompt_choices(settings: Any) -> list[dict[str, str]]:
    return [
        {"id": key, "title": value[0]} for key, value in SCREENSHOT_PROMPTS.items()
    ] + enabled_style_choices(
        disabled_builtins=settings.vision_disabled_builtin_styles,
        custom_prompts=settings.vision_custom_prompts,
    )


def capture_prompt(prompt_id: str, settings: Any) -> str:
    if prompt_id in SCREENSHOT_PROMPTS:
        return SCREENSHOT_PROMPTS[prompt_id][1]
    return resolve_prompt_text(
        prompt_id,
        custom_prompts=settings.vision_custom_prompts,
        overrides=settings.vision_builtin_overrides,
    )


def load_capture_ai_preferences() -> dict[str, Any]:
    raw = read_json(app_data_dir() / "studio-capture-ai.json", {})
    return raw if isinstance(raw, dict) else {}


def save_capture_ai_preferences(preferences: dict[str, Any]) -> None:
    write_json_atomic(app_data_dir() / "studio-capture-ai.json", preferences)


def connection_identity(connection: AssistantConnectionSettings) -> dict[str, str]:
    from quill.core.assistant_ai import default_host_for_provider, default_model_for_provider

    provider = connection.provider.strip().lower()
    return {
        "provider": provider,
        "host": (connection.host.strip() or default_host_for_provider(provider)).rstrip("/"),
        "model": connection.model.strip() or default_model_for_provider(provider),
    }


def auto_ai_allowed(
    preferences: dict[str, Any],
    connection: AssistantConnectionSettings,
    *,
    ai_enabled: bool,
    safe_mode: bool,
) -> bool:
    return bool(
        ai_enabled
        and not safe_mode
        and connection.provider.strip().lower() != "off"
        and preferences.get("auto_ai_enabled") is True
        and preferences.get("approved_connection") == connection_identity(connection)
    )


def inspect_screenshot(
    evidence: CaptureEvidence,
    *,
    connection: AssistantConnectionSettings | None,
    instructions: str = "",
    question: str = "",
    history: str = "",
    cancellation_token: Any = None,
    can_send: Callable[[], bool] | None = None,
) -> str:
    """Analyze an immutable copy; cloud receives only the reviewed artifact."""
    raw = Path(evidence.path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != evidence.sha256:
        raise ValueError("Screenshot changed. Capture it again before inspection.")
    if cancellation_token is not None:
        cancellation_token.raise_if_cancelled()
    with tempfile.TemporaryDirectory(prefix="quill-inspect-") as folder:
        snapshot = Path(folder) / "capture.png"
        snapshot.write_bytes(raw)
        if connection is None:
            from quill.io.ocr import ocr_image

            result = ocr_image(snapshot)
            confidences = [
                f"Line {i}: "
                + (f"{line.confidence:g}%" if line.confidence >= 0 else "not reported")
                for i, line in enumerate(getattr(result, "lines", []), 1)
            ]
            return (
                f"Local OCR ({result.engine}); recognition may be incorrect.\n{result.text}\n"
                "Confidence by line: "
                + ("; ".join(confidences) or "not reported")
                + "\nElement coordinates and keyboard semantics "
                "are not supplied by this OCR result."
            )
        from quill.core.ai.model_manager import load_ai_enabled
        from quill.core.ai.vision import describe_image
        from quill.core.assistant_ai import load_keyed_provider_api_key

        if not load_ai_enabled():
            raise RuntimeError("AI was disabled before the screenshot was sent.")
        if cancellation_token is not None:
            cancellation_token.raise_if_cancelled()
        prompt = INSPECTION_PROMPT + "\nSelected instructions:\n" + instructions
        if history:
            prompt += (
                "\nEarlier conversation about this exact artifact (unverified):\n"
                + history[-18000:]
            )
        if question:
            prompt += "\nUser question:\n" + question
        key = load_keyed_provider_api_key(connection.provider)
        if can_send is not None and not can_send():
            raise RuntimeError("Automatic screenshot AI permission changed before sending.")
        text, error = describe_image(connection, key, snapshot, prompt=prompt, max_tokens=3000)
        if error:
            raise RuntimeError(error)
        identity = connection_identity(connection)
        return (
            f"AI ({identity['provider']}, {identity['model']}); uncertain.\n"
            f"Question: {question or 'Inspect screenshot'}\n{text or 'No response.'}"
        )
