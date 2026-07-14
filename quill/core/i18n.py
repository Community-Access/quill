"""Internationalisation helpers for QUILL.

Provides ``_()``, ``ngettext()``, ``lazy_gettext()``, and ``init_locale()``.
All user-visible strings in QUILL should be wrapped with ``_()`` so Babel can
extract them into the ``.pot`` master template for community translation.

Usage in modules::

    from quill.core.i18n import _
    label = _("Open file")

Speech strings must also be wrapped; mark them in comments as ``# SPEECH:``
so translators know they will be spoken aloud by a screen reader::

    # SPEECH: announce after document save
    msg = _("Saved")

Initialisation happens once in ``MainFrame.__init__`` via ``init_locale()``
before any UI strings are resolved.  During import (before init) all calls
return the untranslated message string.
"""

from __future__ import annotations

import gettext
import locale
import logging
from pathlib import Path

_LOCALE_DIR = Path(__file__).resolve().parents[1] / "locale"
_DOMAIN = "quill"
_log = logging.getLogger(__name__)

_translation: gettext.NullTranslations = gettext.NullTranslations()


def init_locale(language: str | None = None) -> str:
    """Initialise the active translation.

    ``language`` is a BCP 47 / POSIX locale tag (e.g. ``"fr"``, ``"fr_FR"``,
    ``"es_419"``).  An empty string or ``None`` triggers OS-language detection.
    Returns the resolved language tag that was activated.

    Safe to call multiple times; a new language replaces the previous one.
    """
    global _translation

    tag = (language or "").strip()
    if not tag:
        tag = _detect_os_language()

    if not _LOCALE_DIR.is_dir():
        _translation = gettext.NullTranslations()
        return tag

    try:
        t = gettext.translation(
            _DOMAIN,
            localedir=str(_LOCALE_DIR),
            languages=[tag],
            fallback=False,
        )
        _translation = t
        _log.debug("i18n: loaded translation for %r", tag)
    except FileNotFoundError:
        _translation = gettext.NullTranslations()
        _log.debug("i18n: no translation for %r, using fallback", tag)

    return tag


def _(message: str) -> str:
    """Translate *message* to the active language."""
    return _translation.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Translate a plural-aware *singular* / *plural* pair for count *n*."""
    return _translation.ngettext(singular, plural, n)


class _LazyString:
    """String-like proxy that defers translation until first use."""

    __slots__ = ("_message",)

    def __init__(self, message: str) -> None:
        self._message = message

    def __str__(self) -> str:
        return _(self._message)

    def __repr__(self) -> str:
        return f"lazy_gettext({self._message!r})"

    def __eq__(self, other: object) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(str(self))


LazyStr = _LazyString


def lazy_gettext(message: str) -> _LazyString:
    """Return a proxy that translates *message* on first string conversion.

    Useful for module-level constants that are evaluated before ``init_locale``
    is called::

        LABEL = lazy_gettext("Open file")
    """
    return _LazyString(message)


# Display names for languages QUILL is likely to be translated into. The
# native name is included in parentheses so a speaker of that language can
# recognise their own language in the chooser even before the UI switches.
_DISPLAY_NAMES: dict[str, str] = {
    "en": "English",
    "ar": "Arabic (العربية)",
    "cs": "Czech (Čeština)",
    "da": "Danish (Dansk)",
    "de": "German (Deutsch)",
    "el": "Greek (Ελληνικά)",
    "es": "Spanish (Español)",
    "fi": "Finnish (Suomi)",
    "fr": "French (Français)",
    "he": "Hebrew (עברית)",
    "hi": "Hindi (हिन्दी)",
    "it": "Italian (Italiano)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "nb": "Norwegian Bokmål (Norsk bokmål)",
    "nl": "Dutch (Nederlands)",
    "pl": "Polish (Polski)",
    "pt": "Portuguese (Português)",
    "pt_BR": "Portuguese, Brazil (Português do Brasil)",
    "ru": "Russian (Русский)",
    "sv": "Swedish (Svenska)",
    "tr": "Turkish (Türkçe)",
    "uk": "Ukrainian (Українська)",
    "zh": "Chinese (中文)",
    "zh_Hans": "Chinese, Simplified (简体中文)",
    "zh_Hant": "Chinese, Traditional (繁體中文)",
}


def language_display_name(tag: str) -> str:
    """Return a human-friendly name for a locale *tag* (falls back to the tag).

    Looks up the exact tag first, then the base language (so ``"fr_CA"`` still
    shows the French name), then returns the tag unchanged.
    """
    key = tag.replace("-", "_")
    if key in _DISPLAY_NAMES:
        return _DISPLAY_NAMES[key]
    base = key.split("_", 1)[0]
    return _DISPLAY_NAMES.get(base, tag)


def available_languages() -> list[str]:
    """Return locale tags that have a compiled translation (``quill.mo``).

    These are the directory names under ``quill/locale`` that contain
    ``LC_MESSAGES/quill.mo`` — i.e. the languages a user can actually switch
    to. The list is sorted and never includes the source language placeholder
    (English needs no ``.mo``). Returns an empty list when only the ``.pot``
    template is present.
    """
    if not _LOCALE_DIR.is_dir():
        return []
    tags: list[str] = []
    for child in _LOCALE_DIR.iterdir():
        if not child.is_dir():
            continue
        if (child / "LC_MESSAGES" / f"{_DOMAIN}.mo").is_file():
            tags.append(child.name)
    return sorted(tags)


def _detect_os_language() -> str:
    """Return the best-guess UI language from the OS."""
    try:
        tag, _ = locale.getlocale()
        if tag:
            return tag.replace("_", "-").split(".")[0]
    except Exception:
        pass
    return "en"
