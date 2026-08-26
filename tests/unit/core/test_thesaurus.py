from __future__ import annotations

import pytest

from quill.core import thesaurus


@pytest.mark.skipif(
    not thesaurus.is_available(),
    reason="Thesaurus data file not installed; skipping content-dependent tests.",
)
class TestThesaurusContent:
    def test_lookup_returns_entry_for_common_word(self) -> None:
        entry = thesaurus.lookup("happy")
        assert entry is not None
        assert entry.word == "happy"
        assert len(entry.meanings) >= 1
        assert any("cheerful" in m.synonyms or "glad" in m.synonyms for m in entry.meanings)

    def test_lookup_is_case_insensitive(self) -> None:
        assert thesaurus.lookup("Happy") is not None
        assert thesaurus.lookup("HAPPY") is not None

    def test_lookup_unknown_word_returns_none(self) -> None:
        assert thesaurus.lookup("qwertyzzzword") is None

    def test_meanings_carry_part_of_speech(self) -> None:
        entry = thesaurus.lookup("write")
        assert entry is not None
        pos_set = {m.part_of_speech for m in entry.meanings}
        assert "verb" in pos_set

    def test_all_synonyms_deduplicates(self) -> None:
        entry = thesaurus.lookup("happy")
        assert entry is not None
        synonyms = entry.all_synonyms
        assert len(synonyms) == len({s.lower() for s in synonyms})


def test_word_at_returns_word_under_cursor() -> None:
    result = thesaurus.word_at("Hello there friend", 8)
    assert result == ("there", 6, 11)


def test_word_at_handles_cursor_after_word() -> None:
    text = "Hello"
    # Cursor sits immediately after the word.
    result = thesaurus.word_at(text, len(text))
    assert result is not None
    assert result[0] == "Hello"


def test_word_at_returns_none_outside_word() -> None:
    assert thesaurus.word_at("  ", 0) is None
    assert thesaurus.word_at("", 0) is None


def test_data_path_is_inside_package() -> None:
    path = thesaurus.data_path()
    assert path.name == "th_en_US_v2.dat"
    assert path.parent.name == "data"


@pytest.mark.skipif(
    not thesaurus.is_available(),
    reason="Thesaurus data file not installed; skipping content-dependent tests.",
)
class TestRelationsAreKeptApart:
    """MyThes marks the relation of every sense member. It is not decoration.

    Until 2026-08-26 the parser truncated each member at its first bracket and
    filed the result under "synonyms", so 13,060 antonyms across 9,667
    headwords were offered as substitutes: "heavy" for "light", "decrease" for
    "increase". Nothing announced it, and a writer who took one had inverted
    their own sentence. These tests exist so that cannot come back.
    """

    def test_light_does_not_offer_heavy_as_a_synonym(self) -> None:
        """The single assertion that encodes the whole defect."""
        entry = thesaurus.lookup("light")
        assert entry is not None
        assert "heavy" not in entry.all_synonyms
        assert "heavy" in entry.all_antonyms

    def test_increase_does_not_offer_decrease_as_a_synonym(self) -> None:
        entry = thesaurus.lookup("increase")
        assert entry is not None
        assert "decrease" not in entry.all_synonyms
        assert "decrement" not in entry.all_synonyms
        assert "decrease" in entry.all_antonyms

    def test_no_headword_offers_an_antonym_as_a_synonym(self) -> None:
        """The property behind the two examples above, over a spread of words.

        Sampled rather than exhaustive: the whole file is ~200,000 senses and
        this suite should stay fast. The words are ones with rich antonym sets,
        which is where a regression would show first.
        """
        for word in ("light", "increase", "fast", "hot", "open", "hard", "true"):
            entry = thesaurus.lookup(word)
            if entry is None:
                continue
            overlap = {s.lower() for s in entry.all_synonyms} & {
                a.lower() for a in entry.all_antonyms
            }
            assert not overlap, f"{word}: {sorted(overlap)} offered as both"

    def test_broader_terms_are_not_substitutes(self) -> None:
        """A hypernym is a true fact about the word and a bad replacement for it.

        "The Hague" is a city; writing "city" where "The Hague" belonged loses
        the meaning, so generic terms are kept out of the synonym list.
        """
        entry = thesaurus.lookup("'s gravenhage")
        assert entry is not None
        assert "city" not in entry.all_synonyms
        assert "city" in entry.all_broader

    def test_similar_terms_still_count_as_synonyms(self) -> None:
        """The other half of the rule, and the one that is easy to overshoot.

        "happy" has no unmarked members in its primary sense -- every one is a
        "(similar term)". Treating those as anything but synonyms would delete
        the main sense of the word from the thesaurus.
        """
        entry = thesaurus.lookup("happy")
        assert entry is not None
        assert "cheerful" in entry.all_synonyms


class TestSplitRelation:
    """The parser's unit, including the guard against a future data file."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("heavy (antonym)", ("heavy", "antonym")),
            ("capital (generic term)", ("capital", "broader")),
            ("cheerful (similar term)", ("cheerful", "similar")),
            ("aspect (related term)", ("aspect", "related")),
            ("glad", ("glad", "")),
            ("  spaced  ", ("spaced", "")),
            ("", ("", "")),
        ],
    )
    def test_known_markers(self, raw: str, expected: tuple[str, str]) -> None:
        assert thesaurus._split_relation(raw) == expected

    def test_an_unknown_parenthetical_stays_part_of_the_term(self) -> None:
        """No such term exists in the shipped data -- the four markers are the
        whole vocabulary -- so this guards a future file. The safe failure is a
        slightly odd term, never a silently miscategorised one."""
        assert thesaurus._split_relation("mercury (planet)") == ("mercury (planet)", "")


@pytest.mark.skipif(
    not thesaurus.is_available(),
    reason="Thesaurus data file not installed; skipping content-dependent tests.",
)
class TestChoiceRows:
    def test_substitutes_come_first_and_the_rest_are_labelled(self) -> None:
        rows = thesaurus.choice_rows(thesaurus.lookup("light"))
        labels = [label for label, _ in rows]
        first_marked = next(
            i for i, label in enumerate(labels) if label.startswith(("broader:", "opposite:"))
        )
        assert all(label.startswith("[") for label in labels[:first_marked])
        assert all(label.startswith(("broader:", "opposite:")) for label in labels[first_marked:])

    def test_the_inserted_term_never_carries_the_prefix(self) -> None:
        """Replacing "light" with "opposite: heavy" would be a funny bug."""
        rows = thesaurus.choice_rows(thesaurus.lookup("light"))
        for label, term in rows:
            assert not term.startswith(("broader:", "opposite:", "["))
            assert term in label
