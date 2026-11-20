"""Write QUILL Lite's copy of the GitHub Guide from QUILL's.

The GitHub Workbench is one window both editors open, so the GitHub Guide is
one book. QUILL ships it as ``docs/user guide/github-guide/github-guide*.md``;
QUILL Lite ships its own copy, ``standalone/quilllite/docs/github-guide/
lite-github-guide*.md``, because each app's Help menu opens the documents in
its own docs folder.

The two copies were edited by hand until 2026-11-20, and drifted: a chapter
fixed in one book stayed wrong in the other, and the Lite contents page still
linked headings the QUILL book had renamed. Now QUILL's book is the source and
this script writes the copy. It changes only what has to differ:

- file names and the links between chapters, ``github-guide-`` to
  ``lite-github-guide-``;
- the closing link back to the editor's own user guide, which is QUILL Lite's;
- a link out of the book that does not resolve beside QUILL Lite's guide (a
  QUILL Guide chapter, say) keeps its words and loses the link, so the copy
  never ships a dead one.

Run it after editing the QUILL book, then render both:

    python scripts/sync_lite_github_guide.py          # write the copy
    python scripts/sync_lite_github_guide.py --check  # exit 1 if it has drifted

``tests/unit/docs/test_lite_github_guide_sync.py`` runs ``--check``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
SOURCE = _ROOT / "docs" / "user guide" / "github-guide"
TARGET = _ROOT / "standalone" / "quilllite" / "docs" / "github-guide"

_LINK = re.compile(r"(?<!!)\[(?P<text>[^\]]*)\]\((?P<target>[^)\s]+)\)")


def lite_name(name: str) -> str:
    """``github-guide-04-issues.md`` -> ``lite-github-guide-04-issues.md``."""
    return f"lite-{name}" if name.startswith("github-guide") else name


def _relink(match: re.Match[str]) -> str:
    text, target = match.group("text"), match.group("target")
    path, _, anchor = target.partition("#")
    if not path or "://" in path or path.startswith("mailto:"):
        return match.group(0)
    if path.startswith("github-guide"):
        new = lite_name(path) + (f"#{anchor}" if anchor else "")
        return f"[{text}]({new})"
    if path == "../userguide.html":
        if text == "QUILL User Guide":
            text = "QUILL Lite User Guide"
        return f"[{text}]({target})"
    resolved = (TARGET / path).with_suffix(".md")
    if resolved.exists() or (TARGET / path).exists():
        return match.group(0)
    return text


def lite_text(text: str) -> str:
    """QUILL's chapter text as QUILL Lite's copy of it."""
    return _LINK.sub(_relink, text)


def expected() -> dict[Path, str]:
    """Every file of QUILL Lite's copy, and what it should say."""
    return {
        TARGET / lite_name(source.name): lite_text(source.read_text(encoding="utf-8"))
        for source in sorted(SOURCE.glob("github-guide*.md"))
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report drift; write nothing")
    args = parser.parse_args(argv)
    want = expected()
    stale = sorted(path.name for path in TARGET.glob("lite-github-guide*.md") if path not in want)
    drift = [
        path.name
        for path, text in want.items()
        if not path.exists() or path.read_text(encoding="utf-8") != text
    ]
    if args.check:
        for name in drift:
            print(f"out of date: {name}")
        for name in stale:
            print(f"no QUILL chapter for: {name}")
        return 1 if drift or stale else 0
    TARGET.mkdir(parents=True, exist_ok=True)
    for path, text in want.items():
        if path.name in drift:
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {path.name}")
    for name in stale:
        for suffix in (".md", ".html", ".epub"):
            (TARGET / name).with_suffix(suffix).unlink(missing_ok=True)
        print(f"removed {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
