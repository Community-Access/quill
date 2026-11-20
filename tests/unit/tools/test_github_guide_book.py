"""The GitHub Guide as one book, for each editor, cannot drift (GH-R-115)."""

from __future__ import annotations

import re

from quill.tools import build_github_guide_book as book


def test_the_committed_books_match_the_guides() -> None:
    for path, wanted in book.outputs().items():
        assert path.read_text(encoding="utf-8") == wanted, (
            f"{path.name} drifted. Regenerate with: "
            "python -m quill.tools.build_github_guide_book --write"
        )


def test_every_chapter_is_in_its_book_in_order_and_links_stay_inside() -> None:
    for folder, prefix in book.GUIDES:
        text = (folder / f"{prefix}-book.md").read_text(encoding="utf-8")
        chapters = sorted(folder.glob(f"{prefix}-[0-9][0-9]-*.md"))
        headings = re.findall(r"^# (Chapter \d+:.*)$", text, re.M)
        assert len(headings) == len(chapters) >= 13
        numbers = [int(re.match(r"Chapter (\d+)", h).group(1)) for h in headings]
        assert numbers == sorted(numbers)
        assert not re.search(rf"\]\({prefix}[^)]*\.(?:html|md)", text), "a link leaves the book"
        assert "- Previous: " not in text
        assert (folder / f"{prefix}-book.epub").exists()
