"""Let an engine-pack copy of a package supersede a bundled one.

Most engine packs hold something the app does *not* ship, so putting the pack
on ``sys.path`` is all it takes to light the feature up. yt-dlp is the
exception: it is bundled (a ~3 MB wheel, so a YouTube link works on a fresh
install with no download) *and* it goes stale, because upstream ships fixes
whenever YouTube changes its player -- far more often than QUILL ships
releases. So its on-demand installer has to be able to override the copy the
app was built with.

``sys.path`` cannot express that in a frozen build. PyInstaller's
``FrozenImporter`` lives in ``sys.meta_path``, and the whole of ``meta_path``
is consulted before the path machinery is reached, so the baked-in copy always
wins and an "update" silently does nothing. The finder here goes in at
``meta_path[0]``, ahead of it, and claims exactly one package tree.

wx-free, strict-typed. Split out of ``engine_install`` to keep that module
under its size budget (GATE-11).
"""

from __future__ import annotations

import importlib
import importlib.machinery
import sys
from pathlib import Path


class EnginePackPriorityFinder:
    """A meta-path finder that resolves one package tree from an engine pack.

    Declines every other module, so no import outside *module_name* and its
    submodules is affected.
    """

    def __init__(self, pack_dir: Path | str, module_name: str) -> None:
        self._pack_dir = str(pack_dir)
        self._module_name = module_name
        self._submodule_prefix = f"{module_name}."

    @property
    def module_name(self) -> str:
        return self._module_name

    def find_spec(
        self, fullname: str, path: object = None, target: object = None
    ) -> importlib.machinery.ModuleSpec | None:
        if fullname != self._module_name and not fullname.startswith(self._submodule_prefix):
            return None
        # Delegate to the ordinary path machinery so packages, submodules, and
        # namespace rules behave exactly as normal -- only the search location
        # differs. The top-level package is pinned to the pack; a submodule
        # then arrives with its parent's __path__, which already points there.
        search = [self._pack_dir] if fullname == self._module_name else path
        return importlib.machinery.PathFinder.find_spec(fullname, search)  # type: ignore[arg-type]


def prefer_pack_module(pack_dir: Path, module_name: str) -> bool:
    """Make *module_name* resolve from *pack_dir* first. Idempotent.

    Returns whether the override is now installed -- ``False`` when the pack
    holds no copy of the package, which is the normal case for a user who has
    never installed an update.
    """
    try:
        if not (pack_dir / module_name).is_dir():
            return False
    except OSError:
        return False
    for finder in sys.meta_path:
        if isinstance(finder, EnginePackPriorityFinder) and finder.module_name == module_name:
            return True
    sys.meta_path.insert(0, EnginePackPriorityFinder(pack_dir, module_name))
    importlib.invalidate_caches()
    return True
