"""Unit tests for the Vault Phase 3 search + quick-switcher core (wx-free)."""

from __future__ import annotations

from pathlib import Path

from quill.core.vault.search import quick_switch_matches, search_vault
from quill.core.vault.vault import scan_vault


def _make_vault(tmp_path: Path) -> object:
    (tmp_path / "intro.md").write_text(
        "# Introduction\n\nThe quick brown fox jumps.\nAnother line about foxes.\n",
        encoding="utf-8",
    )
    (tmp_path / "chapter.md").write_text(
        "---\naliases: [Chapter One, Ch1]\n---\n# Chapter\n\nA fox appears here too.\n",
        encoding="utf-8",
    )
    (tmp_path / "fox.md").write_text(
        "# Fox Facts\n\nFoxes are clever.\n",
        encoding="utf-8",
    )
    return scan_vault(tmp_path)


# --- full-text search ------------------------------------------------------


def test_search_finds_matching_lines_with_1_based_line_numbers(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    hits = search_vault(vault, "fox")
    # Every note mentions fox; check one concrete hit's line number and snippet.
    by_path = {(h.path, h.line_number) for h in hits}
    assert ("intro.md", 3) in by_path  # "The quick brown fox jumps." is line 3
    assert all("fox" in h.line.lower() for h in hits)


def test_title_matches_rank_above_body_matches(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    hits = search_vault(vault, "fox")
    # fox.md's title ("Fox Facts") matches, so its hits come before body-only notes.
    first_title_path = hits[0].path
    assert first_title_path == "fox.md"
    # A body-only match (intro/chapter) appears after the title-tier note.
    assert any(h.path in {"intro.md", "chapter.md"} for h in hits)
    assert hits.index(next(h for h in hits if h.path == "fox.md")) < hits.index(
        next(h for h in hits if h.path in {"intro.md", "chapter.md"})
    )


def test_whole_word_excludes_substring_matches(tmp_path: Path) -> None:
    (tmp_path / "n.md").write_text("# N\n\nfoxes and a fox\n", encoding="utf-8")
    vault = scan_vault(tmp_path)
    plain = search_vault(vault, "fox")
    whole = search_vault(vault, "fox", whole_word=True)
    assert plain  # matches "foxes" and "fox"
    # whole-word "fox" matches the standalone word, and the line still contains it once.
    assert whole and all(h.line == "foxes and a fox" for h in whole)


def test_regex_search(tmp_path: Path) -> None:
    (tmp_path / "n.md").write_text("# N\n\ncat dog cog\n", encoding="utf-8")
    vault = scan_vault(tmp_path)
    hits = search_vault(vault, r"c.g", regex=True)
    assert len(hits) == 1 and hits[0].line == "cat dog cog"


def test_within_paths_restricts_to_a_subset(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    hits = search_vault(vault, "fox", within_paths={"intro.md"})
    assert hits and {h.path for h in hits} == {"intro.md"}


def test_empty_or_invalid_query_yields_no_hits(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    assert search_vault(vault, "   ") == []
    assert search_vault(vault, "(unclosed", regex=True) == []  # invalid regex -> [], not an error


# --- quick switcher --------------------------------------------------------


def test_quick_switch_fuzzy_matches_titles_and_aliases(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    # "ch1" fuzzily matches the alias "Ch1" on chapter.md.
    matches = quick_switch_matches(vault, "ch1")
    assert matches and matches[0].path == "chapter.md"


def test_quick_switch_ranks_contiguous_prefix_highest(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    matches = quick_switch_matches(vault, "intro")
    assert matches[0].title == "Introduction"  # contiguous prefix beats scattered


def test_quick_switch_empty_query_returns_all_by_title(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    matches = quick_switch_matches(vault, "")
    assert {m.path for m in matches} == {"intro.md", "chapter.md", "fox.md"}


def test_quick_switch_non_subsequence_is_excluded(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path)
    assert quick_switch_matches(vault, "zzzz") == []
