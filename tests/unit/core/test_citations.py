"""Unit tests for quill.core.citations (issue #203)."""

from __future__ import annotations

import pytest

from quill.core.citations import (
    CITATION_STYLES,
    SOURCE_TYPES,
    Source,
    format_bibliography_entry,
    format_in_text,
)

_BOOK = Source(
    source_type="book",
    authors=("Jane Smith",),
    title="The Long Road",
    publisher="Acme Press",
    year="2021",
)
_ARTICLE = Source(
    source_type="article",
    authors=("Ada Lovelace", "Charles Babbage"),
    title="On the Engine",
    container="Journal of Computing",
    volume="12",
    issue="3",
    pages="45-60",
    year="2020",
)
_WEBSITE = Source(
    source_type="website",
    authors=("Pat Jones",),
    title="Getting Started",
    container="Example Docs",
    year="2024",
    url="https://example.com/start",
    accessed="3 Mar. 2026",
)


class TestInText:
    def test_mla_book_uses_author_and_page(self) -> None:
        s = Source(source_type="book", authors=("Jane Smith",), title="T", pages="42")
        assert format_in_text(s, "mla") == "(Smith 42)"

    def test_apa_uses_author_year(self) -> None:
        assert format_in_text(_BOOK, "apa") == "(Smith, 2021)"

    def test_chicago_uses_author_year(self) -> None:
        assert format_in_text(_BOOK, "chicago") == "(Smith 2021)"

    def test_two_authors_joined_with_and(self) -> None:
        assert "Lovelace and Babbage" in format_in_text(_ARTICLE, "apa")

    def test_three_plus_authors_use_et_al(self) -> None:
        s = Source(source_type="book", authors=("A One", "B Two", "C Three"), year="2000")
        assert "One et al." in format_in_text(s, "apa")

    def test_no_author_falls_back_to_title(self) -> None:
        s = Source(source_type="website", title="Untitled Source", year="2024")
        assert "Untitled Source" in format_in_text(s, "apa")


class TestBibliographyMLA:
    def test_book(self) -> None:
        entry = format_bibliography_entry(_BOOK, "mla")
        assert entry == "Smith, Jane. *The Long Road*. Acme Press, 2021."

    def test_article_has_quotes_and_volume(self) -> None:
        entry = format_bibliography_entry(_ARTICLE, "mla")
        assert '"On the Engine."' in entry
        assert "*Journal of Computing*" in entry
        assert "vol. 12" in entry and "no. 3" in entry and "pp. 45-60" in entry

    def test_website_has_accessed(self) -> None:
        entry = format_bibliography_entry(_WEBSITE, "mla")
        assert "Accessed 3 Mar. 2026." in entry
        assert "https://example.com/start" in entry


class TestBibliographyAPA:
    def test_book_has_year_in_parens_and_initials(self) -> None:
        entry = format_bibliography_entry(_BOOK, "apa")
        assert entry == "Smith, J. (2021). *The Long Road*. Acme Press."

    def test_article_uses_ampersand_and_volume_issue(self) -> None:
        entry = format_bibliography_entry(_ARTICLE, "apa")
        assert "Lovelace, A., & Babbage, C." in entry
        assert "*Journal of Computing*, 12(3), 45-60." in entry


class TestBibliographyChicago:
    def test_book_author_date(self) -> None:
        entry = format_bibliography_entry(_BOOK, "chicago")
        assert entry == "Smith, Jane. 2021. *The Long Road*. Acme Press."

    def test_article_has_journal_volume_issue_pages(self) -> None:
        entry = format_bibliography_entry(_ARTICLE, "chicago")
        assert '"On the Engine."' in entry
        assert "*Journal of Computing* 12 (3): 45-60." in entry


class TestValidation:
    def test_unknown_style_raises(self) -> None:
        with pytest.raises(ValueError, match="style"):
            format_bibliography_entry(_BOOK, "turabian")

    def test_unknown_source_type_raises(self) -> None:
        with pytest.raises(ValueError, match="source type"):
            format_bibliography_entry(Source(source_type="podcast"), "mla")

    def test_catalogues_are_well_formed(self) -> None:
        assert {v for v, _ in CITATION_STYLES} == {"mla", "chicago", "apa"}
        assert {v for v, _ in SOURCE_TYPES} == {"book", "article", "website"}
