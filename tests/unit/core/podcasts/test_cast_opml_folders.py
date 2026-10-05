"""Folders through Import OPML and back out through export (2026-10-04 folder test).

``fixtures/cast_folders.opml`` is a slice of a real Downcast export with folders
added: nested two and three deep, empty folders (one inside another), one
podcast filed in two folders, names with an ampersand, accents, quotes and
Downcast's double escaping, and podcasts at the top level on both sides of the
folders. Before this test, both empty folders vanished on import.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts import opml, opml_import
from quill.core.podcasts.subscriptions import PodcastLibrary

_FILE = Path(__file__).parent / "fixtures" / "cast_folders.opml"

_EXPECTED = [
    "[News & Politics]",
    "  [Daily]",
    '    [Morning "Briefs"]',
    "      Today in iOS Podcast - The Unofficial iOS, iPhone, iPad, and Apple Watch News "
    "and iPhone Apps Podcast",
    "    The Best of Car Talk",
    "  The Moth",
    "  MacBites",
    "[Café Français]",
    "  LDS Talks - John Bytheway",
    "[Empty Folder]",
    "[Outer]",
    "  [Inner Empty]",
    "[We're Folder]",
    "  The Blind Geek Zone",
    "TED Talks Daily",
    "LightningBolt Theater of the Mind",
]


def _tree(library: PodcastLibrary) -> list[str]:
    out: list[str] = []

    def walk(parent: str | None, depth: int) -> None:
        for folder in [f for f in library.folders if f.parent_folder_id == parent]:
            out.append("  " * depth + f"[{folder.name}]")
            walk(folder.id, depth + 1)
        for show in [s for s in library.shows if s.folder_id == parent]:
            out.append("  " * depth + show.title)

    walk(None, 0)
    return out


@pytest.fixture
def imported() -> tuple[PodcastLibrary, opml_import.ImportPlan]:
    library = PodcastLibrary()
    plan = opml_import.parse_and_plan(library, _FILE.read_text(encoding="utf-8"))
    opml_import.apply_plan(library, plan)
    return library, plan


def test_the_file_structure_arrives_exactly(imported) -> None:
    library, _plan = imported
    assert _tree(library) == _EXPECTED


def test_empty_folders_are_kept_in_file_order() -> None:
    folders = opml.parse_opml_folders(_FILE.read_text(encoding="utf-8"))
    assert folders == [
        ["News & Politics"],
        ["News & Politics", "Daily"],
        ["News & Politics", "Daily", 'Morning "Briefs"'],
        ["Café Français"],
        ["Empty Folder"],
        ["Outer"],
        ["Outer", "Inner Empty"],
        ["We're Folder"],
    ]


def test_a_podcast_in_two_folders_is_followed_once_and_the_report_says_where(imported) -> None:
    library, plan = imported
    assert [s.title for s in library.shows].count("The Moth") == 1
    assert plan.duplicates_in_file == [
        "The Moth (http://feeds.feedburner.com/themothpodcast), also listed in "
        "Café Français; kept in News & Politics"
    ]


def test_export_and_import_again_gives_the_same_tree(imported) -> None:
    library, _plan = imported
    exported = opml.export_opml(library)
    assert 'text="News &amp; Politics"' in exported
    assert 'text="Morning &quot;Briefs&quot;"' in exported
    again = PodcastLibrary()
    opml_import.apply_plan(again, opml_import.parse_and_plan(again, exported))
    assert _tree(again) == _EXPECTED


def test_importing_the_same_file_twice_adds_no_folders_or_podcasts(imported) -> None:
    library, _plan = imported
    folders, shows = len(library.folders), len(library.shows)
    plan = opml_import.parse_and_plan(library, _FILE.read_text(encoding="utf-8"))
    opml_import.apply_plan(library, plan)
    assert (len(library.folders), len(library.shows)) == (folders, shows)
    assert plan.new == []


def test_into_folder_nests_empty_folders_too() -> None:
    library = PodcastLibrary()
    plan = opml_import.parse_and_plan(library, _FILE.read_text(encoding="utf-8"))
    opml_import.apply_plan(library, plan, into_folder="Downcast")
    tree = _tree(library)
    assert tree[0] == "[Downcast]"
    assert "  [Empty Folder]" in tree
    assert "    [Inner Empty]" in tree
