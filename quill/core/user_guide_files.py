"""The user guides as files: a contents page plus one file per chapter.

QUILL's guide and QUILL Lite's each used to be one Markdown file, 25,000 and
11,000 lines long. They are now a contents page, ``userguide.md``, which stays
where it always was, and a folder of chapter files beside it
(``docs/user guide/quill-guide/`` and ``standalone/quilllite/docs/guide/``).
The contents page links every chapter as ``<folder>/<chapter>.html``, in
reading order, and that list of links *is* the order: nothing else names the
chapters, so adding one is one line in the contents and nothing here.

Everything that used to read the one file reads through this module instead:

- the gates that scan what a guide teaches (documentation chords, GATE-DOCKEY,
  the menu and settings audits, QUILL Lite's docs tests) read
  :func:`read_guide_text`, the contents and every chapter joined, or walk
  :func:`guide_files` when they report a file and line;
- Help > User Guide renders the guide with :func:`render_guide` and opens the
  chapter holding the anchor F1 asked for (:func:`file_for_anchor`);
- the release renderers build the whole-book EPUB from
  :func:`single_document_text`, so there is still one ``userguide.epub`` to
  read from start to finish.

No ``wx`` here: it is called from gates and build scripts as well as the UI.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote

INDEX_NAME = "userguide.md"

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The two split guides, as they sit in the source tree.
QUILL_GUIDE = _REPO_ROOT / "docs" / "user guide" / INDEX_NAME
LITE_GUIDE = _REPO_ROOT / "standalone" / "quilllite" / "docs" / INDEX_NAME

#: The manual both guides' WordPress and Forms chapters hand over to.
WORDPRESS_FORMS_MANUAL = (
    _REPO_ROOT / "docs" / "user guide" / "wordpress-and-forms" / "wordpress-forms-guide.md"
)

#: A contents-page link to a chapter: ``](quill-guide/quill-guide-03-x.html#y)``.
_CHAPTER_LINK = re.compile(
    r"\]\((?P<folder>[A-Za-z0-9_-]+)/(?P<stem>[A-Za-z0-9_-]+)\.html(?:#[^)\s]*)?\)"
)
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
_LINK = re.compile(r"(?<!!)\[(?P<text>[^\]]*)\]\((?P<target>[^)\s]+)\)")

#: The last block of every chapter: a rule, then Previous, Next and Contents.
#: The whole-book EPUB drops it, because "Next" is simply the next page there.
NAV_RULE = "---"
_NAV_ITEM = re.compile(r"^- (?:Previous: |Next: )?\[[^\]]+\]\([^)]+\)\s*$")


def chapter_paths(index: Path) -> list[Path]:
    """The chapter files *index* links, in the order it links them.

    Empty for a guide that is still one file, or one that cannot be read.
    """
    try:
        text = index.read_text(encoding="utf-8")
    except OSError:
        return []
    found: list[Path] = []
    for match in _CHAPTER_LINK.finditer(text):
        path = index.parent / match["folder"] / f"{match['stem']}.md"
        if path not in found and path.is_file():
            found.append(path)
    return found


def guide_files(path: Path) -> list[Path]:
    """*path* and, when it is a split guide's contents page, every chapter."""
    return [path, *chapter_paths(path)]


def manual_files(index: Path = WORDPRESS_FORMS_MANUAL) -> list[Path]:
    """The WordPress and Forms manual: its index, then the pages it links.

    The manual keeps its pages beside its index (``](wordpress-forms-01-x.html)``),
    so they are read in the order the index links them.
    """
    try:
        text = index.read_text(encoding="utf-8")
    except OSError:
        return []
    found = [index]
    for match in _LINK.finditer(text):
        target = match["target"].partition("#")[0]
        if "/" in target or "://" in target or not target.endswith(".html"):
            continue
        path = index.parent / f"{target[: -len('.html')]}.md"
        if path not in found and path.is_file():
            found.append(path)
    return found


def read_guide_text(path: Path) -> str:
    """The whole guide's text: the contents page, then each chapter in order.

    For a split guide (QUILL's or QUILL Lite's) this also includes the shared
    WordPress and Forms manual, which their WordPress and Forms chapters hand
    over to: a gate asking whether "the guide" names a command is asking about
    everything a reader is sent to. A document that is not a split guide reads
    as itself, so a gate can call this for every file in its corpus.
    """
    parts = guide_files(path)
    if len(parts) > 1:
        parts += manual_files()
    return "\n\n".join(part.read_text(encoding="utf-8") for part in parts)


def _unfenced_lines(text: str) -> Iterator[tuple[int, str]]:
    """(line index, line) for every line outside a fenced code block."""
    fence: str | None = None
    for number, line in enumerate(text.splitlines()):
        match = _FENCE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)
                continue
            yield number, line
        elif match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
            if not line.strip()[len(match.group(1)) :].strip():
                fence = None


def headings(text: str) -> list[tuple[int, str, int]]:
    """(level, title, line index) for every ATX heading outside a code fence."""
    found: list[tuple[int, str, int]] = []
    for number, line in _unfenced_lines(text):
        match = _HEADING.match(line)
        if match:
            title = re.sub(r"[ \t]+#+$", "", match.group(2)).strip()
            found.append((len(match.group(1)), title, number))
    return found


def _plain(title: str) -> str:
    """A heading's text as Pandoc sees it: no link targets, code ticks or emphasis."""
    title = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", title)
    title = title.replace("`", "")
    title = re.sub(r"(\*\*|__|\*|~~)", "", title)
    return title.replace("\\", "")


def gfm_anchor(title: str) -> str:
    """The id Pandoc gives a heading (``-f gfm+smart``), before de-duplication.

    Lower case; letters, digits, ``_``, ``-`` and spaces kept, everything else
    dropped; spaces become hyphens. ``+smart`` turns ``--`` and ``---`` into
    dashes first, which are then dropped like any other punctuation.
    """
    text = _plain(title).replace("---", "").replace("--", "").lower()
    kept = "".join(ch for ch in text if ch.isalnum() or ch in "_- ")
    return kept.replace(" ", "-")


def preview_anchor(title: str) -> str:
    """The id QUILL's own renderer gives a heading (``browser_preview._slugify``)."""
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return normalized or "preview"


def heading_anchors(text: str) -> list[tuple[str, str]]:
    """(Pandoc id, QUILL renderer id) for each heading, Pandoc's de-duplicated."""
    seen: dict[str, int] = {}
    found: list[tuple[str, str]] = []
    for _level, title, _line in headings(text):
        base = gfm_anchor(title)
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.append((base if count == 0 else f"{base}-{count}", preview_anchor(title)))
    return found


def anchors_in(path: Path) -> set[str]:
    """Every id a heading in *path* answers to, in either renderer."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {anchor for pair in heading_anchors(text) for anchor in pair}


def file_for_anchor(index: Path, anchor: str | None) -> Path:
    """The guide file whose heading has *anchor*; the contents page otherwise.

    Chapters are searched before the contents page, whose own headings repeat
    the chapter titles and would otherwise answer first.
    """
    if anchor:
        for path in [*chapter_paths(index), index]:
            if anchor in anchors_in(path):
                return path
    return index


def _strip_nav(text: str) -> str:
    """*text* without its closing Previous / Next / Contents block."""
    lines = text.rstrip("\n").split("\n")
    end = len(lines)
    while end > 0 and _NAV_ITEM.match(lines[end - 1]):
        end -= 1
    if end == len(lines):
        return text
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    if end > 0 and lines[end - 1].strip() == NAV_RULE:
        return "\n".join(lines[: end - 1]).rstrip("\n") + "\n"
    return text


def single_document_text(index: Path) -> str:
    """The whole guide as one Markdown document, for the one-file EPUB.

    The contents page's title and opening, then every chapter without its
    navigation block. A link from one guide file to another becomes a link to
    the anchor inside this one document (the target's first heading when the
    link named none).
    """
    chapters = chapter_paths(index)
    if not chapters:
        return index.read_text(encoding="utf-8")
    first_anchor: dict[Path, str] = {}
    texts: dict[Path, str] = {}
    for path in chapters:
        texts[path] = _strip_nav(path.read_text(encoding="utf-8"))
        pairs = heading_anchors(texts[path])
        first_anchor[path] = pairs[0][0] if pairs else ""
    index_text = index.read_text(encoding="utf-8")
    title = next((t for level, t, _n in headings(index_text) if level == 1), "User Guide")

    def relink(source: Path, text: str) -> str:
        def swap(match: re.Match[str]) -> str:
            target = match["target"]
            if "://" in target or target.startswith(("#", "mailto:")):
                return match.group(0)
            path_part, _sep, fragment = target.partition("#")
            resolved = (source.parent / unquote(path_part)).resolve().with_suffix(".md")
            for chapter in chapters:
                if chapter.resolve() == resolved:
                    anchor = fragment or first_anchor[chapter]
                    return f"[{match['text']}](#{anchor})"
            return match.group(0)

        return _LINK.sub(swap, text)

    parts = [f"# {title}\n"] + [relink(path, texts[path]) for path in chapters]
    return "\n\n".join(part.rstrip("\n") for part in parts) + "\n"


def _localise_links(source: Path, text: str, guide: set[Path]) -> str:
    """Point links that leave the guide at the files they name, by ``file:`` URL.

    The rendered copy lives under the app's data folder, where a relative link
    to a sibling document (``../tutorials.md``) would find nothing. Links
    between guide files stay relative, because the copy keeps their layout.
    """

    def swap(match: re.Match[str]) -> str:
        target = match["target"]
        if "://" in target or target.startswith(("#", "mailto:", "/")):
            return match.group(0)
        path_part, sep, fragment = target.partition("#")
        resolved = (source.parent / unquote(path_part)).resolve()
        if resolved.with_suffix(".md") in guide:
            return match.group(0)
        for candidate in (resolved.with_suffix(".html"), resolved):
            if candidate.is_file():
                return f"[{match['text']}]({candidate.as_uri()}{sep}{fragment})"
        return match.group(0)

    return _LINK.sub(swap, text)


def render_guide(index: Path, out_dir: Path, start_anchor: str | None = None) -> Path:
    """Render every file of the guide into *out_dir*; return the page to open.

    The layout is kept (``userguide.html`` and ``<folder>/<chapter>.html``) so
    the links between pages work in the copy. The page returned is the chapter
    holding *start_anchor*, rendered to scroll to it, or the contents page.
    Raises ``OSError`` when a file cannot be read or written.
    """
    from quill.core.browser_preview import render_preview_html

    files = guide_files(index)
    guide = {path.resolve() for path in files}
    page = file_for_anchor(index, start_anchor)
    opened = out_dir / "userguide.html"
    for source in files:
        text = _localise_links(source, source.read_text(encoding="utf-8"), guide)
        title = next((t for level, t, _n in headings(text) if level == 1), "User Guide")
        anchor = start_anchor if source == page else None
        html = render_preview_html(_plain(title), text, "markdown", start_anchor=anchor)
        target = out_dir / source.relative_to(index.parent).with_suffix(".html")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".tmp")
        temp.write_text(html, encoding="utf-8")
        os.replace(temp, target)
        if source == page:
            opened = target
    return opened


def main(argv: list[str] | None = None) -> int:
    """``python -m quill.core.user_guide_files book <userguide.md> <out.md>``

    Writes :func:`single_document_text` for a render script that has no other
    way to reach it (``standalone/quilllite/scripts/render_docs.ps1``).
    """
    import sys

    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3 or args[0] != "book":
        print("usage: python -m quill.core.user_guide_files book <userguide.md> <out.md>")
        return 2
    Path(args[2]).write_text(single_document_text(Path(args[1])), encoding="utf-8", newline="\n")
    return 0


__all__ = [
    "INDEX_NAME",
    "LITE_GUIDE",
    "WORDPRESS_FORMS_MANUAL",
    "NAV_RULE",
    "QUILL_GUIDE",
    "anchors_in",
    "chapter_paths",
    "file_for_anchor",
    "gfm_anchor",
    "guide_files",
    "heading_anchors",
    "manual_files",
    "headings",
    "preview_anchor",
    "read_guide_text",
    "render_guide",
    "single_document_text",
]


if __name__ == "__main__":
    raise SystemExit(main())
