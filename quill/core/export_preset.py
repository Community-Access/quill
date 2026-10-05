"""The "Default export format" setting (default_export_preset).

File > Export lists every format by name, so a default cannot choose for you
there -- you already chose by picking the menu row. The one place QUILL asks
"which format?" is **Export > Other Pandoc Format...**, and that list opens with
your default already selected, so Enter exports in the format you usually use.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence

#: Setting value -> the Pandoc export format name it means.
PRESET_FORMATS: dict[str, str] = {
    "html": "html",
    "markdown": "markdown",
    "pdf": "pdf",
    "docx": "docx",
    "epub": "epub",
    "text": "plain_text",
}

DEFAULT_PRESET = "html"


def preset_format_name(settings: object) -> str:
    """The Pandoc export format the user's default export preset names."""
    raw = str(getattr(settings, "default_export_preset", DEFAULT_PRESET) or "").strip().lower()
    return PRESET_FORMATS.get(raw, PRESET_FORMATS[DEFAULT_PRESET])


def preset_index(format_names: Sequence[str], settings: object) -> int:
    """Where the default format sits in *format_names*; 0 when it is not offered."""
    wanted = preset_format_name(settings)
    for index, name in enumerate(format_names):
        if name == wanted:
            return index
    return 0


__all__ = ["DEFAULT_PRESET", "PRESET_FORMATS", "preset_format_name", "preset_index"]
