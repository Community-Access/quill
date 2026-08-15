"""Status-bar layout constants and value normalizers for :mod:`quill.core.settings`.

Extracted from ``settings.py`` to keep that module within its GATE-11 size
budget. This module is UI-framework-agnostic and has no dependency on the
``Settings`` dataclass, so it can be imported without circular references.
"""

from __future__ import annotations

from typing import Any

STATUS_BAR_ITEMS: tuple[str, ...] = (
    "line_column",
    # #872: page indicator. Visible by default (not in
    # _default_status_bar_hidden below), placed right after line_column
    # since both are "where am I" position cells -- not first, but adjacent.
    "page",
    "message",
    "word_count",
    # Character count of the whole document.
    "char_count",
    # Total line count of the whole document.
    "line_count",
    # Estimated reading time from the word count (~200 wpm).
    "reading_time",
    # Caret position as a percentage through the document.
    "document_progress",
    "mode",
    # Tab key behaviour: "Indent" (smart line indent) or "Tab char" (literal
    # tab insertion). Toggled with QUILL Key + U.
    "tab_mode",
    # One Editor, Every Format: the Document Format switcher cell. Shows the
    # current format ("Format: Markdown"); activating it opens the switcher.
    "document_format",
    "selection",
    "encoding",
    "line_endings",
    "spell_check",
    "background_tasks",
    "notifications",
    "read_aloud",
    "autosave",
    "search_term",
    "file_path",
    "quill_key_mode",
    "extend_mode",
    # A11Y live indicator (§8.3): shows the detected screen reader by name.
    "sr_name",
    # §10.4 Notebook goal progress cell.
    "notebook_goal",
    # Abbreviation expansion toggle indicator.
    "abbreviations",
    # Copy Tray occupied-slot count.
    "copy_tray_slots",
    # Active language profile for code-aware editing (#181).
    "language_profile",
    # Braille Mode (BR-010): page / line / cell / print page when a BRF
    # document is active. Hidden for non-BRF documents so it does not
    # take up status-bar real estate for sighted/non-braille workflows.
    "braille",
    # EdSharp port: caret-heading context — "Section: Heading N of M"
    # when the caret is on a heading in a Markdown or HTML document.
    # Hidden by default; users who work heavily with heading-level
    # navigation can opt in via Preferences -> Status Bar.
    "section_heading",
    # Active AI engine (Native / Copilot / Claude / OpenAI Agents). Hidden by
    # default; auto-surfaces once the user picks a non-Native agentic engine,
    # and is the click target for the quick engine switcher.
    "ai_engine",
    # Internet Radio mini-player: station + play/pause/stopped state. Hidden
    # by default; auto-surfaces the first time a station is played.
    "radio_player",
    # Podcasts mini-player + download activity. Hidden by default;
    # auto-surfaces the first time an episode plays or downloads.
    "podcast_player",
)


def _default_status_bar_order() -> list[str]:
    return list(STATUS_BAR_ITEMS)


def _default_status_bar_hidden() -> list[str]:
    return [
        "char_count",
        "line_count",
        "reading_time",
        "document_progress",
        "selection",
        "encoding",
        "line_endings",
        "spell_check",
        "background_tasks",
        "notifications",
        "read_aloud",
        "autosave",
        "search_term",
        "file_path",
        "quill_key_mode",
        "extend_mode",
        "sr_name",
        "abbreviations",
        "copy_tray_slots",
        "language_profile",
        "braille",
        "section_heading",
        "ai_engine",
        "radio_player",
        "podcast_player",
    ]


def _normalize_status_bar_order(raw: object) -> list[str]:
    if not isinstance(raw, list):
        values: list[str] = []
    else:
        values = [value for value in raw if isinstance(value, str)]
    allowed = set(STATUS_BAR_ITEMS)
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in allowed or value in seen:
            continue
        unique.append(value)
        seen.add(value)
    for item in STATUS_BAR_ITEMS:
        if item not in seen:
            unique.append(item)
    return unique


def _normalize_status_bar_hidden(raw: object, order: list[str]) -> list[str]:
    if not isinstance(raw, list):
        return _default_status_bar_hidden()
    order_set = set(order)
    hidden: list[str] = []
    seen: set[str] = set()
    for value in raw:
        if not isinstance(value, str):
            continue
        if value not in order_set or value in seen:
            continue
        hidden.append(value)
        seen.add(value)
    return hidden


def _clamp_int(raw: object, fallback: int, minimum: int, maximum: int) -> int:
    if isinstance(raw, (int, float, str)):
        try:
            value = int(raw)
        except (TypeError, ValueError, OverflowError):
            # OverflowError: JSON ``1e999`` parses to ``float('inf')`` and
            # ``int(inf)`` raises it -- a bad settings value must fall back, not
            # crash startup.
            value = fallback
    else:
        value = fallback
    if value < minimum:
        value = minimum
    if value > maximum:
        value = maximum
    return value


#: Browse Mode's follow-on timeout presets. Anything else read from a settings
#: file falls back to "unlimited", i.e. no timeout, which is the answer that
#: cannot strand somebody mid-navigation.
BROWSE_MODE_FOLLOWON_TIMEOUTS = frozenset({
    "instant",
    "fast",
    "normal",
    "slow",
    "custom",
    "unlimited",
})


def _normalize_browse_mode(data: dict[str, Any]) -> dict[str, Any]:
    """Every Browse Mode value, validated, in one pass.

    Extracted from ``Settings.from_dict`` (GATE-11 says extract, never
    rebaseline) because it is six independent fields with six independent
    validations, all of them about one feature, and none of them about the
    rest of that method. Behaviour is unchanged from the inline form.

    The follow-on timeout is #265's follow-up shape: a preset token plus an
    integer custom-millisecond override, replacing the float seconds it used
    to be. An unknown token reads as "unlimited" so a consumer treats it as no
    timeout at all, and the custom value clamps to [0, 60000] ms.
    """
    feedback = str(data.get("browse_mode_feedback", "speech")).strip().lower()
    if feedback not in {"sound", "speech", "both", "none"}:
        feedback = "speech"
    move_detail = str(data.get("browse_mode_move_detail", "position")).strip().lower()
    if move_detail not in {"none", "line", "position"}:
        move_detail = "position"
    followon_timeout = str(data.get("browse_mode_followon_timeout", "unlimited")).strip().lower()
    if followon_timeout not in BROWSE_MODE_FOLLOWON_TIMEOUTS:
        followon_timeout = "unlimited"
    try:
        followon_custom_ms = int(data.get("browse_mode_followon_custom_ms", 4000))
    except (TypeError, ValueError):
        followon_custom_ms = 4000
    followon_custom_ms = max(0, min(60_000, followon_custom_ms))
    return {
        "wrap": bool(data.get("browse_mode_wrap", True)),
        "feedback": feedback,
        "move_detail": move_detail,
        # The old key is still read, so a settings file written before the
        # rename keeps its answer instead of silently reverting to the default.
        "preload_cache": bool(
            data.get(
                "browse_mode_preload_cache",
                data.get("browse_mode_prewarm_for_large_docs", True),
            )
        ),
        "followon_timeout": followon_timeout,
        "followon_custom_ms": followon_custom_ms,
    }
