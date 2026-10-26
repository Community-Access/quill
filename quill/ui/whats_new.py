"""Help > What's New: an app's changelog, opened as HTML in the browser.

One module for the whole family, because the question is the same everywhere --
"what changed in this app?" -- and so is the answer: the ``CHANGELOG`` every app
already renders to HTML beside its user guide. Ten copies of the lookup would be
ten chances for one of them to look in the wrong folder, which is how Quill
Radio 3.0 lost its User Guide (``quill.core.app_folders``).

Where a changelog is looked for, in order:

* a packaged build's own ``docs\\`` beside the program (the launcher's folder,
  never the shared runtime's, which holds no documents);
* this checkout's ``standalone/<app>/docs`` -- or, for QUILL itself, the
  repository root, where QUILL's own changelog lives.

HTML is preferred because that is what a browser shows properly. A Markdown
changelog is the fallback, rendered through the same preview renderer the app
shells use and cached in the data folder, so a dev run is not empty-handed.

Callers pass their own ``announce``, so the result -- opened, or why not -- is
spoken the way each app speaks. Only :func:`append_whats_new_item`, the
one-line menu row for an app shell, touches wx, and imports it when called.
"""

from __future__ import annotations

import os
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

__all__ = [
    "APP_MENU_LABEL",
    "append_whats_new_item",
    "changelog_candidates",
    "find_changelog",
    "open_whats_new",
]

#: The row in a standalone app's Help menu, on the key every one of them gives
#: it. The two editors are keyless instead (keymap.py's help.whats_new), and
#: Quill Radio writes What's &New because its What Is This? owns W.
APP_MENU_LABEL = "&What's New\tCtrl+Shift+F1"

#: The repository root (``quill/ui/whats_new.py`` -> two levels up).
_REPO_ROOT = Path(__file__).resolve().parents[2]

#: QUILL itself keeps its changelog at the repository root, not under standalone/.
_QUILL_APP = "quill"


def changelog_candidates(app: str, *, folders: list[Path] | None = None) -> list[Path]:
    """Every place *app*'s changelog may be, most specific first.

    *app* is the folder name under ``standalone/`` (``"radio"``, ``"quilllite"``),
    or ``"quill"`` for QUILL itself. *folders* overrides
    :func:`quill.core.app_folders.app_folders`, for tests.
    """
    if folders is None:
        from quill.core.app_folders import app_folders

        folders = app_folders()
    roots = [folder / "docs" for folder in folders]
    if app == _QUILL_APP:
        roots.extend([_REPO_ROOT, _REPO_ROOT / "docs"])
    else:
        roots.append(_REPO_ROOT / "standalone" / app / "docs")
        roots.append(_REPO_ROOT / "standalone" / app)
    return [root / f"CHANGELOG{suffix}" for root in roots for suffix in (".html", ".md")]


def find_changelog(app: str, *, folders: list[Path] | None = None) -> Path | None:
    """The first changelog that exists for *app*, or None."""
    for candidate in changelog_candidates(app, folders=folders):
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _rendered(path: Path, title: str) -> Path:
    """*path* itself when it is HTML; otherwise a rendered copy in the data folder."""
    if path.suffix.lower() == ".html":
        return path
    from quill.core.browser_preview import render_preview_html
    from quill.core.paths import app_data_dir

    html = render_preview_html(title, path.read_text(encoding="utf-8"), "markdown")
    target_dir = app_data_dir() / "whats-new"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{path.parent.name}-CHANGELOG.html"
    temp = target.with_suffix(".tmp")
    temp.write_text(html, encoding="utf-8")
    os.replace(temp, target)
    return target


def open_whats_new(
    app: str,
    app_name: str,
    announce: Callable[[str], object],
    *,
    folders: list[Path] | None = None,
    open_url: Callable[[str], bool] = webbrowser.open,
) -> bool:
    """Open *app*'s changelog in the browser; True when it opened.

    Every outcome is spoken through *announce*, because the browser taking focus
    is the only other sign anything happened, and a missing changelog -- a
    stripped build, a checkout without rendered docs -- must say so rather than
    do nothing.
    """
    title = f"What's New in {app_name}"
    found = find_changelog(app, folders=folders)
    if found is None:
        announce(f"{title} was not found in this build.")
        return False
    try:
        target = _rendered(found, title)
    except OSError as error:
        announce(f"Could not open {title}: {error}")
        return False
    if open_url(target.as_uri()):
        announce(f"Opened {title} in your browser")
        return True
    announce(f"{title} is at {target}")
    return False


def append_whats_new_item(
    host: Any, menu: Any, app: str, app_name: str, *, label: str = APP_MENU_LABEL
) -> Any:
    """Append Help > What's New to *menu*, bound on *host*'s frame; returns its id.

    For the app-shell family (a ``frame``, an ``_announce`` and, where it has
    one, ``_keep_menu_ids`` -- a ``wx.NewIdRef`` nothing holds is recycled, and a
    recycled id is a row that stops firing).
    """
    import wx

    item_id = wx.NewIdRef()
    menu.Append(item_id, label)
    host.frame.Bind(
        wx.EVT_MENU, lambda _e: open_whats_new(app, app_name, host._announce), id=item_id
    )
    keep = getattr(host, "_keep_menu_ids", None)
    if callable(keep):
        keep(item_id)
    return item_id
