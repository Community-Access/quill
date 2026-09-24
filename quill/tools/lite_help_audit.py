"""GATE-LITE-HELP: F1 help must ship with every QuillLite surface and control.

The eighth app to join the family's F1 program, and the same shape as the seven
before it. :mod:`quill.core.lite_surface_help` is QuillLite's catalogue of window
purposes and this is its gate, so a new QuillLite window cannot ship without
saying what it is for and a new control cannot ship without either help or a
deliberate, reviewed classification.

Configuration only: the scanner, the snapshot rules and the CLI all live in
:mod:`quill.tools.help_audit`. What is QuillLite's own is here -- the modules it
scans, the catalogue that judges the titles, the snapshot path, and the
exemptions.

Regenerate with::

    python -m quill.tools.lite_help_audit --write

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

SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "lite_help_inventory.json"

#: QuillLite has no ``quill/ui`` subpackage: its modules sit together under
#: ``quill/apps`` (the app, the window, its commands, its dialogs), which is
#: what ``lite*.py`` picks up -- including any module a future split adds.
#:
#: The one exception is a dialog that has been *shared* rather than split: the
#: Spelling Announcements window moved to ``quill/ui`` so QUILL could open it on
#: the same chord (bad.md P1.14), and moving it out of this glob silently
#: dropped twelve authored help sentences from the audit and from the generated
#: reference. A surface no gate can see is one that rots, so the glob follows
#: the surface. Keep this in step with ``build_help_reference.APPS``.
_SCAN_DIRS: tuple[str, ...] = ()
_SCAN_GLOBS: tuple[str, ...] = (
    "quill/apps/lite*.py",
    "quill/ui/spelling_voice_dialog.py",
    # The hosted-AI windows went the same way as the Spelling Announcements
    # one, and for the stronger reason: QUILL now opens them too (they are its
    # *default* AI), so they could not stay in a QuillLite-only module without
    # breaking the rule that QuillLite is never ahead of QUILL. They stay in
    # this glob because QuillLite is still a caller, and a surface no gate can
    # see is one that rots -- QUILL's own help audit covers them as well, which
    # is correct: two callers, two gates, one set of sentences.
    "quill/ui/hosted_ai*.py",
)

#: Surface constructions whose titles the scan cannot resolve, with the reason
#: they are fine. Keyed ``<module>::<qualname>``.
TITLE_EXEMPT: dict[str, str] = {
    "quill/apps/lite_check.py::run_check": (
        "The --check diagnostic's frame is built, measured and destroyed without "
        "a MainLoop; no listener ever reaches it, so it has no purpose to author. "
        "Its title is the app name, single-sourced from quill.core.lite."
    ),
    "quill/apps/lite_dialogs.py::choose_from_rows": (
        "One generic list window with six callers, each passing a literal the "
        "catalogue answers: 'Headings', 'Bookmarks', 'Copy Tray', 'Clip Library', "
        "'Spelling Suggestions' and 'Marks'. The alternative is six copies of a "
        "list dialog, which is six places for the Enter-key handling to be got "
        "wrong in."
    ),
    "quill/apps/lite_dialogs.py::show_text_window": (
        "The title is the caller's, and both callers pass a literal that the "
        "catalogue answers: 'Keyboard shortcuts' and 'About QuillLite'."
    ),
    "quill/apps/lite_dialogs.py::choose_searchable": (
        "One filtered-list window with two callers, each passing a literal the "
        "catalogue answers: 'Insert Markdown Tag' and 'Insert HTML Tag'. Exactly "
        "the argument choose_from_rows makes: the alternative is two copies of a "
        "search-and-choose dialog, which is two places to get the "
        "Enter-moves-to-the-list handling wrong in."
    ),
    "quill/ui/hosted_ai_dialogs.py::ask_ai_privacy_agreement": (
        "The title is quill.core.ai.gateway_privacy.AGREEMENT_TITLE, not a "
        "literal, and deliberately: the window is titled by the same module "
        "that owns the agreement's text and its version number, so a change to "
        "what is being agreed to cannot leave the window announcing the old "
        "thing. The catalogue answers that constant's current value."
    ),
    "quill/apps/lite_dialogs_entry.py::ask_text": (
        "One labelled-box window whose three callers pass literals the catalogue "
        "answers: 'Insert HTML Tag' for the attribute box, and 'Insert Link' and "
        "'Insert Image' for the address. It exists instead of wx.TextEntryDialog "
        "precisely because that one's prompt is not a StaticText immediately "
        "before the field, so the field's accessible name on wxMSW is whatever a "
        "reader can scrape -- which is nothing."
    ),
}


def scan() -> tuple[list[ControlSite], list[TitleViolation]]:
    """Every helpable-control site in QuillLite, and every unknown title."""
    from quill.core import lite_surface_help

    return scan_paths(
        resolve_paths(_SCAN_DIRS, _SCAN_GLOBS),
        is_known_title=lite_surface_help.is_known_title,
        title_exempt=TITLE_EXEMPT,
        catalogue="quill/core/lite_surface_help.py",
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
        module_name="quill.tools.lite_help_audit",
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
