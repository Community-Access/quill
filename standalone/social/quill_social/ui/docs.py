"""Finding and opening the documentation QUILL Social ships with itself.

The installer has always placed the user guide (and the architecture, keymap and
PRD notes) in a ``docs`` folder beside the program, and the Start menu even gets
a shortcut to it -- but nothing inside the app could open any of it. This module
is the missing half.

Resolution order mirrors the one the other QuillVille apps use:

1. a packaged build's own ``docs\\`` next to the exe -- HTML first, because it
   opens in a browser where a screen reader already has heading, link and
   find-in-page navigation, and Markdown is what Windows has no default handler
   for;
2. this checkout's ``standalone/social/docs``, so the menu items work in a dev
   run too rather than silently doing nothing.

Path resolution is kept pure and separate from opening so it can be tested
without a browser or a frozen build.
"""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["DOC_TITLES", "doc_candidates", "find_doc", "open_doc"]

#: The docs worth offering on the Help menu, as stem -> human title. The
#: remaining files that ship (ARCHITECTURE, PHASES, TESTING, QUILLIN_ADAPTERS)
#: are contributor notes, not user documentation, so they stay off the menu --
#: they are still in the docs folder for anyone who wants them.
DOC_TITLES: dict[str, str] = {
    "USER_GUIDE": "QUILL Social User Guide",
    "KEYMAP_SPEC": "QUILL Social Keyboard Reference",
    "QUILL_Social_PRD_Working_Draft": "QUILL Social Product Requirements",
}


def doc_candidates(stem: str) -> list[Path]:
    """Every path *stem* might live at, best first.

    HTML precedes Markdown at each root: a ``.md`` file has no default handler
    on a stock Windows install, so opening one can do nothing at all.
    """
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        exe_docs = Path(sys.executable).resolve().parent / "docs"
        candidates.append(exe_docs / f"{stem}.html")
        candidates.append(exe_docs / f"{stem}.md")
    # quill_social/ui/docs.py -> quill_social/ui -> quill_social -> standalone/social
    repo_docs = Path(__file__).resolve().parents[2] / "docs"
    candidates.append(repo_docs / f"{stem}.html")
    candidates.append(repo_docs / f"{stem}.md")
    return candidates


def find_doc(stem: str) -> Path | None:
    """The first candidate that exists, or None when the doc did not ship."""
    for candidate in doc_candidates(stem):
        try:
            if candidate.is_file():
                return candidate
        except OSError:  # pragma: no cover - an unreadable path is simply not it
            continue
    return None


def open_doc(stem: str) -> Path | None:
    """Open *stem* in the system browser. Returns the path opened, or None.

    Never raises: a missing doc or a machine with no browser association is
    reported to the caller so it can say so out loud, rather than throwing out
    of a menu handler.
    """
    path = find_doc(stem)
    if path is None:
        return None
    try:
        import webbrowser

        webbrowser.open(path.as_uri())
    except Exception:  # noqa: BLE001 - a failed open is reported, never fatal
        return None
    return path
