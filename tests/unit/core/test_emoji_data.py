"""Tests for the Accessible Emoji Picker data model (quill.core.emoji_data)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core import emoji_data


@pytest.fixture(autouse=True)
def _fake_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A small, hand-built catalog covering every field/search path -- direct
    symbol lookup, emoticon aliases, name/keyword substrings, and a
    description-only match -- instead of depending on the real (large,
    LLM-generated) committed catalog."""
    catalog = {
        "unicode_emoji_version": "16.0",
        "source_urls": {},
        "entries": [
            {
                "char": "\U0001f600",  # grinning face
                "name": "grinning face",
                "category": "Smileys & Emotion",
                "subgroup": "face-smiling",
                "keywords": ["grin", "happy", "smile"],
                "emoticons": [":D"],
                "description": "A bright yellow face with a wide open smile and closed eyes.",
            },
            {
                "char": "\U0001faf0",  # melting face proxy
                "name": "melting face",
                "category": "Smileys & Emotion",
                "subgroup": "face-affection",
                "keywords": [],
                "emoticons": [],
                "description": "A yellow face melting into a puddle, an awkward embarrassment.",
            },
            {
                "char": "\U0001f436",  # dog face
                "name": "dog face",
                "category": "Animals & Nature",
                "subgroup": "animal-mammal",
                "keywords": ["dog", "pet", "puppy"],
                "emoticons": [],
                "description": "A friendly brown dog face with floppy ears and a pink tongue.",
            },
            {
                "char": "\U0001f499",  # blue heart
                "name": "blue heart",
                "category": "Smileys & Emotion",
                "subgroup": "emotion",
                "keywords": ["blue", "heart"],
                "emoticons": ["<3"],
                "description": "A solid blue heart shape.",
            },
        ],
    }
    path = tmp_path / "emoji_catalog.json"
    path.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(emoji_data, "_CATALOG_PATH", path)
    monkeypatch.setattr(emoji_data, "_ENTRIES", None)
    monkeypatch.setattr(emoji_data, "_LOAD_ERROR", None)
    return path


def test_is_available_and_no_load_error() -> None:
    assert emoji_data.is_available() is True
    assert emoji_data.load_error() is None


def test_missing_catalog_degrades_to_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(emoji_data, "_CATALOG_PATH", tmp_path / "nonexistent.json")
    monkeypatch.setattr(emoji_data, "_ENTRIES", None)
    monkeypatch.setattr(emoji_data, "_LOAD_ERROR", None)
    assert emoji_data.is_available() is False
    assert emoji_data.load_error() is not None
    assert emoji_data.list_categories() == []


def test_list_categories_preserves_catalog_order() -> None:
    assert emoji_data.list_categories() == ["Smileys & Emotion", "Animals & Nature"]


def test_list_by_category() -> None:
    smileys = emoji_data.list_by_category("Smileys & Emotion")
    assert [e.name for e in smileys] == ["grinning face", "melting face", "blue heart"]
    assert emoji_data.list_by_category("Nonexistent") == []


def test_entry_by_char() -> None:
    entry = emoji_data.entry_by_char("\U0001f600")
    assert entry is not None
    assert entry.name == "grinning face"
    assert emoji_data.entry_by_char("\U0001f9ff") is None  # not in the fixture catalog


def test_entries_by_chars_preserves_order_and_drops_unknown_chars() -> None:
    """Exercises the exact lookup quill.core.emoji_usage's Favorites/Recent
    lists go through: stored order matters (most-recent-first for Recent),
    and a stale char from an older catalog version must not raise or stop
    the rest of the list from resolving."""
    entries = emoji_data.entries_by_chars(["\U0001f436", "\U0001f9ff", "\U0001f600", "\U0001f499"])
    assert [e.name for e in entries] == ["dog face", "grinning face", "blue heart"]


def test_search_empty_query_returns_nothing() -> None:
    assert emoji_data.search("") == []
    assert emoji_data.search("   ") == []


def test_search_by_direct_symbol() -> None:
    results = emoji_data.search("\U0001f600")
    assert [e.name for e in results] == ["grinning face"]


def test_search_by_emoticon_alias() -> None:
    results = emoji_data.search(":D")
    assert [e.name for e in results] == ["grinning face"]

    results = emoji_data.search("<3")
    assert [e.name for e in results] == ["blue heart"]


def test_search_by_name_substring() -> None:
    results = emoji_data.search("dog")
    assert [e.name for e in results] == ["dog face"]


def test_search_by_keyword_substring() -> None:
    results = emoji_data.search("puppy")
    assert [e.name for e in results] == ["dog face"]


def test_search_by_description_only_match() -> None:
    """ "melting" is not a keyword on the melting-face fixture entry -- only
    its rich description mentions it -- so this proves tier 4 (description
    search) actually fires and is reachable."""
    results = emoji_data.search("puddle")
    assert [e.name for e in results] == ["melting face"]


def test_search_ranks_stronger_matches_first_and_never_duplicates() -> None:
    # "heart" is a keyword on blue heart; also appears nowhere else here.
    results = emoji_data.search("heart")
    names = [e.name for e in results]
    assert names == ["blue heart"]
    assert len(names) == len(set(names))


def test_search_case_insensitive() -> None:
    assert [e.name for e in emoji_data.search("DOG")] == ["dog face"]
    assert [e.name for e in emoji_data.search("Puddle")] == ["melting face"]


def test_describe_includes_every_field() -> None:
    entry = emoji_data.list_by_category("Smileys & Emotion")[0]
    described = emoji_data.describe(entry)
    assert entry.char in described.summary
    assert entry.name in described.summary
    assert "Category: Smileys & Emotion > face-smiling" in described.detail
    assert "Keywords: grin, happy, smile" in described.detail
    assert "Also typed as: :D" in described.detail
    assert entry.description in described.detail


def test_describe_omits_empty_keyword_and_emoticon_lines() -> None:
    melting = emoji_data.list_by_category("Smileys & Emotion")[1]
    described = emoji_data.describe(melting)
    assert "Keywords:" not in described.detail
    assert "Also typed as:" not in described.detail


# --------------------------------------------------------------------------- #
# The shipped catalogue is the *current* Unicode set
# --------------------------------------------------------------------------- #
#
# The picker fetches nothing at runtime (network_egress_audit's no-surprise-calls
# rule, and the app must work offline and in Safe Mode), so the catalogue is a
# committed file that a maintainer regenerates when Unicode publishes a new
# emoji version -- roughly once a year. A committed file with nothing watching
# it is a file that silently falls a release behind, and the symptom is somebody
# searching for an emoji their phone shows them and finding nothing.


#: The Unicode Emoji version the committed catalogue is built from. Raise this
#: and regenerate together (`python -m quill.tools.generate_emoji_catalog`);
#: never raise it alone.
EXPECTED_EMOJI_VERSION = "16.0"

#: A representative handful from the two newest sets. A version stamp says what
#: the generator was *asked* for; these say what actually arrived, which is the
#: half a truncated download would get wrong.
NEWEST_EMOJI = {
    # Emoji 16.0
    "\U0001fae9": "face with bags under eyes",
    "\U0001fabe": "leafless tree",
    "\U0001fac6": "fingerprint",
    "\U0001fadc": "root vegetable",
    "\U0001fadf": "splatter",
    "\U0001fa89": "harp",
    "\U0001fa8f": "shovel",
    "\U0001f1e8\U0001f1f6": "flag: Sark",
    # Emoji 15.1
    "\U0001f426‍⬛": "black bird",
    "\U0001f642‍↔️": "head shaking horizontally",
    "\U0001f34b‍\U0001f7e9": "lime",
}


def _catalog() -> dict:
    """The **shipped** catalogue, read straight off disk.

    Deliberately not through :mod:`quill.core.emoji_data`: the autouse fixture
    above points that at a hand-built eleven-entry stub, which is right for
    testing the search paths and useless for asking whether the real file is
    current. These four tests are about the committed data, so they open it.
    """
    import json
    from pathlib import Path

    import quill

    path = Path(quill.__file__).resolve().parent / "data" / "emoji_catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_catalog_states_the_unicode_version_it_was_built_from() -> None:
    assert _catalog()["unicode_emoji_version"] == EXPECTED_EMOJI_VERSION


def test_every_emoji_from_the_newest_sets_is_actually_present() -> None:
    """The version stamp says what was asked for; this says what arrived.

    A truncated download, a parser that stopped early, or a regeneration that
    quietly reused a cached file all leave the stamp correct and the tail
    missing -- and the only person who finds out is somebody searching for an
    emoji their phone shows them.
    """
    present = {entry["char"] for entry in _catalog()["entries"]}
    missing = sorted(name for char, name in NEWEST_EMOJI.items() if char not in present)
    assert not missing, f"catalogue is missing: {missing}"


def test_the_catalog_carries_every_unicode_grouping() -> None:
    # Nine, and the same nine Unicode publishes. A missing group is a whole
    # branch of the browse list gone, which nothing else here would notice.
    groups = {entry["category"] for entry in _catalog()["entries"]}
    assert groups == {
        "Smileys & Emotion",
        "People & Body",
        "Animals & Nature",
        "Food & Drink",
        "Travel & Places",
        "Activities",
        "Objects",
        "Symbols",
        "Flags",
    }


def test_every_entry_has_the_description_the_picker_reads_aloud() -> None:
    """The written description is the entire reason this picker is usable.

    A visual grid is the one control shape that cannot be used without sight, so
    the list is what replaces it -- and a row with no description is a row that
    reads out as a bare character, which is where this started.
    """
    blank = [
        entry["name"] for entry in _catalog()["entries"] if not str(entry.get("description", ""))
    ]
    assert not blank[:10], f"{len(blank)} entries have no description, e.g. {blank[:5]}"
