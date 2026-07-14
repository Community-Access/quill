"""Built-in vision prompt styles for the Image Description Toolkit (IDT).

Twelve evaluated prompt styles that produce substantially different image
descriptions depending on the use case.  Each constant holds the full prompt
text sent to the vision model.  The ``BUILTIN_PROMPT_STYLES`` list is the
canonical registry consumed by the UI picker and the Manage Image Prompts
dialog.

The prompts are immutable constants — users can disable built-in styles and
add custom prompts, but the shipped text is never edited in place.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Individual prompt constants
# ---------------------------------------------------------------------------

PROMPT_NARRATIVE = (
    "Describe this image as a narrative scene overview. "
    "Walk through the scene from left to right, describing the spatial "
    "relationships between objects and people. "
    "Include what is in the foreground, middle ground, and background. "
    "Be thorough but natural — write as if you are telling someone what "
    "they would see if they were standing in front of the image."
)

PROMPT_DETAILED = (
    "Describe this image in structured detail using these sections: "
    "SUBJECT — what or who is the main focus; "
    "SETTING — where this takes place and what surrounds the subject; "
    "COLORS — the dominant and accent colors and how they interact; "
    "COMPOSITION — how elements are arranged, framed, and balanced; "
    "DETAILS — textures, patterns, text, and small elements that matter. "
    "Be precise and thorough in each section."
)

PROMPT_CONCISE = (
    "Describe this image in two to three sentences. "
    "Cover what is shown, where it is, and what is happening. "
    "Be brief and direct — no extra commentary or interpretation."
)

PROMPT_ARTISTIC = (
    "Describe this image with attention to its visual and artistic qualities. "
    "Focus on light and shadow, color relationships and palette, texture, "
    "mood, and the overall aesthetic impression. "
    "Write as an art critic would — highlight what makes the image visually "
    "striking or emotionally resonant."
)

PROMPT_TECHNICAL = (
    "Describe this image from a technical photography perspective. "
    "Note the orientation and framing, lighting direction and quality, "
    "depth of field, composition choices, clarity and sharpness, "
    "and any strengths or limitations in the image quality. "
    "Be objective and analytical."
)

PROMPT_COLORFUL = (
    "Describe this image with rich, specific color language. "
    "Name the exact colors you see — use precise terms like crimson, "
    "teal, amber, slate, ochre rather than generic red, blue, yellow. "
    "Note the direction and quality of the light and how it affects the "
    "colors. End with a one-sentence summary of the atmosphere the "
    "colors create."
)

PROMPT_SIMPLE = (
    "Describe this image in exactly one sentence. "
    "Make it clear, direct, and informative — capture the essence "
    "of what this image shows."
)

PROMPT_ACCESSIBILITY = (
    "Describe this image in clear, plain language for a blind reader. "
    "Lead with the most important content — what is this image of? "
    "Describe the scene from left to right, noting the relative sizes "
    "and positions of people and objects. "
    "If the image contains text, transcribe it verbatim. "
    "Be concise but complete. Include details that help a blind reader "
    "understand the context, mood, and purpose of the image."
)

PROMPT_COMPARISON = (
    "Describe this image using analogies and comparisons to familiar "
    "objects and experiences. "
    "For each element, relate it to something a person might know: "
    "compare sizes to everyday objects, textures to common materials, "
    "colors to familiar things. "
    "Make the image relatable through comparison rather than abstract "
    "description."
)

PROMPT_MOOD = (
    "Describe the emotional atmosphere and psychological tone of this image. "
    "What feeling does it evoke? What mood is conveyed through the "
    "lighting, colors, expressions, and composition? "
    "Focus on the emotional impact — is it calm, tense, joyful, "
    "melancholic, mysterious, warm, cold? "
    "Describe the visual elements that create this mood."
)

PROMPT_FUNCTIONAL = (
    "Describe this image by focusing on function, purpose, and action. "
    "Use active verbs: what illuminates, supports, connects, moves, "
    "contains, directs, or transforms? "
    "Describe what each element does rather than just what it looks like. "
    "If the image shows a tool, device, or structure, explain its "
    "purpose and how its parts work together."
)

PROMPT_AIALTTEXT = (
    "Write three alternative text descriptions for this image at "
    "different lengths: "
    "1. Short (about 25 words) — the essential information for a quick scan. "
    "2. Medium (about 50 words) — a balanced description with key details. "
    "3. Long (about 100 words) — a thorough description for full context. "
    "Label each variant clearly with its word-count target. "
    "Each variant should stand alone as a complete alt-text description."
)

# ---------------------------------------------------------------------------
# Canonical registry
# ---------------------------------------------------------------------------

BUILTIN_PROMPT_STYLES: list[dict[str, str]] = [
    {"id": "narrative", "title": "Narrative", "prompt": PROMPT_NARRATIVE},
    {"id": "detailed", "title": "Detailed", "prompt": PROMPT_DETAILED},
    {"id": "concise", "title": "Concise", "prompt": PROMPT_CONCISE},
    {"id": "artistic", "title": "Artistic", "prompt": PROMPT_ARTISTIC},
    {"id": "technical", "title": "Technical", "prompt": PROMPT_TECHNICAL},
    {"id": "colorful", "title": "Colorful", "prompt": PROMPT_COLORFUL},
    {"id": "simple", "title": "Simple", "prompt": PROMPT_SIMPLE},
    {"id": "accessibility", "title": "Accessibility", "prompt": PROMPT_ACCESSIBILITY},
    {"id": "comparison", "title": "Comparison", "prompt": PROMPT_COMPARISON},
    {"id": "mood", "title": "Mood", "prompt": PROMPT_MOOD},
    {"id": "functional", "title": "Functional", "prompt": PROMPT_FUNCTIONAL},
    {"id": "aialttext", "title": "AI Alt Text", "prompt": PROMPT_AIALTTEXT},
]

#: Set of all built-in style IDs for fast membership checks.
BUILTIN_STYLE_IDS: frozenset[str] = frozenset(style["id"] for style in BUILTIN_PROMPT_STYLES)

#: Lookup from style ID to full prompt text.
BUILTIN_PROMPT_BY_ID: dict[str, str] = {
    style["id"]: style["prompt"] for style in BUILTIN_PROMPT_STYLES
}

#: Lookup from style ID to human-readable title.
BUILTIN_TITLE_BY_ID: dict[str, str] = {
    style["id"]: style["title"] for style in BUILTIN_PROMPT_STYLES
}


def resolve_prompt_text(
    style_id: str,
    *,
    custom_prompts: list[dict[str, str]] | None = None,
    overrides: dict[str, str] | None = None,
    fallback: str = PROMPT_ACCESSIBILITY,
) -> str:
    """Return the prompt text for *style_id*, falling back gracefully.

    Resolution order: user override -> built-in constant -> custom prompt ->
    fallback.  Pass *overrides* (from settings.vision_builtin_overrides) so
    that user-edited built-in text is used instead of the shipped default.
    """
    if overrides:
        user_text = overrides.get(style_id, "").strip()
        if user_text:
            return user_text
    builtin = BUILTIN_PROMPT_BY_ID.get(style_id)
    if builtin is not None:
        return builtin
    if custom_prompts:
        for entry in custom_prompts:
            if entry.get("id") == style_id:
                return str(entry.get("prompt", fallback))
    return fallback


def enabled_style_choices(
    *,
    disabled_builtins: list[str] | None = None,
    custom_prompts: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Return the ordered list of enabled ``{id, title}`` entries for the picker.

    Built-in styles appear in canonical IDT order (skipping disabled ones);
    custom prompts are appended after the built-ins.
    """
    disabled: set[str] = set(disabled_builtins or [])
    choices: list[dict[str, str]] = []
    for style in BUILTIN_PROMPT_STYLES:
        if style["id"] not in disabled:
            choices.append({"id": style["id"], "title": style["title"]})
    for entry in custom_prompts or []:
        eid = entry.get("id", "")
        if eid:
            choices.append({"id": eid, "title": entry.get("title", eid)})
    return choices


__all__ = [
    "BUILTIN_PROMPT_STYLES",
    "BUILTIN_STYLE_IDS",
    "BUILTIN_PROMPT_BY_ID",
    "BUILTIN_TITLE_BY_ID",
    "PROMPT_ACCESSIBILITY",
    "PROMPT_AIALTTEXT",
    "PROMPT_ARTISTIC",
    "PROMPT_COLORFUL",
    "PROMPT_COMPARISON",
    "PROMPT_CONCISE",
    "PROMPT_DETAILED",
    "PROMPT_FUNCTIONAL",
    "PROMPT_MOOD",
    "PROMPT_NARRATIVE",
    "PROMPT_SIMPLE",
    "PROMPT_TECHNICAL",
    "enabled_style_choices",
    "resolve_prompt_text",
]
