"""GATE-INKWELL-HELP: F1 help must ship with every Inkwell surface and control.

Quill Inkwell answers F1 exactly as Quill Radio and QUILL Cast do -- what the
window is for, then what the focused control does -- but until 2026-08-27 it
had no authored catalogue, so every Inkwell window opened its help with the
generic sentence. :mod:`quill.core.inkwell_surface_help` is Inkwell's
catalogue and this is its gate, the same shape as GATE-RADIO-HELP and
GATE-CAST-HELP so no app's coverage can rot quietly.

Configuration only: the scanner, the snapshot rules and the CLI live in
:mod:`quill.tools.help_audit`. What is Inkwell's own is here -- the single
app module (Inkwell has no ``quill/ui`` subpackage; its shared dialogs are
QUILL's and are audited with QUILL), the catalogue that judges the titles,
the snapshot path, and the exemptions.

Regenerate with::

    python -m quill.tools.inkwell_help_audit --write

and review the diff: every ``missing`` you commit is a failing build.
"""

from __future__ import annotations

from pathlib import Path

from quill.tools.help_audit import (
    REPO_ROOT,
    ControlSite,
    TitleViolation,
    build_snapshot,
    resolve_paths,
    run_cli,
    scan_paths,
)
from quill.tools.help_audit import (
    STATUSES as STATUSES,
)
from quill.tools.help_audit import (
    write_snapshot as _write_snapshot,
)

SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "inkwell_help_inventory.json"

#: Inkwell is a single-file app: the manager window and its panel live in
#: ``quill/apps/inkwell.py``; the dialogs it opens (Manage Abbreviations,
#: Quick Insert, Fill In) are shared with QUILL and live under ``quill/ui``.
_SCAN_DIRS: tuple[str, ...] = ()
_SCAN_GLOBS: tuple[str, ...] = ("quill/apps/inkwell.py",)

#: Surface constructions whose titles the scan cannot resolve, with the
#: reason they are fine. Keyed ``<module>::<qualname>``.
TITLE_EXEMPT: dict[str, str] = {}


def scan() -> tuple[list[ControlSite], list[TitleViolation]]:
    """Every helpable-control site in Inkwell's app module, and every unknown title."""
    from quill.core import inkwell_surface_help

    return scan_paths(
        resolve_paths(_SCAN_DIRS, _SCAN_GLOBS),
        is_known_title=inkwell_surface_help.is_known_title,
        title_exempt=TITLE_EXEMPT,
        catalogue="quill/core/inkwell_surface_help.py",
    )


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, str]:
    from quill.tools.help_audit import load_snapshot as _load

    return _load(path)


def write_snapshot(snapshot: dict[str, str], path: Path = SNAPSHOT_PATH) -> None:
    _write_snapshot(snapshot, path)


def main(argv: list[str] | None = None) -> int:
    return run_cli(
        argv,
        description=__doc__.splitlines()[0],
        module_name="quill.tools.inkwell_help_audit",
        snapshot_path=SNAPSHOT_PATH,
        scan=scan,
    )


__all__ = [
    "SNAPSHOT_PATH",
    "STATUSES",
    "TITLE_EXEMPT",
    "ControlSite",
    "TitleViolation",
    "build_snapshot",
    "load_snapshot",
    "main",
    "scan",
    "write_snapshot",
]


if __name__ == "__main__":
    raise SystemExit(main())
