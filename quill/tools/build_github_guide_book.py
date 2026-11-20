"""Generate the GitHub Guide as one book, for each editor (GitHub PRD D15, GH-R-115).

The guide is written as a contents page and thirteen chapter pages, which
is right for F1 (Ctrl+F1 opens the chapter for where you are) and awkward
to carry: a reading app or a braille display wants one book. This joins the
same Markdown, in order, into ``<prefix>-book.md`` beside each guide's chapter
folder (``github-guide-book.md`` for QUILL, ``lite-github-guide-book.md`` for QUILL
Lite), not in it, since that folder holds only the chapters its contents page
links. So the book is the guide and cannot say anything else:

- the contents page's opening and Keys at a glance come first, then each
  chapter, its own level 1 heading starting a new section of the EPUB;
- each chapter's Previous, Next and Contents links are left out (the book
  has its own table of contents), and a link to another chapter becomes a
  link inside the book.

The EPUB and HTML are rendered from the book's Markdown the way every guide
page is (``scripts/release_readiness.py``: pandoc, the accessible template).
``tests/unit/tools/test_github_guide_book.py`` fails when a committed book's
Markdown differs from what this writes. Regenerate with::

    python -m quill.tools.build_github_guide_book --write
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from quill.core.user_guide_files import _published_url

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: (guide folder, the file-name prefix of its pages).
GUIDES: tuple[tuple[Path, str], ...] = (
    (_REPO_ROOT / "docs" / "user guide" / "github-guide", "github-guide"),
    (_REPO_ROOT / "standalone" / "quilllite" / "docs" / "github-guide", "lite-github-guide"),
)

_LINK = re.compile(
    r"\]\((?P<file>[a-z-]*github-guide(?:-\d\d-[a-z0-9-]+)?)\.(?:html|md)(?P<frag>#[^)]*)?\)"
)
_OUTWARD = re.compile(r"\]\((?P<target>\.\./[^)\s]+\.html(?:#[^)\s]*)?)\)")
_NAV = re.compile(r"\n---\n\n- (?:Previous|Next): .*\Z", re.S)


def _slug(heading: str) -> str:
    """GitHub's heading id, as pandoc's gfm reader makes it."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def _first_heading(text: str) -> str:
    match = re.search(r"^# (.+)$", text, re.M)
    return match.group(1).strip() if match else ""


def book(folder: Path, prefix: str) -> str:
    """The whole guide in *folder* as one Markdown book."""
    contents = (folder / f"{prefix}.md").read_text(encoding="utf-8")
    chapters = sorted(folder.glob(f"{prefix}-[0-9][0-9]-*.md"))
    titles = {path.stem: _first_heading(path.read_text(encoding="utf-8")) for path in chapters}
    title = _first_heading(contents)

    def relink(text: str) -> str:
        def swap(match: re.Match[str]) -> str:
            frag = match.group("frag")
            if frag:
                return f"]({frag})"
            name = match.group("file")
            target = titles.get(name) or title
            return f"](#{_slug(target)})"

        def outward(match: re.Match[str]) -> str:
            # A link to another document leaves the book: its page on the website.
            path_part, _sep, frag = match.group("target").partition("#")
            published = _published_url((folder / path_part).resolve().with_suffix(".md"))
            if not published:
                return match.group(0)
            return f"]({published}{'#' + frag if frag else ''})"

        return _OUTWARD.sub(outward, _LINK.sub(swap, text))

    opening = contents.split("\n## The chapters", 1)[0].rstrip()
    parts = [
        relink(opening),
        "",
        "This is the whole guide as one book: the same chapters as the guide's own "
        "pages, in order, each starting with its level 1 heading.",
    ]
    for path in chapters:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        parts += ["", relink(_NAV.sub("\n", text).rstrip())]
    return "\n".join(parts).rstrip() + "\n"


def outputs() -> dict[Path, str]:
    return {folder.parent / f"{prefix}-book.md": book(folder, prefix) for folder, prefix in GUIDES}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write both books")
    args = parser.parse_args(argv)
    drifted = []
    for path, wanted in outputs().items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if args.write:
            path.write_text(wanted, encoding="utf-8", newline="\n")
            print(f"wrote {path.relative_to(_REPO_ROOT)}")
        elif current != wanted:
            drifted.append(str(path.relative_to(_REPO_ROOT)))
    if drifted:
        print(f"{', '.join(drifted)} drifted; run with --write")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
