#!/usr/bin/env python3
"""Publish the tutorials as accessible HTML under docs/site/tutorials/.

Converts every ``docs/tutorials/*.md`` with pandoc (standalone, ``lang=en``),
rewrites inter-tutorial ``.md`` links to ``.html``, and points the index's
user-guide and podcast references at their site homes.

Usage::

    python docs/tutorials/build_html.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
SITE_DIR = REPO_ROOT / "docs" / "site" / "tutorials"


def main() -> int:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise SystemExit("pandoc is required to build the tutorial pages.")
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    sources = sorted(HERE.glob("*.md"))
    for source in sources:
        target = SITE_DIR / (
            "index.html" if source.name == "README.md" else source.with_suffix(".html").name
        )
        html = subprocess.run(
            [
                pandoc,
                str(source),
                "--standalone",
                "--from",
                "gfm",
                "--to",
                "html5",
                "--css",
                "/assets/style.css",
                "--metadata",
                "lang=en",
                "--metadata",
                f"pagetitle=QUILL Tutorials - {source.stem}",
            ],
            capture_output=True,
            encoding="utf-8",
            check=True,
        ).stdout
        # Site chrome: a small landmark nav so every tutorial links home, to
        # the tutorial index, and to the podcast that teaches the same ground.
        nav = (
            '<header class="site"><div class="wrap">'
            '<nav class="site" aria-label="Primary"><ul>'
            '<li><a href="/index.html">QUILL home</a></li>'
            '<li><a href="index.html">All tutorials</a></li>'
            '<li><a href="/podcast/index.html">The QUILL Cast</a></li>'
            '<li><a href="/docs/userguide.html">User guide</a></li>'
            "</ul></nav></div></header>"
        )
        html = html.replace("<body>", "<body>\n" + nav, 1)
        # Inter-tutorial links: point at the sibling HTML pages.
        html = re.sub(r'href="(\d\d-[^"]+)\.md"', r'href="\1.html"', html)
        html = html.replace('href="README.md"', 'href="index.html"')
        # Repo-relative references that exist elsewhere on the site.
        html = html.replace('href="../user%20guide/userguide.md"', 'href="../docs.html"').replace(
            'href="../podcast/README.md"', 'href="../podcast/index.html"'
        )
        target.write_text(html, encoding="utf-8")
        print(f"wrote {target.relative_to(REPO_ROOT)}")
    print(f"{len(sources)} tutorial pages published.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
