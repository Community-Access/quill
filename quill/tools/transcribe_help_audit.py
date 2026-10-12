"""GATE-TRANSCRIBE-HELP: F1 help must ship with every QUILL Transcribe surface and control.

QUILL Transcribe answers F1 as every family app does -- what the window is for,
then what the focused control does. :mod:`quill.core.transcribe.surface_help`
is its catalogue and this is its gate, the same shape as GATE-INKWELL-HELP.

Configuration only: the scanner, the snapshot rules and the CLI live in
:mod:`quill.tools.help_audit`. What is QUILL Transcribe's own is here -- its app
modules (``quill/apps/transcribe*.py``; the shared dialogs it opens are QUILL's
and are audited with QUILL), the catalogue that judges the titles, the
snapshot path, and the exemptions.

Regenerate with::

    python -m quill.tools.transcribe_help_audit --write

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

SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "transcribe_help_inventory.json"

#: The app and its own dialogs live in ``quill/apps/transcribe*.py``; the
#: dialogs it shares with QUILL live under ``quill/ui`` and are audited there.
_SCAN_DIRS: tuple[str, ...] = ()
_SCAN_GLOBS: tuple[str, ...] = ("quill/apps/transcribe*.py",)

#: Surface constructions whose titles the scan cannot resolve, with the
#: reason they are fine. Keyed ``<module>::<qualname>``.
TITLE_EXEMPT: dict[str, str] = {}


def scan() -> tuple[list[ControlSite], list[TitleViolation]]:
    """Every helpable-control site in QUILL Transcribe's modules, and every unknown title."""
    from quill.core.transcribe import surface_help

    return scan_paths(
        resolve_paths(_SCAN_DIRS, _SCAN_GLOBS),
        is_known_title=surface_help.is_known_title,
        title_exempt=TITLE_EXEMPT,
        catalogue="quill/core/transcribe/surface_help.py",
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
        module_name="quill.tools.transcribe_help_audit",
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
