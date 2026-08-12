"""Tests for locating the documentation QUILL Social ships with itself.

The bug these guard against: the installer placed the user guide in docs\\ beside
the program and nothing in the app could open it. The rules worth pinning are
that HTML wins over Markdown (Windows has no default handler for .md, so a .md
shortcut can open nothing at all), that a dev checkout resolves too, and that a
missing document is reported rather than raised.
"""

from pathlib import Path

from quill_social.ui.docs import DOC_TITLES, doc_candidates, find_doc, open_doc


def test_html_is_preferred_over_markdown() -> None:
    order = [c.suffix for c in doc_candidates("USER_GUIDE")]
    assert order[0] == ".html"
    assert ".md" in order
    assert order.index(".html") < order.index(".md")


def test_candidates_include_the_in_repo_docs_folder() -> None:
    """A dev run must resolve too, or the menu items silently do nothing."""
    repo_docs = Path(__file__).resolve().parents[1] / "docs"
    assert any(c.parent == repo_docs for c in doc_candidates("USER_GUIDE"))


def test_the_user_guide_actually_ships() -> None:
    found = find_doc("USER_GUIDE")
    assert found is not None, "USER_GUIDE is offered on the Help menu but is not present"
    assert found.is_file()


def test_every_menu_document_resolves() -> None:
    """Each stem offered on the Help menu must exist, or we advertise a dead item."""
    missing = [stem for stem in DOC_TITLES if find_doc(stem) is None]
    assert not missing, f"Help menu offers documents that do not ship: {missing}"


def test_a_missing_document_is_reported_not_raised() -> None:
    assert find_doc("NO_SUCH_DOCUMENT") is None
    assert open_doc("NO_SUCH_DOCUMENT") is None


def test_doc_titles_are_human_readable() -> None:
    for stem, title in DOC_TITLES.items():
        assert title != stem
        assert "_" not in title
