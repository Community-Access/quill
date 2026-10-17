"""Finding a named text by its words, in any order (quill/core/list_search.py)."""

from __future__ import annotations

from pathlib import Path

from quill.core.copy_tray import CopyTray
from quill.core.list_search import SearchTerms, matches_search
from quill.core.snippets import Snippet, search_snippets


def test_the_whole_search_or_every_word() -> None:
    assert matches_search("meeting notes", ["Meeting notes for Tuesday"])
    assert matches_search("notes meeting", ["Notes from the meeting"])
    assert matches_search("reply thanks", ["Thanks", "a reply to a kind note"])
    assert not matches_search("reply invoice", ["Thanks", "a reply to a kind note"])


def test_case_and_spacing_are_ignored() -> None:
    assert matches_search("  MEETING   notes ", ["meeting notes"])
    assert SearchTerms("").found_in("anything")
    assert SearchTerms("   ").found_in("")


def test_a_one_word_search_is_still_a_substring_search() -> None:
    assert matches_search("meet", ["Meeting"])
    assert not matches_search("meetings", ["Meeting"])


def _snippet(name: str, body: str = "text", trigger: str = "") -> Snippet:
    return Snippet(
        id=name, name=name, trigger=trigger or f";{name[:3].lower()}", body=body, tags=[]
    )


def test_snippets_are_found_by_words_in_any_order_and_ranked_as_before() -> None:
    snippets = [
        _snippet("Notes from the meeting"),
        _snippet("Meeting notes for Tuesday"),
        _snippet("Invoice reminder"),
    ]
    in_order = [s.name for s in search_snippets(snippets, "meeting notes")]
    # Starts-with-the-name still comes first; the any-order match follows.
    assert in_order == ["Meeting notes for Tuesday", "Notes from the meeting"]
    # Neither name starts with "notes meeting", so both are any-order matches,
    # alphabetical -- and before 2026-10-16 this search found nothing at all.
    assert [s.name for s in search_snippets(snippets, "notes meeting")] == [
        "Meeting notes for Tuesday",
        "Notes from the meeting",
    ]
    assert [s.name for s in search_snippets(snippets, "invoice notes")] == []


def test_the_copy_tray_search_takes_words_in_any_order(tmp_path: Path) -> None:
    tray = CopyTray(tmp_path)
    tray.copy_to(1, "Thanks for the meeting notes")
    tray.copy_to(2, "Invoice attached")
    found = [number for number, _slot in tray.search_slots("notes thanks")]
    assert found == [1]
    assert [n for n, _s in tray.search_slots("invoice")] == [2]
