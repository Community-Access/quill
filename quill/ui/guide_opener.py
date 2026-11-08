"""Open an editor's guides in the browser: Help > Open User Guide, Open GitHub Guide.

QUILL and QUILL Lite share this, so the two editors find and open their guides
the same way in every download (:mod:`quill.core.guide_locations` says where
they look). The user guide is rendered from its Markdown by
:func:`quill.core.user_guide_files.render_guide`, which is what lets F1 open
the chapter holding a section; the GitHub Guide opens as the HTML that ships
beside it.

Callers pass ``report``, the way each editor tells the person what happened
(QUILL's status bar, QUILL Lite's announcement), so the outcome is said once
and in that editor's voice. No wx here: :func:`register_github_guide_help`
only hands an opener to the F1 engine, which imports wx when F1 is pressed.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from pathlib import Path

from quill.core.guide_locations import Guide, Product, find_guide

__all__ = [
    "GITHUB_GUIDE_BUTTON",
    "is_github_window",
    "open_guide",
    "register_github_guide_help",
]

#: The F1 window's button in a GitHub window.
GITHUB_GUIDE_BUTTON = "Open GitHub Guide"

_PRODUCT_NAMES: dict[Product, str] = {"quill": "QUILL", "quilllite": "QUILL Lite"}

#: The sentence for each outcome: (opened, saved-or-found-at, could-not-open).
_WORDS: dict[Guide, tuple[str, str, str]] = {
    "user": ("Opened user guide in browser", "User guide saved to", "Could not open user guide"),
    "github": (
        "Opened GitHub Guide in browser",
        "GitHub Guide is at",
        "Could not open GitHub Guide",
    ),
}


def open_guide(
    product: Product,
    guide: Guide,
    *,
    render_dir: Path | None = None,
    report: Callable[[str], None],
    start_anchor: str | None = None,
) -> bool:
    """Open *product*'s *guide*; False when no copy of it is on disk.

    *render_dir* is where a Markdown guide is rendered (the editor's data
    folder); a guide that ships as HTML needs none.

    A missing user guide is the caller's to answer (QUILL opens its welcome
    guide instead); a missing GitHub Guide is reported here, because nothing
    else could stand in for it.
    """
    opened, elsewhere, failed = _WORDS[guide]
    path = find_guide(product, guide)
    if path is None:
        if guide == "github":
            report(
                f"The GitHub Guide is not in this copy of {_PRODUCT_NAMES[product]}. "
                "Reinstalling puts it back."
            )
        return False
    page = path
    if path.suffix.lower() == ".md" and render_dir is not None:
        from quill.core.user_guide_files import render_guide

        try:
            page = render_guide(path, render_dir, start_anchor)
        except OSError as error:
            report(f"{failed}: {error}")
            return True
    if webbrowser.open(page.as_uri()):
        report(opened)
    else:
        report(f"{elsewhere} {page}")
    return True


def is_github_window(title: str) -> bool:
    """True for the GitHub windows: GitHub Items, Explore GitHub, a review."""
    lowered = title.strip().lower()
    return "github" in lowered or lowered.startswith("review pull request")


def register_github_guide_help(product: Product, report: Callable[[str], None]) -> None:
    """Give every GitHub window's F1 answer a button that opens the GitHub Guide."""
    from quill.ui import app_context_help

    def _open() -> None:
        open_guide(product, "github", report=report)

    app_context_help.register_guide_route(is_github_window, GITHUB_GUIDE_BUTTON, _open)
