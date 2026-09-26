"""Your own words and phrases for dictation: the same ``dictation.md`` QUILL uses.

The file format is QUILL's (:mod:`quill.core.speech.dictation_profile`): a
Markdown file with a **Vocabulary** section -- names and jargon, which the
built-in engines' output is corrected towards by sound and spelling -- and a
**Replacements** section, ``say => write``, which is how somebody makes their
own spoken phrases: "my signature => Jeff Bishop\\nTucson" writes two lines
whenever they say *my signature*.

QUILL keeps the file in its data folder and its Locked Dictation reads it too,
so one set of words serves both kinds of dictation. QUILL Lite keeps its own,
in its own data folder, because it keeps everything of its own there.

Read when it changes, not on every phrase: a dictation session hears a phrase
every few seconds, and re-reading a file that has not changed that often is
work for nothing.

wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.speech.dictation_profile import DictationProfile, parse_profile
from quill.core.speech.vocabulary import apply_custom_vocabulary

__all__ = ["LITE_TEMPLATE", "ensure_file", "load", "rewriter"]

LITE_TEMPLATE = """\
# My dictation words and phrases

Teach dictation your words. Both sections are optional. Save this file and the
next phrase you dictate uses it -- there is nothing to restart.

## Vocabulary

Names, jargon and acronyms you use, spelled the way you want them. When the
speech engine writes something that sounds or looks close to one of these, it
is corrected to your spelling.

- QUILL
- NVDA
- JAWS

## Replacements

Your own spoken phrases. Say the words on the left and dictation writes the
text on the right. Use \\n for a new line and \\t for a tab.

my email address => someone@example.com
"""

_cache: dict[Path, tuple[float, DictationProfile]] = {}


def ensure_file(path: Path, template: str = LITE_TEMPLATE) -> Path:
    """*path*, created from *template* first when it does not exist yet."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template, encoding="utf-8")
    return path


def load(path: Path) -> DictationProfile:
    """The profile at *path*, re-read only when the file has changed. Never raises."""
    try:
        modified = path.stat().st_mtime
    except OSError:
        return DictationProfile()
    cached = _cache.get(path)
    if cached is not None and cached[0] == modified:
        return cached[1]
    try:
        profile = parse_profile(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return DictationProfile()
    _cache[path] = (modified, profile)
    return profile


def rewriter(path: Path) -> Callable[[str], str] | None:
    """``text -> text`` applying *path*'s vocabulary and replacements, or ``None``."""
    profile = load(path)
    if profile.is_empty:
        return None

    def rewrite(text: str) -> str:
        if profile.vocabulary:
            text = apply_custom_vocabulary(text, list(profile.vocabulary))
        return profile.apply_replacements(text)

    return rewrite
