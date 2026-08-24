"""Settings help that says what a setting does *not* do (list.md section 3).

The rule: **what it does, then the misreading it prevents, in that order, in
one added sentence.** Not a doc page -- a doc page is something somebody has to
decide to go and read, and the moment a setting is misread is the moment they
are standing on it.

Two things are asserted here, and the second is the one that will catch the
next mistake:

* every help string is a *sentence about a setting*, not a label repeated;
* every one of them contains a **negative clause** -- "never", "not", "instead
  of", "rather than", "only" -- because that is what the second half of the
  rule always turns out to be. Every misread in this area has been about what
  a setting leaves alone: whether it touches what you already have, whether
  "keep" means the episode or just the file, whether off means never or only
  not-by-itself.

A string can be exempt, and a handful are: a button ("Choose a folder") and a
status readout name what a control *is*, and there is no misreading of "Status"
to prevent. Those are listed by key rather than detected, so adding one is a
decision somebody makes on purpose.
"""

from __future__ import annotations

import re

from quill.core.podcasts import settings_help as cast_help
from quill.core.radio import settings_help as radio_help

#: Keys that name a control rather than explain a setting. A button and a
#: status line have nothing they could be misread as doing.
NOT_SETTINGS: frozenset[str] = frozenset({
    "download_folder_button",
    "folder_button",
    "temp_folder_button",
    "save_button",
    "status",
})

#: The shapes the "and what it does not do" half actually takes. Not a style
#: rule -- these are the words that draw the boundary.
_NEGATIVE = re.compile(
    r"\b(never|not|no |nothing|neither|nor|instead of|rather than|only|"
    r"without|cannot|leaves|untouched|stay|stays|unchanged)\b",
    re.IGNORECASE,
)


def _tables() -> list[tuple[str, dict[str, str]]]:
    return [
        ("cast", cast_help.HELP),
        ("cast/show", cast_help.SHOW_HELP),
        ("radio/recording", radio_help.HELP),
        ("radio/downloads", radio_help.DOWNLOAD_HELP),
    ]


def _settings_entries() -> list[tuple[str, str, str]]:
    return [
        (table, key, text)
        for table, entries in _tables()
        for key, text in entries.items()
        if key not in NOT_SETTINGS
    ]


def test_every_setting_says_what_it_does_not_do() -> None:
    """The whole rule, in one assertion.

    A string with no negative clause is a string that answered "what does this
    do?" and stopped -- which is the version that was already there, and the
    version somebody misreads.
    """
    missing = [
        f"{table}:{key}" for table, key, text in _settings_entries() if not _NEGATIVE.search(text)
    ]
    assert missing == [], "help with no 'and what it does not do' half: " + ", ".join(missing)


def test_every_setting_is_more_than_one_sentence() -> None:
    """Two clauses at least: the rule is 'then', not 'or'."""
    too_short = [
        f"{table}:{key}"
        for table, key, text in _settings_entries()
        if len([part for part in re.split(r"(?<=[.!?]) ", text) if part.strip()]) < 2
    ]
    assert too_short == []


def test_nothing_is_a_doc_page() -> None:
    """One added sentence, not five. Help nobody finishes is help nobody read."""
    too_long = [f"{table}:{key}" for table, key, text in _settings_entries() if len(text) > 420]
    assert too_long == []


def test_every_string_reads_as_prose() -> None:
    """No leftover placeholders, no double spaces from a joined literal, and a
    capital at the front -- a screen reader reads exactly what is here."""
    for table, entries in _tables():
        for key, text in entries.items():
            assert text == text.strip(), f"{table}:{key} has stray whitespace"
            assert "  " not in text, f"{table}:{key} has a double space"
            assert text[0].isupper(), f"{table}:{key} does not start with a capital"
            assert "{}" not in text and "TODO" not in text, f"{table}:{key} is unfinished"


def test_the_exemptions_all_exist() -> None:
    """An exemption for a key nobody uses is an exemption hiding a real one."""
    known = {key for _table, entries in _tables() for key in entries}
    assert NOT_SETTINGS <= known


def test_the_lookup_picks_a_table_rather_than_falling_through() -> None:
    """Recordings and downloads both have a destination folder, so a lookup
    that searched one then the other would hand a downloads control the
    sentence about recordings -- the kind of wrong that reads as right."""
    assert "folder" in radio_help.HELP
    assert "folder" in radio_help.DOWNLOAD_HELP
    assert radio_help.describe("folder") == radio_help.HELP["folder"]
    assert radio_help.describe("folder", downloads=True) == radio_help.DOWNLOAD_HELP["folder"]


def test_an_unknown_key_answers_with_silence() -> None:
    """A control that says "no description available" says nothing twice."""
    assert radio_help.describe("no-such-setting") == ""
    assert cast_help.describe("no-such-setting") == ""
    assert cast_help.describe("no-such-setting", per_show=True) == ""


def test_the_per_show_table_is_reached_by_asking_for_it() -> None:
    assert cast_help.describe("auto_download") == cast_help.HELP["auto_download"]
    assert (
        cast_help.describe("auto_download", per_show=True) == cast_help.SHOW_HELP["auto_download"]
    )
    assert cast_help.HELP["auto_download"] != cast_help.SHOW_HELP["auto_download"]


def test_the_dialogs_read_the_tables_rather_than_their_own_literals() -> None:
    """The strings moved out so they could be checked at all; a dialog that
    kept a literal would be a control quietly outside the rule."""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    for name, module in (
        ("quill/ui/podcasts/podcast_settings_dialog.py", "settings_help.HELP["),
        ("quill/ui/podcasts/show_settings_dialog.py", "settings_help.SHOW_HELP["),
        ("quill/ui/radio/recording_settings_dialog.py", "settings_help.HELP["),
        ("quill/ui/radio/download_prefs_dialog.py", "settings_help.DOWNLOAD_HELP["),
    ):
        source = (repo / name).read_text(encoding="utf-8")
        assert module in source, name
        literals = re.findall(r'SetName\(\s*\n?\s*"', source)
        assert literals == [], f"{name} still names a control with a literal"
