"""GATE-CAST-WORDS: the words QUILL Cast uses (qc.md section 12)."""

from __future__ import annotations

from quill.core.podcasts import words
from quill.tools import cast_words_audit


def test_the_forbidden_words_are_caught_as_whole_words_only() -> None:
    assert words.offences("Unsubscribe from this show") == ["Unsubscribe"]
    assert words.offences("Search for unplayed episodes") == ["Search", "unplayed"]
    assert words.offences("Researching a podcast") == [], "a whole word, not a substring"
    assert words.offences("Import an OPML subscription list") == [], "the format's own name"
    assert words.offences("Follow it; find it; unheard.") == []


def test_the_tree_has_no_unreviewed_offence() -> None:
    found = cast_words_audit.scan()
    allowlist = cast_words_audit.load_allowlist()
    assert cast_words_audit.violations(found, allowlist) == []
    stale = [key for key in allowlist if key not in {offence.key for offence in found}]
    assert stale == [], "an allowlist entry whose literal is gone must be removed"


def test_an_entry_with_no_reason_fails() -> None:
    offence = cast_words_audit.Offence(("x.py::Search here", ("Search",)))
    assert cast_words_audit.violations([offence], {"x.py::Search here": ""})
    assert not cast_words_audit.violations([offence], {"x.py::Search here": "a product name"})


def test_the_settings_catalogue_is_in_the_scan_and_speaks_cast_words() -> None:
    """Preferences and Settings for This Podcast build their rows from these
    labels, so the gate reads them; "When I subscribe" was there until 2026-10-03."""
    from quill.core.podcasts import settings_catalog

    scanned = {
        path.relative_to(cast_words_audit.REPO_ROOT).as_posix()
        for path in cast_words_audit._files()
    }
    assert "quill/core/podcasts/settings_help.py" in scanned
    assert "quill/core/podcasts/settings_defs_show.py" in scanned
    for definition in settings_catalog.CATALOG:
        assert words.offences(definition.label) == [], definition.id
        assert words.offences(definition.help) == [], definition.id
        for choice in definition.choices:
            assert words.offences(str(choice.label)) == [], (definition.id, choice)
    assert words.offences("It never unsubscribes you") == ["unsubscribes"]
