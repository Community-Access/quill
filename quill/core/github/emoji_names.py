"""Emoji shortcodes read by name: ``:tada:`` becomes "party popper" (GitHub PRD 22.12).

GitHub renders ``:rocket:`` as a picture, but the raw text QUILL shows keeps
the shortcode, and a screen reader spells it out, colons and underscores and
all. :func:`name_shortcodes` replaces each shortcode it knows with the
emoji's name in words, the name a screen reader gives the picture. Names come
from QUILL's own emoji catalogue (:mod:`quill.core.emoji_data`): a shortcode
is a catalogue name with underscores for spaces (``:thumbs_up:``), or one of
GitHub's own older aliases (``:+1:``, ``:tada:``, ``:shipit:``), listed below.
A shortcode inside code (a backtick span or a fenced block) is code, and is
left as typed; so is anything QUILL does not know.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
import threading

__all__ = ["GITHUB_ALIASES", "name_for", "name_shortcodes"]

#: GitHub's shortcodes that are not the Unicode name, the ones people type most.
GITHUB_ALIASES: dict[str, str] = {
    "+1": "thumbs up",
    "-1": "thumbs down",
    "thumbsup": "thumbs up",
    "thumbsdown": "thumbs down",
    "tada": "party popper",
    "hooray": "party popper",
    "heart": "red heart",
    "smile": "grinning face with smiling eyes",
    "smiley": "grinning face with big eyes",
    "laughing": "grinning squinting face",
    "laugh": "grinning squinting face",
    "confused": "confused face",
    "eyes": "eyes",
    "rocket": "rocket",
    "white_check_mark": "check mark button",
    "heavy_check_mark": "check mark",
    "x": "cross mark",
    "warning": "warning",
    "bug": "bug",
    "sparkles": "sparkles",
    "fire": "fire",
    "wave": "waving hand",
    "pray": "folded hands",
    "clap": "clapping hands",
    "ok_hand": "OK hand",
    "joy": "face with tears of joy",
    "thinking": "thinking face",
    "100": "hundred points",
    "memo": "memo",
    "zap": "high voltage",
    "construction": "construction",
    "lock": "locked",
    "art": "artist palette",
    "recycle": "recycling symbol",
    "boom": "collision",
    "bulb": "light bulb",
    "wrench": "wrench",
    "heavy_plus_sign": "plus",
    "heavy_minus_sign": "minus",
    "arrow_up": "up arrow",
    "arrow_down": "down arrow",
    "shipit": "squirrel (GitHub's ship it)",
    "octocat": "Octocat (GitHub's mascot)",
}

_SHORTCODE = re.compile(r"(?<![\w:]):([a-z0-9_+\-]{1,40}):(?![\w:])")
_CODE = re.compile(r"(```.*?```|~~~.*?~~~|`[^`\n]*`)", re.DOTALL)

_LOCK = threading.Lock()
_NAMES: dict[str, str] | None = None


def _names() -> dict[str, str]:
    global _NAMES
    with _LOCK:
        if _NAMES is None:
            from quill.core.emoji_data import _load

            names: dict[str, str] = {}
            for entry in _load():
                if ":" in entry.name:  # skin tones and flags' qualifiers
                    continue
                code = re.sub(r"[^a-z0-9+\-]+", "_", entry.name.casefold()).strip("_")
                names.setdefault(code, entry.name)
            names.update(GITHUB_ALIASES)
            _NAMES = names
        return _NAMES


def name_for(shortcode: str) -> str:
    """The name for ``tada`` or ``:tada:``, or ``""`` when it is not known."""
    return _names().get(shortcode.strip(":").casefold(), "")


def _outside_code(text: str) -> str:
    return _SHORTCODE.sub(lambda m: name_for(m.group(1)) or m.group(0), text)


def name_shortcodes(text: str) -> str:
    """*text* with every known shortcode outside code read as its name."""
    if ":" not in text:
        return text
    parts = _CODE.split(text)
    return "".join(part if index % 2 else _outside_code(part) for index, part in enumerate(parts))
