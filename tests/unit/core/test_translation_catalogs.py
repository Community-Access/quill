"""Guard: every shipped ``.po`` must have a compiled, non-empty ``.mo``.

The display-language picker (``i18n.available_languages``) lists only languages
that have a compiled ``quill.mo`` on disk; the app loads translations from those
``.mo`` files via stdlib ``gettext``. A ``.po`` merged without its compiled
``.mo`` (the build does not compile them) is invisible to users -- exactly the
"Italian isn't in Change Display Language" report. These tests fail CI if a
catalog is missing, uncompiled, or empty, so a translation can't silently ship
without actually being selectable.
"""

from __future__ import annotations

import gettext

from quill.core.i18n import _DOMAIN, _LOCALE_DIR, available_languages


def _catalog_languages() -> list[str]:
    return sorted(p.parent.parent.name for p in _LOCALE_DIR.glob(f"*/LC_MESSAGES/{_DOMAIN}.po"))


def test_every_translation_catalog_is_compiled_and_listed() -> None:
    langs = _catalog_languages()
    assert langs, "expected at least one .po translation catalog under quill/locale"
    listed = set(available_languages())
    for lang in langs:
        mo = _LOCALE_DIR / lang / "LC_MESSAGES" / f"{_DOMAIN}.mo"
        assert mo.is_file(), (
            f"{lang}: {mo} is missing. Run 'python -m quill.tools.compile_translations' "
            "and commit the .mo, or the language never appears in Change Display Language."
        )
        assert lang in listed, f"{lang} has a compiled .mo but available_languages() omits it"


def test_italian_catalog_has_real_translations() -> None:
    # Elena Brescacin's it catalog -- confirm the .mo carries actual translations
    # (a present-but-empty .mo would list Italian yet translate nothing).
    translation = gettext.translation(_DOMAIN, localedir=str(_LOCALE_DIR), languages=["it"])
    catalog = translation._catalog  # type: ignore[attr-defined]
    translated = sum(
        1
        for key, value in catalog.items()
        if isinstance(key, str) and key and value and key != value
    )
    assert translated > 100, "it.mo has too few translated entries -- likely stale or empty"
