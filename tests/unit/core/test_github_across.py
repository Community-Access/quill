"""Across Repositories (across.py) and Repository Sets (repository_sets.py)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import across
from quill.core.github.repository_sets import RepositorySets, normalize_repository


def _row(title: str, when: str, **kw: Any) -> SimpleNamespace:
    return SimpleNamespace(title=title, updated_at=when, **kw)


def _fetchers(answers: dict[str, Any]) -> dict[str, Any]:
    def fetch(repo: str, limit: int) -> list[Any]:
        answer = answers[repo]
        if isinstance(answer, Exception):
            raise answer
        return answer[:limit]

    return {key: fetch for key, _label in across.CATEGORIES}


def test_every_repository_answers_for_itself() -> None:
    result = across.fetch_across(
        None,
        "issues",
        ["a/one", "b/two", "c/three", "a/one"],
        fetchers=_fetchers({
            "a/one": [_row("Crash", "2026-11-02")],
            "b/two": RuntimeError("404 Not Found"),
            "c/three": [],
        }),
    )
    assert [repo for repo, _row in result.rows] == ["a/one"]
    by_repo = {o.repository: o for o in result.outcomes}
    assert by_repo["b/two"].error == "not found, or no access"
    assert by_repo["c/three"].note == "no issues and pull requests"
    assert result.summary() == "1 from 2 of 3 repositories; 1 could not be read; 1 had none."


def test_a_busy_repository_is_bounded_and_says_so() -> None:
    many = [_row(f"#{n}", f"2026-11-{n % 28 + 1:02d}") for n in range(40)]
    result = across.fetch_across(
        None, "issues", ["a/one"], per_repo=30, fetchers=_fetchers({"a/one": many})
    )
    assert len(result.rows) == 30 and result.outcomes[0].more
    assert "1 had more than shown" in result.summary()
    assert result.outcomes[0].state == "partial"


def test_a_fork_whose_upstream_is_chosen_adds_no_issues() -> None:
    result = across.fetch_across(
        None,
        "issues",
        ["me/proj", "org/proj"],
        upstream_of=lambda repo: "org/proj" if repo == "me/proj" else "",
        fetchers=_fetchers({"me/proj": [_row("dup", "x")], "org/proj": [_row("real", "y")]}),
    )
    assert [repo for repo, _ in result.rows] == ["org/proj"]
    assert "a fork of org/proj" in result.outcomes[0].note


def test_latest_release_skips_drafts_and_prereleases() -> None:
    rows = [
        SimpleNamespace(draft=True, prerelease=False, published_at="2026-11-09"),
        SimpleNamespace(draft=False, prerelease=True, published_at="2026-11-08"),
        SimpleNamespace(draft=False, prerelease=False, published_at="2026-11-01"),
    ]
    assert across.latest_release(rows) is rows[2]
    assert across.latest_release(rows[:2]) is rows[1]
    assert across.latest_release(rows[:1]) is None


def test_order_and_the_next_repository_keys() -> None:
    rows = [
        ("b/two", _row("Beta", "2026-11-03")),
        ("a/one", _row("alpha", "2026-11-01")),
        ("b/two", _row("Gamma", "2026-11-02")),
    ]
    assert [r[1].title for r in across.order_rows(rows, "newest")] == ["Beta", "Gamma", "alpha"]
    assert [r[1].title for r in across.order_rows(rows, "name")] == ["alpha", "Beta", "Gamma"]
    grouped = across.order_rows(rows, "repository", chosen=["a/one", "b/two"])
    assert [r[0] for r in grouped] == ["a/one", "b/two", "b/two"]
    assert across.next_repository(grouped, 0) == 1
    assert across.next_repository(grouped, 1) == 1  # the last run: stays
    assert across.next_repository(grouped, 2, -1) == 0


def test_unknown_category_is_refused() -> None:
    with pytest.raises(ValueError):
        across.fetch_across(None, "wiki", ["a/b"], fetchers={})


def test_repository_sets_are_per_account_and_validated(tmp_path) -> None:
    assert normalize_repository("https://github.com/Owner/Repo.git/") == "Owner/Repo"
    assert normalize_repository("not a repo") == ""
    sets = RepositorySets.load("octo", data_dir=tmp_path)
    rejected = sets.set_repositories("Work", ["a/one", "github.com/b/two", "nope", "a/one"])
    assert rejected == ["nope"]
    sets.save()
    again = RepositorySets.load("octo", data_dir=tmp_path)
    assert again.repositories("Work") == ["a/one", "b/two"]
    assert RepositorySets.load("someone-else", data_dir=tmp_path).names() == []
