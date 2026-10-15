"""Give every Markdown file in a staged docs folder its HTML and EPUB.

Run by every app's build after it has staged the docs folder it ships:

    python scripts/complete_docs_folder.py <staged docs folder> [--check]

Each app's Help menu opens the HTML and offers the EPUB, and a package that
ships a ``.md`` without them is a document somebody using the app cannot open
the way the app says they can. On 2026-10-15 the last builds had exactly that:
QUILL Cast shipped HTML but no EPUB for all four of its documents, Quill Social
shipped seven Markdown files and nothing else, Quill Beacon two, and QUILL's
portable folder its user guide alone. Each build stages its docs its own way,
so the fix is one step every build runs at the end rather than one fix per
script.

A rendering that already sits beside the Markdown (copied from the source
tree, where ``check_docs_artifacts.py`` keeps them current) is kept; only a
missing one is made, with the same Pandoc invocation, accessible template and
fixed EPUB date ``release_readiness.py`` uses, so a staged copy is identical to
a source one. ``--check`` only reports, and exits 1 if anything is missing.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_REPO = _SCRIPTS.parent
sys.path.insert(0, str(_SCRIPTS))

import release_readiness as rr  # noqa: E402


def missing(folder: Path) -> list[tuple[Path, list[str]]]:
    """Each Markdown file under *folder* and which renderings it lacks."""
    gaps: list[tuple[Path, list[str]]] = []
    for source in sorted(folder.rglob("*.md")):
        lacking = [ext for ext in (".html", ".epub") if not source.with_suffix(ext).is_file()]
        if lacking:
            gaps.append((source, lacking))
    return gaps


def _identifier(source: Path, folder: Path) -> str:
    try:
        return rr._epub_identifier(source.relative_to(_REPO))
    except ValueError:  # a staged folder outside the repo: name it by its place in the folder
        return rr._epub_identifier(Path(folder.name) / source.relative_to(folder))


def render(source: Path, lacking: list[str], folder: Path, pandoc: str) -> None:
    template = _REPO / "docs" / "pandoc" / "quill-accessible.html5"
    if ".html" in lacking:
        subprocess.run(
            [
                pandoc,
                str(source),
                "-f",
                "gfm+smart",
                "-t",
                "html5",
                "-s",
                "--template",
                str(template),
                "--metadata",
                f"pagetitle={rr._page_title(source)}",
                "-o",
                str(source.with_suffix(".html")),
            ],
            check=True,
        )
    if ".epub" in lacking:
        subprocess.run(
            [
                pandoc,
                str(source),
                "-f",
                "gfm+smart",
                "-t",
                "epub3",
                "--metadata",
                f"identifier={_identifier(source, folder)}",
                "-o",
                str(source.with_suffix(".epub")),
            ],
            check=True,
            env={**os.environ, "SOURCE_DATE_EPOCH": rr.EPUB_SOURCE_DATE_EPOCH},
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    folder = args.folder.resolve()
    if not folder.is_dir():
        print(f"No docs folder at {folder}; nothing to complete.")
        return 0
    gaps = missing(folder)
    if args.check or not gaps:
        for source, lacking in gaps:
            print(f"  {source.relative_to(folder)}: no {' or '.join(lacking)}")
        print(f"{len(gaps)} document(s) without HTML and EPUB in {folder}.")
        return 1 if gaps else 0
    pandoc = rr._resolve_pandoc()
    for source, lacking in gaps:
        render(source, lacking, folder, pandoc)
        print(f"  rendered {' and '.join(lacking)} for {source.relative_to(folder)}")
    left = missing(folder)
    print(f"Docs complete in {folder}: {len(gaps)} rendered, {len(left)} still missing.")
    return 1 if left else 0


if __name__ == "__main__":
    raise SystemExit(main())
