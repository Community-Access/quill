"""GATE-RADIO-HELP: F1 help must ship with every radio surface and control.

Quill Radio answers F1 everywhere with two paragraphs: what the window is for
(:mod:`quill.core.radio.surface_help`, keyed by window title) and what the
focused control does (its ``SetHelpText``, its accessible name, and a role
line). Wiring is inherited -- the dialog contract's show paths bind F1 on
every window -- so the only way coverage can rot is content: a new window
with no purpose paragraph, or a new control with nothing authored.

This module is now **configuration**: the scanner, the snapshot rules and the
CLI live in :mod:`quill.tools.help_audit`, shared with GATE-CAST-HELP since
2026-08-24. What is Radio's own is here -- which modules are scanned, which
catalogue judges the titles, where the snapshot lives, and the exemptions.
Read the engine's docstring for what ``helped`` / ``named-help`` /
``help-elsewhere`` / ``opt-out`` mean and why ``missing`` fails the build.

Regenerate with::

    python -m quill.tools.radio_help_audit --write

and review the diff: every ``missing`` you commit is a failing build.
"""

from __future__ import annotations

from pathlib import Path

from quill.tools.help_audit import (
    HELP_ELSEWHERE as HELP_ELSEWHERE,
)
from quill.tools.help_audit import (
    HELPED as HELPED,
)
from quill.tools.help_audit import (
    MISSING as MISSING,
)
from quill.tools.help_audit import (
    NAMED_HELP as NAMED_HELP,
)
from quill.tools.help_audit import (
    OPT_OUT as OPT_OUT,
)
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

SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "radio_help_inventory.json"

#: The radio UI surface: everything the F1 experience must cover.
_SCAN_DIRS: tuple[str, ...] = ("quill/ui/radio",)
_SCAN_GLOBS: tuple[str, ...] = ("quill/apps/radio*.py",)

#: Surface constructions whose titles the scan cannot resolve, with the
#: reason they are fine. Keyed ``<module>::<qualname>``.
TITLE_EXEMPT: dict[str, str] = {
    "quill/ui/radio/first_run_dialog.py::RadioFirstRunDialog.__init__": (
        "titles come from onboarding.SCREEN_TITLES; all three screens are in "
        "surface_help.PURPOSES, pinned by test_surface_help"
    ),
    "quill/ui/radio/catalogue_picker_dialog.py::_CataloguePicker.show": (
        "one dialog, many catalogues: the title is the caller's, because the "
        "same window serves ACB Media Podcasts and Community Picks. Each "
        "caller's title is a literal in its own wiring module and is registered "
        "in surface_help.PURPOSES; test_catalogue_picker pins that every caller "
        "of choose_from_catalogue passes a title the catalogue knows"
    ),
}


def scan() -> tuple[list[ControlSite], list[TitleViolation]]:
    """Every helpable-control site in the radio UI, and every unknown title."""
    from quill.core.radio import surface_help

    return scan_paths(
        resolve_paths(_SCAN_DIRS, _SCAN_GLOBS),
        is_known_title=surface_help.is_known_title,
        title_exempt=TITLE_EXEMPT,
        catalogue="quill/core/radio/surface_help.py",
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
        module_name="quill.tools.radio_help_audit",
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
