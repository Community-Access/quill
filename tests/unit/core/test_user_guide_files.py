"""The user guides as a contents page plus chapter files (quill.core.user_guide_files).

Two halves: the helper's own behaviour on a small guide built here, and the
real guides' shape -- every chapter linked, every file name unique across the
tree (the site flattens docs by basename), and every link between guide files
landing on a heading that exists.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

import pytest

from quill.core import user_guide_files as ugf

_ROOT = Path(__file__).resolve().parents[3]
_GUIDES = (ugf.QUILL_GUIDE, ugf.LITE_GUIDE)


def _small_guide(tmp_path: Path) -> Path:
    folder = tmp_path / "book"
    folder.mkdir()
    (folder / "book-01-start.md").write_text(
        "# Chapter 1: Start\n\n## Saving -- your work\n\nSee [later](book-02-end.html#the-end).\n\n"
        "---\n\n- Next: [Chapter 2: End](book-02-end.html)\n- [Contents](../userguide.md)\n",
        encoding="utf-8",
    )
    (folder / "book-02-end.md").write_text(
        "# Chapter 2: End\n\n## The end\n\n```text\n# not a heading\n```\n\nBack to "
        "[the start](book-01-start.html).\n",
        encoding="utf-8",
    )
    index = tmp_path / "userguide.md"
    index.write_text(
        "# Small Guide\n\n### [Chapter 1: Start](book/book-01-start.html)\n\n"
        "- [Saving](book/book-01-start.html#saving--your-work)\n\n"
        "### [Chapter 2: End](book/book-02-end.html)\n",
        encoding="utf-8",
    )
    return index


def test_chapters_come_in_contents_order(tmp_path: Path) -> None:
    index = _small_guide(tmp_path)
    assert [p.name for p in ugf.chapter_paths(index)] == ["book-01-start.md", "book-02-end.md"]
    assert ugf.guide_files(index)[0] == index
    text = ugf.read_guide_text(index)
    assert text.index("Small Guide") < text.index("Chapter 1") < text.index("Chapter 2: End\n")


def test_a_single_file_document_reads_as_itself(tmp_path: Path) -> None:
    doc = tmp_path / "notes.md"
    doc.write_text("# Notes\n", encoding="utf-8")
    assert ugf.guide_files(doc) == [doc]
    assert ugf.read_guide_text(doc) == "# Notes\n"


def test_anchors_follow_pandoc_and_the_in_app_renderer() -> None:
    assert ugf.gfm_anchor("Saving -- your work") == "saving--your-work"
    assert ugf.gfm_anchor("Do a Document Task (Ctrl+3)") == "do-a-document-task-ctrl3"
    assert ugf.preview_anchor("Do a Document Task (Ctrl+3)") == "do-a-document-task-ctrl-3"
    assert ugf.gfm_anchor("Smileys & Emotion (169)") == "smileys--emotion-169"


def test_headings_in_code_fences_are_not_headings(tmp_path: Path) -> None:
    index = _small_guide(tmp_path)
    titles = [t for _l, t, _n in ugf.headings((tmp_path / "book" / "book-02-end.md").read_text())]
    assert titles == ["Chapter 2: End", "The end"]
    assert ugf.file_for_anchor(index, "not-a-heading") == index


def test_an_anchor_opens_its_chapter_and_none_opens_the_contents(tmp_path: Path) -> None:
    index = _small_guide(tmp_path)
    assert ugf.file_for_anchor(index, "the-end").name == "book-02-end.md"
    assert ugf.file_for_anchor(index, "saving--your-work").name == "book-01-start.md"
    assert ugf.file_for_anchor(index, None) == index
    assert ugf.file_for_anchor(index, "nowhere") == index


def test_the_one_file_book_drops_navigation_and_links_inside_itself(tmp_path: Path) -> None:
    book = ugf.single_document_text(_small_guide(tmp_path))
    assert book.startswith("# Small Guide\n")
    assert "- Next:" not in book and "[Contents]" not in book
    assert "[later](#the-end)" in book
    assert "[the start](#chapter-1-start)" in book


def test_render_keeps_the_layout_and_opens_the_right_page(tmp_path: Path) -> None:
    index = _small_guide(tmp_path)
    out = tmp_path / "out"
    opened = ugf.render_guide(index, out, "the-end")
    assert opened == out / "book" / "book-02-end.html"
    assert (out / "userguide.html").is_file() and (out / "book" / "book-01-start.html").is_file()
    assert "the-end" in opened.read_text(encoding="utf-8")
    assert ugf.render_guide(index, out) == out / "userguide.html"


@pytest.mark.parametrize("index", _GUIDES, ids=lambda p: p.parent.name)
def test_every_chapter_file_is_on_the_contents_page(index: Path) -> None:
    chapters = ugf.chapter_paths(index)
    assert len(chapters) > 15
    # Every folder the contents page links into (QUILL Lite's guide/ and, since
    # 2026-11-09, github-guide/) holds only chapters it links.
    folders = {chapter.parent for chapter in chapters}
    on_disk = sorted(path for folder in folders for path in folder.glob("*.md"))
    assert on_disk == sorted(chapters), "a chapter the contents never links"
    for chapter in chapters:
        first = ugf.headings(chapter.read_text(encoding="utf-8"))
        assert first[0][0] == 1 and [lvl for lvl, _t, _n in first].count(1) == 1, chapter.name


def test_guide_basenames_are_unique_in_the_tree() -> None:
    """The site flattens docs by basename, so a second copy would overwrite one."""
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    names = [Path(line).name for line in listed]
    for index in _GUIDES:
        for chapter in ugf.chapter_paths(index):
            assert names.count(chapter.name) <= 1, chapter.name


_LINK = re.compile(r"\]\(([^)\s]+\.html)#([^)\s]+)\)")


@pytest.mark.parametrize("index", _GUIDES, ids=lambda p: p.parent.name)
def test_every_link_between_guide_files_lands_on_a_heading(index: Path) -> None:
    broken: list[str] = []
    for part in ugf.guide_files(index):
        for target, anchor in _LINK.findall(part.read_text(encoding="utf-8")):
            if "://" in target:
                continue
            path = (part.parent / unquote(target)).with_suffix(".md")
            if path.is_file() and anchor not in ugf.anchors_in(path):
                broken.append(f"{part.name}: {target}#{anchor}")
    assert not broken, "\n".join(broken)
