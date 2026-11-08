"""Where each editor's guides are on disk, in every kind of download.

One answer for both editors, because the question is the same and a second
copy is how one of them ends up looking in the wrong folder. QUILL's Help >
Open User Guide used to look beside its own source file and in the working
directory, which in an installed copy is ``{app}\\Lib\\site-packages\\quill``
and wherever Windows started it from: after an Open With launch neither held a
guide, and QUILL opened the welcome guide instead.

A guide is looked for, in order:

* the app's own folder -- beside the program the person started
  (:func:`quill.core.app_folders.app_folders`: ``QUILL_LAUNCHER_DIR``, then the
  running Python's folder), then a portable copy's root (``QUILL_APP_ROOT``),
  then a macOS bundle's ``Contents/Resources`` (``RESOURCEPATH``), then every
  folder above this module, which is how an installed QUILL finds ``{app}``
  from ``{app}\\Lib\\site-packages\\quill\\core``;
* this checkout's source tree, for a development run.

The installed layout is the one the packagers write: ``docs\\userguide.md``
beside the chapter folder (``quill-guide`` for QUILL, ``guide`` for QUILL Lite)
and the GitHub Guide at ``docs\\github-guide\\github-guide.html`` (QUILL) or
``docs\\guide\\lite-github-guide.html`` (QUILL Lite). A user guide only counts
when its chapter folder is beside it, so a folder holding the other editor's
guide is never mistaken for this one's.

wx-free and strict-typed: the editors, the F1 engine and the tests call it.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

__all__ = [
    "GUIDE_TITLES",
    "Guide",
    "Product",
    "find_guide",
    "guide_candidates",
    "search_roots",
]

Product = Literal["quill", "quilllite"]
Guide = Literal["user", "github"]

#: How each guide is named when a message has to say it could not be found.
GUIDE_TITLES: dict[Guide, str] = {"user": "User guide", "github": "GitHub Guide"}

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: (file under the root, folder that must sit beside it or "") per layout.
_INSTALLED: dict[tuple[Product, Guide], tuple[tuple[str, str], ...]] = {
    ("quill", "user"): (("docs/userguide.md", "docs/quill-guide"),),
    ("quill", "github"): (("docs/github-guide/github-guide.html", ""),),
    ("quilllite", "user"): (("docs/userguide.md", "docs/guide"),),
    ("quilllite", "github"): (("docs/guide/lite-github-guide.html", ""),),
}

_SOURCE: dict[tuple[Product, Guide], str] = {
    ("quill", "user"): "docs/user guide/userguide.md",
    ("quill", "github"): "docs/user guide/github-guide/github-guide.html",
    ("quilllite", "user"): "standalone/quilllite/docs/userguide.md",
    ("quilllite", "github"): "standalone/quilllite/docs/guide/lite-github-guide.html",
}


def search_roots(
    *, env: Mapping[str, str] | None = None, executable: str | None = None
) -> list[Path]:
    """Every folder an installed or portable copy may keep ``docs`` in, in order."""
    from quill.core.app_folders import app_folders

    environ = os.environ if env is None else env
    roots = app_folders(env=environ, executable=executable)
    for variable in ("QUILL_APP_ROOT", "RESOURCEPATH"):
        value = (environ.get(variable) or "").strip()
        if value:
            roots.append(Path(value))
    roots.extend(Path(__file__).resolve().parents)
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def guide_candidates(
    product: Product, guide: Guide, *, roots: list[Path] | None = None
) -> list[tuple[Path, Path | None]]:
    """(file, folder that must exist beside it) for every place *guide* may be."""
    found: list[tuple[Path, Path | None]] = []
    for root in search_roots() if roots is None else roots:
        for file, folder in _INSTALLED[(product, guide)]:
            found.append((root / file, root / folder if folder else None))
    found.append((_REPO_ROOT / _SOURCE[(product, guide)], None))
    return found


def find_guide(product: Product, guide: Guide, *, roots: list[Path] | None = None) -> Path | None:
    """The first copy of *product*'s *guide* that exists, or None.

    The user guide is its Markdown contents page (the editors render it, so F1
    can open the chapter it names); the GitHub Guide is its shipped HTML.
    """
    for file, folder in guide_candidates(product, guide, roots=roots):
        try:
            if file.is_file() and (folder is None or folder.is_dir()):
                return file
        except OSError:
            continue
    return None
