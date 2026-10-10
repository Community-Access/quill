"""The family's declarative settings index (qc.md X-01): matching and wording."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.settings_finder import (
    SettingEntry,
    match_rank,
    moved_to,
    registry_entries,
    result_label,
    search_entries,
)

_ENTRIES = (
    SettingEntry("a", "Output folder", "the main window", "Where files go.", ("destination",)),
    SettingEntry("b", "Open the output folder when done", "", "Explorer opens it."),
    SettingEntry("c", "Sample rate", "the main window's Advanced Options", "", ("hz",)),
    SettingEntry("d", "Output", "", "The device."),
)


def test_every_word_must_match_and_case_is_ignored() -> None:
    assert [e.key for e in search_entries(_ENTRIES, "OUTPUT folder")] == ["a", "b"]
    assert search_entries(_ENTRIES, "output banana") == []


def test_an_empty_query_lists_nothing() -> None:
    assert search_entries(_ENTRIES, "") == []
    assert search_entries(_ENTRIES, "   ") == []


def test_the_setting_called_what_you_typed_comes_first() -> None:
    # "Output" is exact (0); "Output folder" starts with it (1); the third
    # only has the word inside its label (2). Declaration order breaks ties.
    assert [e.key for e in search_entries(_ENTRIES, "output")] == ["d", "a", "b"]


def test_aliases_place_and_description_are_searched_but_rank_last() -> None:
    assert [e.key for e in search_entries(_ENTRIES, "destination")] == ["a"]
    assert [e.key for e in search_entries(_ENTRIES, "hz")] == ["c"]
    assert [e.key for e in search_entries(_ENTRIES, "advanced")] == ["c"]
    assert match_rank("Sample rate", "hz", "hz") == 3


def test_match_rank_ignores_access_keys_and_trailing_colons() -> None:
    assert match_rank("&Output folder:", "", "output folder") == 0
    assert match_rank("Output folder", "", "nothing") is None


def test_result_label_and_moved_to_name_the_place() -> None:
    elsewhere, here = _ENTRIES[2], _ENTRIES[1]
    assert result_label(elsewhere) == "Sample rate, in the main window's Advanced Options"
    assert result_label(here) == "Open the output folder when done"
    assert moved_to(elsewhere) == "Moved to the main window's Advanced Options."
    # Nowhere to have moved to: the screen reader's own focus speech is enough.
    assert moved_to(here) == ""


def test_registry_entries_follow_the_group_title_and_keywords() -> None:
    groups = [SimpleNamespace(id="editing", title="Editing")]
    specs = [
        SimpleNamespace(
            key="soft_wrap",
            label="Wrap long lines",
            group="editing",
            description="Wrap at the window edge.",
            keywords=("word wrap",),
        )
    ]
    (entry,) = registry_entries(groups, specs, area="the {title} page of Settings")
    assert entry == SettingEntry(
        "soft_wrap",
        "Wrap long lines",
        "the Editing page of Settings",
        "Wrap at the window edge.",
        ("word wrap",),
    )
    assert search_entries([entry], "word wrap") == [entry]


def test_the_real_registry_is_fully_indexable() -> None:
    from quill.core import settings_registry as registry

    entries = registry_entries(registry.groups(), registry.specs())
    assert len(entries) == len(registry.specs())
    assert all(entry.area.startswith("the ") for entry in entries)
    assert len({entry.key for entry in entries}) == len(entries)
