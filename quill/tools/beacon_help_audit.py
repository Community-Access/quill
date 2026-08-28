"""GATE-BEACON-HELP: F1 help must ship with every Beacon surface and control.

QuillBeacon answers F1 exactly as Quill Radio and QUILL Cast do -- what the
window is for, then what the focused control does -- and this gate keeps that
promise from rotting: :mod:`quill.apps.beacon.surface_help` is Beacon's
authored catalogue, and every helpable control in the Beacon package is
classified in a committed inventory where ``missing`` fails the build.

Configuration only: the scanner, the snapshot rules and the CLI live in
:mod:`quill.tools.help_audit`. What is Beacon's own is here -- the scan dirs,
the catalogue that judges the titles, and the snapshot path.

One honest limitation: Beacon's windows subclass ``wx.Frame``/``wx.Dialog``
and pass their titles through ``super().__init__(...)``, which the shared
title scanner does not resolve (it reads direct ``wx.Frame(...)`` /
``wx.Dialog(...)`` constructions, the composition style Radio and Cast use).
So the title half of this gate is enforced by
``tests/unit/tools/test_beacon_help_audit.py`` pinning every shipped window
title against the catalogue, not by the scan -- until the shared scanner
learns the subclass style.

Regenerate with::

    python -m quill.tools.beacon_help_audit --write

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

SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "beacon_help_inventory.json"

#: The whole of QuillBeacon -- a self-contained app package.
_SCAN_DIRS: tuple[str, ...] = ("quill/apps/beacon",)
_SCAN_GLOBS: tuple[str, ...] = ()

#: Surface constructions whose titles the scan cannot resolve, with the
#: reason they are fine. Keyed ``<module>::<qualname>``. Empty today: the
#: scan sees no Beacon titles at all (see the module docstring), so title
#: coverage is pinned in the gate test instead.
TITLE_EXEMPT: dict[str, str] = {}


def scan() -> tuple[list[ControlSite], list[TitleViolation]]:
    """Every helpable-control site in the Beacon package, and every unknown title."""
    from quill.apps.beacon import surface_help

    return scan_paths(
        resolve_paths(_SCAN_DIRS, _SCAN_GLOBS),
        is_known_title=surface_help.is_known_title,
        title_exempt=TITLE_EXEMPT,
        catalogue="quill/apps/beacon/surface_help.py",
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
        module_name="quill.tools.beacon_help_audit",
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
