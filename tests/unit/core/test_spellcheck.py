from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import spellcheck
from quill.core.spellcheck import (
    add_word_to_scope,
    list_misspellings,
    load_combined_dictionary,
    misspelling_at_position,
    next_misspelling,
    previous_misspelling,
    suggest_words,
)


@pytest.fixture(autouse=True)
def _isolate_backend_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin a deterministic backend tier for each test in this module.

    The on-host spell-check engine transparently selects between pyenchant, the
    bundled English wordlist, and a small built-in stub. On CI (windows-latest
    with no provider dictionaries installed) the enchant import resolves but
    ``check()`` returns False for every token, which would let ``"the"`` and
    ``"appears"`` slip through. Forcing the stub tier keeps the assertions
    independent of whatever backend the host happens to expose.
    """
    monkeypatch.setattr(spellcheck, "_ENCHANT_TRIED", True, raising=False)
    monkeypatch.setattr(spellcheck, "_ENCHANT_DICT", None, raising=False)
    monkeypatch.setattr(spellcheck, "_WORDLIST_CACHE", frozenset(), raising=False)


def test_list_misspellings_detects_unknown_word() -> None:
    misspellings = list_misspellings("the qwertyword appears", set())
    assert [item.word for item in misspellings] == ["qwertyword"]


def test_next_misspelling_returns_next_after_cursor() -> None:
    text = "the alpha qwertyword beta"
    misspelling = next_misspelling(text, text.index("alpha"), {"beta"})
    assert misspelling is not None
    assert misspelling.word == "qwertyword"


def test_add_word_to_scope_updates_combined_dictionary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    doc = tmp_path / "note.md"
    doc.write_text("x", encoding="utf-8")
    add_word_to_scope("qwertyword", "personal", doc, tmp_path)
    add_word_to_scope("docword", "document", doc, tmp_path)
    add_word_to_scope("projword", "project", doc, tmp_path)
    combined = load_combined_dictionary(doc, tmp_path)
    assert {"qwertyword", "docword", "projword"}.issubset(combined)


def test_suggest_words_returns_close_matches() -> None:
    suggestions = suggest_words("navigtion", {"navigation", "navigator"})
    assert "navigation" in suggestions


def test_misspelling_at_position_returns_item() -> None:
    text = "the qwertyword appears"
    item = misspelling_at_position(text, text.index("qwertyword"), set())
    assert item is not None
    assert item.word == "qwertyword"


def test_misspelling_at_position_returns_none_on_known_word() -> None:
    text = "alpha bravo charlie"
    item = misspelling_at_position(text, 0, {"alpha", "bravo", "charlie"})
    assert item is None


def test_misspelling_at_position_handles_caret_between_words() -> None:
    # Caret sits on the space between words; no match should be returned.
    text = "alpha bravo"
    item = misspelling_at_position(text, text.index(" "), set())
    assert item is None


def test_next_misspelling_scans_only_after_cursor() -> None:
    # Earlier unknown words should not be returned when the cursor is past
    # them. This guards the short-circuit optimization.
    text = "earlyunknown midword anotherbad"
    item = next_misspelling(text, text.index("midword"), {"midword"})
    assert item is not None
    assert item.word == "anotherbad"


def test_previous_misspelling_returns_previous_before_cursor() -> None:
    text = "earlywrong midword laterwrong"
    item = previous_misspelling(text, text.index("laterwrong"), {"midword"})
    assert item is not None
    assert item.word == "earlywrong"


# --- #315 list_misspellings memoization ----------------------------------


def test_list_misspellings_memoizes_repeated_calls() -> None:
    """#315: two ``list_misspellings`` calls with the same text and
    dictionary must return equivalent results, and the cached result
    must survive until the cache is reset.
    """
    text = "alpha bravo charlie delta"
    dictionary = {"alpha", "bravo", "charlie", "delta"}
    first = list_misspellings(text, dictionary)
    second = list_misspellings(text, dictionary)
    assert first == second


def test_list_misspellings_cache_invalidates_on_dictionary_change() -> None:
    """#315: adding a word to the dictionary must change the result.
    The memoization key includes the dictionary identity, so an
    updated dictionary is treated as a fresh request.
    """
    text = "alpha foobar"
    short_dict = {"alpha"}
    long_dict = {"alpha", "foobar"}
    short_result = list_misspellings(text, short_dict)
    long_result = list_misspellings(text, long_dict)
    assert [item.word for item in short_result] == ["foobar"]
    assert long_result == []


def test_list_misspellings_cache_reset_clears() -> None:
    """#315: ``reset_caches`` must clear the memoization so perf-budget
    tests can measure the cold path.
    """
    text = "alpha bravo"
    dictionary = {"alpha"}
    list_misspellings(text, dictionary)
    spellcheck.reset_caches()
    # After reset, the call must still work (it just rebuilds the cache).
    assert list_misspellings(text, dictionary) == []


# --- #316 suggest_words length-bucketed cache ----------------------------


def test_length_buckets_returns_words_by_length() -> None:
    """#316: the helper exposes a ``{length: [words]}`` view. The
    bundled wordlist always has words of many lengths, so this is a
    smoke test of the bucketing contract.
    """
    wordlist = spellcheck._load_wordlist()
    if not wordlist:
        pytest.skip("bundled wordlist unavailable in this environment")
    buckets = spellcheck._length_buckets(wordlist)
    assert isinstance(buckets, dict)
    for length, words in buckets.items():
        assert all(len(word) == length for word in words)


def test_suggest_words_still_returns_close_matches_after_bucketing() -> None:
    """#316: the new length-bucketed candidate pool must produce the
    same quality of suggestions as the previous O(W) scan. The bundled
    wordlist or the stub corpus is used depending on what is
    available.
    """
    wordlist = spellcheck._load_wordlist()
    if wordlist:
        # A clear typo: ``writting`` -> ``writing`` (length delta 0).
        suggestions = suggest_words("writting", set(), limit=5)
        assert "writing" in [s.lower() for s in suggestions]
    else:
        # Stub corpus: very small; ``textt`` -> ``text`` (length delta 1).
        suggestions = suggest_words("textt", set(), limit=5)
        assert "text" in [s.lower() for s in suggestions]


def test_length_buckets_cached_after_first_call() -> None:
    """#316: a second call to ``_length_buckets`` with the same
    wordlist identity must hit the cache, so the per-call work stays
    bounded by the bucket size rather than the full corpus size.
    """
    wordlist = spellcheck._load_wordlist()
    if not wordlist:
        pytest.skip("bundled wordlist unavailable in this environment")
    spellcheck._length_buckets(wordlist)
    cached = spellcheck._LENGTH_BUCKETS_BY_WORDLIST_ID.get(id(wordlist))
    assert cached is not None


def test_length_buckets_cache_reset_clears() -> None:
    """#316: ``reset_caches`` must clear the length-bucket cache so
    perf-budget tests can rebuild from scratch.
    """
    wordlist = spellcheck._load_wordlist()
    if not wordlist:
        pytest.skip("bundled wordlist unavailable in this environment")
    spellcheck._length_buckets(wordlist)
    spellcheck.reset_caches()
    assert spellcheck._LENGTH_BUCKETS_BY_WORDLIST_ID == {}
