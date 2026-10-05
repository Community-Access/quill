"""GATE-CAST-HELP: F1 help must ship with every Cast surface and control.

QUILL Cast answers F1 exactly as Quill Radio does -- what the window is for,
then what the focused control does -- but until 2026-08-24 only Radio had an
authored catalogue, so every Cast window opened its help with the generic
sentence. :mod:`quill.core.podcasts.surface_help` is Cast's catalogue and
this is its gate, the same shape as GATE-RADIO-HELP so neither app's coverage
can rot quietly.

Configuration only: the scanner, the snapshot rules and the CLI live in
:mod:`quill.tools.help_audit`. What is Cast's own is here -- the podcast UI
modules, the catalogue that judges the titles, the snapshot path, and the
exemptions.

Regenerate with::

    python -m quill.tools.cast_help_audit --write

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

SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "cast_help_inventory.json"

#: The podcast UI surface -- the whole of QUILL Cast, and the same windows
#: QUILL itself opens for podcasts.
_SCAN_DIRS: tuple[str, ...] = ("quill/ui/podcasts",)
_SCAN_GLOBS: tuple[str, ...] = ("quill/apps/podcasts*.py",)

#: Surface constructions whose titles the scan cannot resolve, with the
#: reason they are fine. Keyed ``<module>::<qualname>``.
TITLE_EXEMPT: dict[str, str] = {
    "quill/ui/podcasts/ai_review_dialog.py::review": (
        "the title is the feature's name, passed in by cast_ai_features; every "
        "one is in surface_help.PURPOSES"
    ),
    "quill/ui/podcasts/ai_answer_dialog.py::show_answer": (
        "the title is 'About <podcast>', 'Is <episode> for me?' or 'Summary of "
        "<episode>'; all three are prefixes in surface_help.PREFIX_PURPOSES"
    ),
    "quill/ui/podcasts/schedule_dialog.py::ScheduleDialog.__init__": (
        "the title is 'Schedule for <podcast>' or 'Schedule for Every Podcast', "
        "built from the podcast's title, so the scan sees no literal; 'Schedule "
        "for' is a prefix in surface_help.PREFIX_PURPOSES"
    ),
    "quill/ui/podcasts/single_setting_dialog.py::SingleSettingDialog.__init__": (
        "the title is '<setting title> -- <show>', built from "
        "single_settings.SINGLE_SETTINGS, so the scan sees no literal; all "
        "three titles are prefixes in surface_help.PREFIX_PURPOSES and are "
        "pinned by test_cast_single_settings"
    ),
    "quill/ui/podcasts/first_run_dialog.py::FirstRunDialog.__init__": (
        "the title is the module's TITLE constant ('Welcome to QUILL Cast'), "
        "so the scan sees a name rather than a literal; the one screen is in "
        "surface_help.PURPOSES, pinned by test_cast_help_audit"
    ),
    "quill/ui/podcasts/skip_settings_dialog.py::SkipSettingsDialog.__init__": (
        "QUILL's own window: Cast never opens it (its Skip Settings route opens "
        "Preferences at Playing), and QUILL's F1 does not read Cast's "
        "catalogue, so a purpose here would describe a window no Cast user can "
        "reach; pinned by test_cast_help_audit"
    ),
    "quill/ui/podcasts/show_list_editor.py::ListSettingDialog.__init__": (
        "the title is '<subject> -- <show>' chosen from _SUBJECTS at runtime; "
        "all three subjects are prefixes in surface_help.PREFIX_PURPOSES and "
        "are pinned by test_cast_show_settings"
    ),
    "quill/ui/podcasts/folder_settings_dialog.py::FolderSettingsDialog.__init__": (
        "an f-string that opens with the module's TITLE ('Folder Settings') "
        "rather than a literal, so the prefix scan cannot see it; surface_help "
        "answers it by prefix, pinned by test_cast_surface_help"
    ),
}


def scan() -> tuple[list[ControlSite], list[TitleViolation]]:
    """Every helpable-control site in the podcast UI, and every unknown title."""
    from quill.core.podcasts import surface_help

    return scan_paths(
        resolve_paths(_SCAN_DIRS, _SCAN_GLOBS),
        is_known_title=surface_help.is_known_title,
        title_exempt=TITLE_EXEMPT,
        catalogue="quill/core/podcasts/surface_help.py",
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
        module_name="quill.tools.cast_help_audit",
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
