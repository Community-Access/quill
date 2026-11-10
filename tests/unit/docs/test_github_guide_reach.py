"""Every contents page lists all of the GitHub Guide, and every route to it works.

The GitHub Guide is twelve chapters (eleven until Chapter 12, the Workbench,
2026-11-10). QUILL's contents page listed five until
2026-11-08, so six chapters were reachable only from inside the guide itself.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from quill.core import user_guide_files as ugf

_ROOT = Path(__file__).resolve().parents[3]
_QUILL_BOOK = _ROOT / "docs" / "user guide" / "github-guide"
_LITE_GUIDE_DIR = _ROOT / "standalone" / "quilllite" / "docs" / "github-guide"

#: Contents page -> (the folder its GitHub chapters are in, their file prefix).
_CONTENTS = {
    ugf.QUILL_GUIDE: (_QUILL_BOOK, "github-guide-"),
    ugf.GITHUB_GUIDE: (_QUILL_BOOK, "github-guide-"),
    ugf.LITE_GUIDE: (_LITE_GUIDE_DIR, "lite-github-guide-"),
    _LITE_GUIDE_DIR / "lite-github-guide.md": (_LITE_GUIDE_DIR, "lite-github-guide-"),
}


def _chapters(folder: Path, prefix: str) -> set[str]:
    return {path.stem for path in folder.glob(f"{prefix}*.md") if re.match(r".*-\d\d-", path.stem)}


@pytest.mark.parametrize("contents", list(_CONTENTS), ids=lambda p: p.name)
def test_every_contents_page_lists_all_twelve_chapters(contents: Path) -> None:
    folder, prefix = _CONTENTS[contents]
    chapters = _chapters(folder, prefix)
    assert len(chapters) == 12
    text = contents.read_text(encoding="utf-8")
    linked = set(re.findall(rf"({re.escape(prefix)}\d\d-[a-z0-9-]+)\.html", text))
    assert linked == chapters, sorted(chapters - linked)


def test_quills_links_to_the_book_stay_outside_its_chapters() -> None:
    """``./github-guide/`` is not a chapter folder, so the guide does not swallow the book."""
    assert not any("github-guide" in path.name for path in ugf.chapter_paths(ugf.QUILL_GUIDE))


def test_the_rendered_guide_links_every_github_chapter_to_its_shipped_page() -> None:
    text = ugf.QUILL_GUIDE.read_text(encoding="utf-8")
    guide = {path.resolve() for path in ugf.guide_files(ugf.QUILL_GUIDE)}
    localised = ugf._localise_links(ugf.QUILL_GUIDE, text, guide)
    uris = set(re.findall(r"\]\((file:[^)#\s]*github-guide-\d\d-[^)#\s]*\.html)", localised))
    assert len(uris) == 12
    assert "](./github-guide/" not in localised


def test_the_whole_book_epub_sends_the_github_links_to_the_website() -> None:
    book = ugf.single_document_text(ugf.QUILL_GUIDE)
    relative = re.findall(r"\]\((?!https?:)[^)]*github-guide[^)]*\)", book)
    assert relative == []
    assert f"]({ugf.SITE_DOCS_URL}github-guide.html)" in book
    assert f"]({ugf.SITE_DOCS_URL}github-guide-01-getting-started.html)" in book


def test_a_published_url_is_only_for_a_real_document_under_docs(tmp_path) -> None:
    assert ugf._published_url(ugf.GITHUB_GUIDE) == f"{ugf.SITE_DOCS_URL}github-guide.html"
    assert ugf._published_url(tmp_path / "x.md") == ""
    assert ugf._published_url(_ROOT / "docs" / "site" / "index.md") == ""


def test_the_gates_that_read_the_guide_read_the_github_guide_too() -> None:
    text = ugf.read_guide_text(ugf.QUILL_GUIDE)
    assert "# Chapter 11: Keyboard reference" in text
    lite = ugf.read_guide_text(ugf.LITE_GUIDE)
    # QUILL Lite's guide holds its own copy as chapters; QUILL's is not added twice.
    assert lite.count("# The GitHub Guide for QUILL and QUILL Lite") == 1
