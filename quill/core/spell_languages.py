"""The spell-check language catalogue: what is installed, downloadable, and how
each language is named aloud.

Split out of :mod:`quill.core.spellcheck` (GATE-11): the catalogue is pure
"which languages, where, what are they called" bookkeeping and needs nothing
from the checking engine, so it lives here and ``spellcheck`` re-exports these
names for its existing callers. This module must not import ``spellcheck`` --
that is the split's one hard rule, and it holds because nothing in the
catalogue needs the checking side.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from quill.core.paths import app_data_dir

logger = logging.getLogger(__name__)

# The Hunspell language the enchant backend validates against. en_US ships inside
# pyenchant and is the default; other languages are downloaded on demand (PRD
# 10.2.4) into managed_hunspell_dir() and discovered via ENCHANT_CONFIG_DIR.
DEFAULT_LANGUAGE = "en_US"


def managed_spell_dir() -> Path:
    """The ENCHANT_CONFIG_DIR root holding Hunspell dictionaries.

    Prefers the Offline Edition's bundled dictionaries under
    ``{app}/dictionaries`` (when QUILL_APP_ROOT is set and a ``hunspell/``
    subdir of translated dictionaries is staged there), so the bundled
    languages are discoverable by both ``installed_languages`` and enchant on
    an air-gapped machine. Falls back to the user-writable app-data dir, where
    on-demand downloads land on a slim install.
    """
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        bundled = Path(app_root) / "dictionaries"
        if (bundled / "hunspell").is_dir():
            return bundled
    return app_data_dir() / "spell"


def managed_hunspell_dir() -> Path:
    """Where downloaded ``<lang>.dic``/``.aff`` pairs live (enchant scans here)."""
    return managed_spell_dir() / "hunspell"


# Human-readable names for the language tags QUILL knows about. en_US is bundled;
# the rest are downloadable (their release-asset components are "spell-<tag>").
#: Every tag the pyenchant wheel ships a dictionary for, plus the downloadable
#: ones. Spoken aloud, "English (South Africa)" is a choice; "en_ZA" is a puzzle
#: -- and this list is read by a screen reader far more often than it is seen.
_LANGUAGE_NAMES: dict[str, str] = {
    "en_AG": "English (Antigua and Barbuda)",
    "en_AU": "English (Australia)",
    "en_BS": "English (Bahamas)",
    "en_BW": "English (Botswana)",
    "en_BZ": "English (Belize)",
    "en_CA": "English (Canada)",
    "en_DK": "English (Denmark)",
    "en_GB": "English (United Kingdom)",
    "en_GH": "English (Ghana)",
    "en_HK": "English (Hong Kong)",
    "en_IE": "English (Ireland)",
    "en_IN": "English (India)",
    "en_JM": "English (Jamaica)",
    "en_NA": "English (Namibia)",
    "en_NG": "English (Nigeria)",
    "en_NZ": "English (New Zealand)",
    "en_PH": "English (Philippines)",
    "en_SG": "English (Singapore)",
    "en_TT": "English (Trinidad and Tobago)",
    "en_US": "English (United States)",
    "en_ZA": "English (South Africa)",
    "en_ZW": "English (Zimbabwe)",
    "es_ES": "Spanish (Spain)",
    "fr_FR": "French (France)",
}

#: ``en_AU-large`` and friends are the same language with a bigger word list.
_LARGE_SUFFIX = "-large"


def language_display_name(lang: str) -> str:
    """A friendly name for a language tag, falling back to the tag itself."""
    if lang.endswith(_LARGE_SUFFIX):
        base = lang[: -len(_LARGE_SUFFIX)]
        if base in _LANGUAGE_NAMES:
            return f"{_LANGUAGE_NAMES[base]} - extended word list"
    return _LANGUAGE_NAMES.get(lang, lang)


def installed_languages() -> list[str]:
    """Hunspell languages available now: everything the backend can resolve.

    Three sources, unioned:

    1. Whatever the enchant provider itself reports. This is the one that was
       missing, and it mattered: the pyenchant wheel ships **22** Hunspell
       dictionaries, not one -- en_GB, en_AU, en_CA, en_IE, en_IN, en_NZ, en_ZA
       and the rest. They install with every QuillVille app, they work (en_GB
       accepts "colour" and rejects "color"), and yet the Spell Check Language
       chooser listed only en_US, because this function looked exclusively at
       the download folder. A British user had no way to pick British English
       out of a dictionary already sitting on their disk.
    2. ``en_US``, always, because it is the default and must never be missing
       from the list even in the wordlist/stub tiers where enchant is absent.
    3. Any ``<tag>.dic`` downloaded on demand into :func:`managed_hunspell_dir`.

    Best-effort on the enchant call: a broker that cannot be built (no enchant
    installed, a broken payload) degrades to the filesystem answer rather than
    taking the language chooser down with it.
    """
    langs = {DEFAULT_LANGUAGE}
    try:
        import enchant  # noqa: PLC0415 - optional backend, imported lazily

        langs.update(str(tag) for tag in enchant.Broker().list_languages())
    except Exception:  # noqa: BLE001 - the chooser must open without enchant
        logger.debug("enchant broker unavailable; listing downloaded dictionaries only")
    hs = managed_hunspell_dir()
    if hs.is_dir():
        for dic in hs.glob("*.dic"):
            langs.add(dic.stem)
    return sorted(langs)


def downloaded_languages() -> list[str]:
    """Only the languages fetched on demand into :func:`managed_hunspell_dir`.

    The subset of :func:`installed_languages` that QUILL actually *manages* --
    it downloaded them, it can delete them. The ones the enchant provider ships
    inside its own payload are part of the application, not components: they
    cannot be removed and offering to remove them (the Optional Components
    manager lists one row per dictionary) would be an action that silently does
    nothing.
    """
    hs = managed_hunspell_dir()
    if not hs.is_dir():
        return []
    return sorted(dic.stem for dic in hs.glob("*.dic"))


def installable_languages() -> list[str]:
    """Downloadable languages (have a pinned release asset) not yet installed."""
    from quill.core import release_assets

    installed = set(installed_languages())
    out = [
        component[len("spell-") :]
        for component in release_assets.ASSETS
        if component.startswith("spell-")
    ]
    return sorted(lang for lang in out if lang not in installed)
