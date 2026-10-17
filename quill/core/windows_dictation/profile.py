"""Your own words and phrases for dictation: the same ``dictation.md`` QUILL uses.

The file format is QUILL's (:mod:`quill.core.speech.dictation_profile`): a
Markdown file with a **Vocabulary** section -- names and jargon, which the
built-in engines' output is corrected towards by sound and spelling -- and a
**Replacements** section, ``say => write``, which is how somebody makes their
own spoken phrases: "my signature => Jeff Bishop\\nTucson" writes two lines
whenever they say *my signature*.

QUILL keeps the file in its data folder and its Locked Dictation reads it too,
so one set of words serves both kinds of dictation; QUILL Transcribe and Quill
Inkwell read it too. QUILL Lite keeps its own, in its own data folder, unless
the person checks "Use the shared word list" in My Words and Phrases (dict.md
D-12, :mod:`quill.core.windows_dictation.words_exchange`).

Read when it changes, not on every phrase: a dictation session hears a phrase
every few seconds, and re-reading a file that has not changed that often is
work for nothing.

wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.speech.dictation_profile import DictationProfile, parse_profile
from quill.core.speech.vocabulary import apply_custom_vocabulary

__all__ = [
    "LITE_TEMPLATE",
    "context_profile",
    "ensure_file",
    "load",
    "my_words",
    "rewriter",
    "with_repair_names",
]

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
_words_cache: dict[Path, tuple[tuple[Path, float], Any]] = {}


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


def my_words(path: Path) -> tuple[str, ...]:
    """The Vocabulary list at *path* (cached with the profile). Never raises."""
    return tuple(load(path).vocabulary)


def with_repair_names(preferences: Any, path: Path) -> Any:
    """*preferences* with My Words' names for self-repair ("Ana, no, Maria",
    D-20), when self-repair is on; unchanged otherwise."""
    if not getattr(preferences, "self_repair", False):
        return preferences
    from dataclasses import replace

    return replace(preferences, repair_names=my_words(path))


def context_profile(path: Path, context: str) -> DictationProfile:
    """The ``## Context: <context>`` list at *path* as a profile (D-21).

    Empty for no context, a context the file has no list for, or a missing
    file. *context* is a dictation profile's name (D-23), matched without case.
    """
    if not str(context or "").strip():
        return DictationProfile()
    from quill.core.windows_dictation.words_file import context_list, parse_words

    try:
        modified = path.stat().st_mtime
    except OSError:
        return DictationProfile()
    key = (path, modified)
    words = _words_cache.get(path)
    if words is None or words[0] != key:
        try:
            parsed = parse_words(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return DictationProfile()
        words = (key, parsed)
        _words_cache[path] = words
    chosen = context_list(words[1], context)
    if chosen is None:
        return DictationProfile()
    return DictationProfile(vocabulary=tuple(chosen.words), replacements=tuple(chosen.corrections))


def rewriter(path: Path, context: str = "") -> Callable[[str], str] | None:
    """``text -> text`` applying *path*'s vocabulary and replacements, or ``None``.

    With *context* -- the active dictation profile's name -- that context's
    own list (``## Context: email``) applies too, after the main lists, so a
    context's correction has the last word.
    """
    profile = load(path)
    extra = context_profile(path, context)
    if profile.is_empty and extra.is_empty:
        return None
    vocabulary = list(profile.vocabulary) + [
        word for word in extra.vocabulary if word not in profile.vocabulary
    ]

    def rewrite(text: str) -> str:
        if vocabulary:
            text = apply_custom_vocabulary(text, vocabulary)
        return extra.apply_replacements(profile.apply_replacements(text))

    return rewrite
